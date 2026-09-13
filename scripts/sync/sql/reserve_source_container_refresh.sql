-- Reserve Source Container Refresh
--
-- Purpose:
--     Atomically reserves one Source for complete Source Container Refresh
--     and creates the associated running Processing Job.
--
-- Responsibilities:
--     - Detect conflicting active Refresh execution for the Source.
--     - Reserve the Source for one Refresh operation.
--     - Create the running Processing Job within the reservation operation.
--     - Return the created Processing Job identity.
--
-- Does NOT:
--     - Enumerate Source Containers.
--     - Apply Source Container catalog changes.
--     - Complete or fail Processing Jobs.
--     - Reserve content synchronization.

CREATE OR REPLACE FUNCTION public.reserve_source_container_refresh(
    p_source_id uuid,
    p_process_type text,
    p_pipeline_version text,
    p_metadata jsonb
)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
    v_processing_job_id uuid;
BEGIN

    -- --------------------------------------------------------
    -- Validate required reservation values.
    -- --------------------------------------------------------

    IF p_source_id IS NULL THEN
        RAISE EXCEPTION
            'source_id is required';
    END IF;

    IF NULLIF(
        btrim(p_process_type),
        ''
    ) IS NULL
    THEN
        RAISE EXCEPTION
            'process_type is required';
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
    -- The transaction-level advisory lock prevents two
    -- operations from checking the same Source simultaneously.
    -- Operations against different Sources remain independent.
    -- --------------------------------------------------------

    PERFORM pg_advisory_xact_lock(
        hashtextextended(
            p_source_id::text,
            0
        )
    );

    -- --------------------------------------------------------
    -- A Source Container Refresh reserves the complete Source.
    --
    -- Any running operation against the same Source conflicts
    -- with the requested Refresh.
    -- --------------------------------------------------------

    IF EXISTS (
        SELECT 1
        FROM public.processing_jobs
        WHERE
            source_id = p_source_id
            AND status = 'running'
    )
    THEN
        RAISE EXCEPTION
            'An active operation already reserves Source %',
            p_source_id;
    END IF;

    -- --------------------------------------------------------
    -- The final conflict check and Processing Job creation
    -- occur inside this single database transaction.
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
        btrim(p_process_type),
        'running',
        now(),
        btrim(p_pipeline_version),
        p_metadata
    )
    RETURNING id
    INTO v_processing_job_id;

    RETURN v_processing_job_id;

END;
$$;