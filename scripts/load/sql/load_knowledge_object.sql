-- Load Knowledge Object
--
-- Purpose:
--     Provides the database operation used by Load to persist a Knowledge
--     Object and its synchronization history within the required database
--     transaction boundary.
--
-- Responsibilities:
--     - Persist the Knowledge Object changes supplied by Load.
--     - Persist the associated synchronization history event.
--     - Keep related Load persistence within the approved database
--       transaction boundary.
--
-- Does NOT:
--     - Determine synchronization state.
--     - Retrieve or extract source content.
--     - Decide whether a record is eligible for Load.
--     - Execute synchronization orchestration.

create or replace function load_knowledge_object(
    p_sync_state text,
    p_knowledge_object_id uuid,
    p_source_id uuid,
    p_source_object_id text,
    p_source_parent_object_id text,
    p_source_path text,
    p_source_url text,
    p_title text,
    p_object_type text,
    p_canonical_content text,
    p_content_hash text,
    p_source_created_at timestamptz,
    p_source_modified_at timestamptz,
    p_metadata jsonb,
    p_processing_job_id uuid,
    p_comparison_reason text
)
returns uuid
language plpgsql
as $$
declare
    v_knowledge_object_id uuid;
begin

    if p_sync_state = 'NEW' then

        insert into knowledge_objects (
            source_id,
            domain_id,
            source_object_id,
            source_parent_object_id,
            source_path,
            source_url,
            title,
            object_type,
            canonical_content,
            content_hash,
            source_created_at,
            source_modified_at,
            metadata
        )
        values (
            p_source_id,
            null,
            p_source_object_id,
            p_source_parent_object_id,
            p_source_path,
            p_source_url,
            p_title,
            p_object_type,
            p_canonical_content,
            p_content_hash,
            p_source_created_at,
            p_source_modified_at,
            p_metadata
        )
        returning id into v_knowledge_object_id;

    elsif p_sync_state = 'MODIFIED' then

        if p_knowledge_object_id is null then
            raise exception
                'knowledge_object_id is required for MODIFIED records.';
        end if;

        update knowledge_objects
        set
            source_parent_object_id = p_source_parent_object_id,
            source_path = p_source_path,
            source_url = p_source_url,
            title = p_title,
            object_type = p_object_type,
            canonical_content = p_canonical_content,
            content_hash = p_content_hash,
            source_created_at = p_source_created_at,
            source_modified_at = p_source_modified_at,
            metadata = p_metadata
        where id = p_knowledge_object_id;

        if not found then
            raise exception
                'Knowledge Object % was not found.',
                p_knowledge_object_id;
        end if;

        v_knowledge_object_id := p_knowledge_object_id;

    else

        raise exception
            'Unsupported synchronization state: %',
            p_sync_state;

    end if;

    insert into sync_history (
        source_id,
        knowledge_object_id,
        processing_job_id,
        sync_event,
        source_modified_at,
        metadata
    )
    values (
        p_source_id,
        v_knowledge_object_id,
        p_processing_job_id,
        p_sync_state,
        p_source_modified_at,
        jsonb_build_object(
            'comparison_reason',
            p_comparison_reason
        )
    );

    return v_knowledge_object_id;

end;
$$;