CREATE OR REPLACE FUNCTION public.upsert_source_containers(
    p_source_id uuid,
    p_processing_job_id uuid,
    p_observed_at timestamptz,
    p_containers jsonb
)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_container jsonb;
    v_count integer := 0;
BEGIN

    IF p_source_id IS NULL THEN
        RAISE EXCEPTION
            'source_id is required';
    END IF;

    IF p_processing_job_id IS NULL THEN
        RAISE EXCEPTION
            'processing_job_id is required';
    END IF;

    IF p_observed_at IS NULL THEN
        RAISE EXCEPTION
            'observed_at is required';
    END IF;

    IF p_containers IS NULL
       OR jsonb_typeof(p_containers) <> 'array'
    THEN
        RAISE EXCEPTION
            'containers must be a JSON array';
    END IF;

    FOR v_container IN
        SELECT value
        FROM jsonb_array_elements(p_containers)
    LOOP

        IF NULLIF(
            btrim(
                v_container->>'source_object_id'
            ),
            ''
        ) IS NULL
        THEN
            RAISE EXCEPTION
                'source_object_id is required';
        END IF;

        IF NULLIF(
            btrim(
                v_container->>'name'
            ),
            ''
        ) IS NULL
        THEN
            RAISE EXCEPTION
                'name is required';
        END IF;

        INSERT INTO public.source_containers (
            source_id,
            source_object_id,
            parent_source_object_id,
            name,
            last_seen_at,
            last_seen_processing_job_id,
            is_active
        )
        VALUES (
            p_source_id,
            v_container->>'source_object_id',
            NULLIF(
                btrim(
                    v_container->>'parent_source_object_id'
                ),
                ''
            ),
            v_container->>'name',
            p_observed_at,
            p_processing_job_id,
            TRUE
        )
        ON CONFLICT (
            source_id,
            source_object_id
        )
        DO UPDATE SET
            parent_source_object_id =
                EXCLUDED.parent_source_object_id,
            name =
                EXCLUDED.name,
            last_seen_at =
                EXCLUDED.last_seen_at,
            last_seen_processing_job_id =
                EXCLUDED.last_seen_processing_job_id,
            is_active =
                TRUE;

        v_count := v_count + 1;

    END LOOP;

    RETURN v_count;

END;
$$;