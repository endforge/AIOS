-- Reserve Synchronization
--
-- Purpose:
--     Atomically admits and reserves one Source Container synchronization
--     scope and creates its operational persistence records.
--
-- Responsibilities:
--     - Serialize synchronization admission decisions for one Source.
--     - Revalidate the registered Source and selected Source Container.
--     - Reject synchronization while Source Container Refresh is active.
--     - Reject same-Container and ancestor/descendant synchronization conflicts.
--     - Allow sibling and otherwise disjoint synchronization scopes.
--     - Create the running Processing Job within the reservation transaction.
--     - Create the associated Synchronization Run within the same transaction.
--     - Generate Synchronization Run identity when the table does not provide
--       a database default.
--     - Return the created Processing Job and Synchronization Run identities.
--
-- Does NOT:
--     - Communicate with a Source of Truth.
--     - Perform preliminary conflict checking.
--     - Refresh Source Containers.
--     - Execute synchronization stages.
--     - Complete or fail Processing Jobs.

CREATE OR REPLACE FUNCTION public.reserve_synchronization(
    p_source_id uuid,
    p_source_container_id uuid,
    p_pipeline_version text,
    p_metadata jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_source_enabled boolean;

    v_container_source_id uuid;
    v_requested_source_object_id text;
    v_container_is_active boolean;

    v_has_sync_conflict boolean;

    v_processing_job_id uuid;
    v_sync_run_id uuid;
BEGIN

    -- --------------------------------------------------------
    -- Validate required reservation values.
    -- --------------------------------------------------------

    IF p_source_id IS NULL THEN
        RAISE EXCEPTION
            'source_id is required';
    END IF;

    IF p_source_container_id IS NULL THEN
        RAISE EXCEPTION
            'source_container_id is required';
    END IF;

    IF NULLIF(
        btrim(p_pipeline_version),
        ''
    ) IS NULL
    THEN
        RAISE EXCEPTION
            'pipeline_version is required';
    END IF;

    IF p_metadata IS NULL
       OR jsonb_typeof(p_metadata) <> 'object'
    THEN
        RAISE EXCEPTION
            'metadata must be a JSON object';
    END IF;

    -- --------------------------------------------------------
    -- Serialize admission decisions for this Source.
    --
    -- Source Container Refresh uses the same Source-level
    -- advisory lock.
    --
    -- The lock exists only for this database transaction.
    -- It serializes admission decisions without serializing the
    -- complete execution of disjoint synchronization scopes.
    -- --------------------------------------------------------

    PERFORM pg_advisory_xact_lock(
        hashtextextended(
            p_source_id::text,
            0
        )
    );

    -- --------------------------------------------------------
    -- Revalidate the Source.
    -- --------------------------------------------------------

    SELECT
        is_enabled
    INTO
        v_source_enabled
    FROM
        public.sources
    WHERE
        id = p_source_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Source % does not exist',
            p_source_id;
    END IF;

    IF v_source_enabled IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION
            'Source % is not enabled',
            p_source_id;
    END IF;

    -- --------------------------------------------------------
    -- Revalidate the selected Source Container.
    -- --------------------------------------------------------

    SELECT
        source_id,
        source_object_id,
        is_active
    INTO
        v_container_source_id,
        v_requested_source_object_id,
        v_container_is_active
    FROM
        public.source_containers
    WHERE
        id = p_source_container_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Source Container % does not exist',
            p_source_container_id;
    END IF;

    IF v_container_source_id <> p_source_id THEN
        RAISE EXCEPTION
            'Source Container % does not belong to Source %',
            p_source_container_id,
            p_source_id;
    END IF;

    IF v_container_is_active IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION
            'Source Container % is not active',
            p_source_container_id;
    END IF;

    -- --------------------------------------------------------
    -- Source Container Refresh reserves the complete Source.
    -- --------------------------------------------------------

    IF EXISTS (
        SELECT 1
        FROM public.processing_jobs
        WHERE
            source_id = p_source_id
            AND process_type = 'source_container_refresh'
            AND status = 'running'
    )
    THEN
        RAISE EXCEPTION
            'Source Container Refresh is active for Source %',
            p_source_id;
    END IF;

    -- --------------------------------------------------------
    -- Authoritative synchronization scope conflict check.
    --
    -- Conflict:
    --     same Container
    --     active scope is an ancestor of requested scope
    --     requested scope is an ancestor of active scope
    --
    -- Allowed:
    --     sibling scopes
    --     otherwise disjoint scopes
    -- --------------------------------------------------------

    WITH RECURSIVE

    requested_ancestors AS (

        SELECT
            source_object_id,
            parent_source_object_id
        FROM
            public.source_containers
        WHERE
            id = p_source_container_id
            AND source_id = p_source_id

        UNION

        SELECT
            parent.source_object_id,
            parent.parent_source_object_id
        FROM
            public.source_containers parent
        INNER JOIN
            requested_ancestors child
                ON parent.source_id = p_source_id
                AND parent.source_object_id =
                    child.parent_source_object_id
    ),

    active_scopes AS (

        SELECT
            sync_run.source_container_id,
            container.source_object_id
        FROM
            public.sync_runs sync_run
        INNER JOIN
            public.processing_jobs processing_job
                ON processing_job.id =
                    sync_run.processing_job_id
        INNER JOIN
            public.source_containers container
                ON container.id =
                    sync_run.source_container_id
        WHERE
            sync_run.source_id = p_source_id
            AND processing_job.status = 'running'
    ),

    active_ancestors AS (

        SELECT
            active_scope.source_container_id
                AS active_source_container_id,

            container.source_object_id,
            container.parent_source_object_id
        FROM
            active_scopes active_scope
        INNER JOIN
            public.source_containers container
                ON container.id =
                    active_scope.source_container_id

        UNION

        SELECT
            active_ancestor.active_source_container_id,
            parent.source_object_id,
            parent.parent_source_object_id
        FROM
            active_ancestors active_ancestor
        INNER JOIN
            public.source_containers parent
                ON parent.source_id = p_source_id
                AND parent.source_object_id =
                    active_ancestor.parent_source_object_id
    )

    SELECT
        EXISTS (

            SELECT 1
            FROM active_scopes active_scope
            WHERE
                active_scope.source_object_id
                IN (
                    SELECT
                        source_object_id
                    FROM
                        requested_ancestors
                )

            UNION ALL

            SELECT 1
            FROM active_ancestors active_ancestor
            WHERE
                active_ancestor.source_object_id =
                    v_requested_source_object_id
        )
    INTO
        v_has_sync_conflict;

    IF v_has_sync_conflict THEN
        RAISE EXCEPTION
            'Conflicting synchronization scope is active for Source % and Source Container %',
            p_source_id,
            p_source_container_id;
    END IF;

    -- --------------------------------------------------------
    -- Admission succeeded.
    --
    -- Both records are created inside this transaction.
    -- --------------------------------------------------------

    INSERT INTO public.processing_jobs (
        source_id,
        process_type,
        status,
        started_at,
        pipeline_version,
        metadata
    )
    VALUES (
        p_source_id,
        'sync',
        'running',
        now(),
        btrim(p_pipeline_version),
        p_metadata
    )
    RETURNING
        id
    INTO
        v_processing_job_id;

    -- --------------------------------------------------------
    -- sync_runs.id does not provide its own UUID default.
    -- Generate the AlphaOmega Synchronization Run identity here.
    -- --------------------------------------------------------

    v_sync_run_id := gen_random_uuid();

    INSERT INTO public.sync_runs (
        id,
        processing_job_id,
        source_id,
        source_container_id
    )
    VALUES (
        v_sync_run_id,
        v_processing_job_id,
        p_source_id,
        p_source_container_id
    );

    RETURN jsonb_build_object(
        'processing_job_id',
        v_processing_job_id,
        'sync_run_id',
        v_sync_run_id,
        'source_id',
        p_source_id,
        'source_container_id',
        p_source_container_id
    );

END;
$$;