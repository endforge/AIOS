-- Deactivate Source Containers
--
-- Purpose:
--     Deactivates persisted Source Containers proven absent by an approved
--     complete Source Container Refresh.
--
-- Responsibilities:
--     - Mark the supplied Source Containers inactive.
--     - Apply deactivation to the persisted source_containers catalog.
--     - Preserve catalog records rather than deleting them.
--
-- Does NOT:
--     - Determine which Source Containers are absent.
--     - Accept incomplete enumeration as proof of absence.
--     - Enumerate a Source of Truth.
--     - Synchronize content.

CREATE OR REPLACE FUNCTION public.deactivate_source_containers(
    p_source_id uuid,
    p_processing_job_id uuid,
    p_source_object_ids jsonb
)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_source_object_id text;
    v_count integer := 0;
    v_updated integer;
BEGIN

    -- --------------------------------------------------------
    -- Required arguments
    -- --------------------------------------------------------

    IF p_source_id IS NULL THEN
        RAISE EXCEPTION
            'source_id is required';
    END IF;

    IF p_processing_job_id IS NULL THEN
        RAISE EXCEPTION
            'processing_job_id is required';
    END IF;

    IF p_source_object_ids IS NULL
       OR jsonb_typeof(p_source_object_ids) <> 'array'
    THEN
        RAISE EXCEPTION
            'source_object_ids must be a JSON array';
    END IF;

    -- --------------------------------------------------------
    -- Process each absent Source Container identity
    -- --------------------------------------------------------

    FOR v_source_object_id IN
        SELECT jsonb_array_elements_text(
            p_source_object_ids
        )
    LOOP

        IF NULLIF(
            btrim(v_source_object_id),
            ''
        ) IS NULL
        THEN
            RAISE EXCEPTION
                'source_object_id is required';
        END IF;

        UPDATE public.source_containers
        SET
            is_active = FALSE
        WHERE
            source_id = p_source_id
            AND source_object_id =
                v_source_object_id
            AND is_active = TRUE;

        GET DIAGNOSTICS
            v_updated = ROW_COUNT;

        v_count :=
            v_count + v_updated;

    END LOOP;

    RETURN v_count;

END;
$$;