CREATE OR REPLACE FUNCTION public.apply_source_container_refresh(
    p_source_id uuid,
    p_processing_job_id uuid,
    p_observation_complete boolean,
    p_upsert_containers jsonb,
    p_absent_source_object_ids jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_upsert_count integer;
    v_deactivated_count integer;
BEGIN

    -- --------------------------------------------------------
    -- Required refresh identity
    -- --------------------------------------------------------

    IF p_source_id IS NULL THEN
        RAISE EXCEPTION
            'source_id is required';
    END IF;

    IF p_processing_job_id IS NULL THEN
        RAISE EXCEPTION
            'processing_job_id is required';
    END IF;

    -- --------------------------------------------------------
    -- ABSENT may only be applied from a complete observation.
    -- --------------------------------------------------------

    IF p_observation_complete IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION
            'Source Container Refresh requires a complete observation';
    END IF;

    -- --------------------------------------------------------
    -- Validate collection arguments before changing anything.
    -- --------------------------------------------------------

    IF p_upsert_containers IS NULL
       OR jsonb_typeof(p_upsert_containers) <> 'array'
    THEN
        RAISE EXCEPTION
            'upsert_containers must be a JSON array';
    END IF;

    IF p_absent_source_object_ids IS NULL
       OR jsonb_typeof(p_absent_source_object_ids) <> 'array'
    THEN
        RAISE EXCEPTION
            'absent_source_object_ids must be a JSON array';
    END IF;

    -- --------------------------------------------------------
    -- NEW / EXISTING / REAPPEARING
    --
    -- This existing function:
    --   * inserts NEW Containers
    --   * updates EXISTING Containers
    --   * reactivates REAPPEARING Containers
    --   * preserves existing AlphaOmega UUIDs
    -- --------------------------------------------------------

    SELECT public.upsert_source_containers(
        p_source_id,
        p_processing_job_id,
        now(),
        p_upsert_containers
    )
    INTO v_upsert_count;

    -- --------------------------------------------------------
    -- ABSENT
    --
    -- This existing function marks only the supplied identities
    -- inactive.
    -- --------------------------------------------------------

    SELECT public.deactivate_source_containers(
        p_source_id,
        p_processing_job_id,
        p_absent_source_object_ids
    )
    INTO v_deactivated_count;

    -- --------------------------------------------------------
    -- Both operations occur inside this single function call.
    --
    -- If either operation fails, the entire invocation fails
    -- and PostgreSQL rolls back changes made by both.
    -- --------------------------------------------------------

    RETURN jsonb_build_object(
        'upserted',
        v_upsert_count,
        'deactivated',
        v_deactivated_count
    );

END;
$$;