"""
AlphaOmega Load Repository

Purpose:
    Provides the persistence boundary used by Load to write synchronized
    Knowledge Object and synchronization-history data.

Responsibilities:
    - Create new Knowledge Objects through the Knowledge Object repository.
    - Update existing Knowledge Objects through the Knowledge Object
      repository.
    - Record synchronization history through the synchronization history
      repository.
    - Keep Load persistence operations behind repository boundaries.

Does NOT:
    - Determine synchronization state.
    - Retrieve or extract source content.
    - Decide whether a record is eligible for Load.
    - Execute synchronization orchestration.
"""

from typing import Any, Mapping, Optional

from supabase import Client


class LoadRepository:
    """
    Provides repository access to AlphaOmega Load persistence.

    The repository invokes the database-owned atomic persistence
    operation. It does not make synchronization decisions or
    reinterpret trusted upstream information.
    """

    FUNCTION_NAME = "load_knowledge_object"

    def __init__(self, client: Client):
        """
        Initialize the Load repository.

        Args:
            client:
                Authenticated Supabase client constrained by RLS.
        """

        if client is None:
            raise ValueError(
                "Authenticated Supabase client is required."
            )

        self._client = client

    def persist(
        self,
        *,
        sync_state: str,
        knowledge_object_id: Optional[str],
        source_id: str,
        source_object_id: str,
        source_parent_object_id: Optional[str],
        source_path: Optional[str],
        source_url: Optional[str],
        title: str,
        object_type: str,
        canonical_content: str,
        content_hash: str,
        source_created_at: Optional[str],
        source_modified_at: Optional[str],
        metadata: Mapping[str, Any],
        processing_job_id: Optional[str],
        comparison_reason: Optional[str],
    ) -> str:
        """
        Atomically persist one NEW or MODIFIED Knowledge Object and
        its synchronization history event.

        Args:
            sync_state:
                Trusted synchronization state produced by Discovery.

            knowledge_object_id:
                Existing AlphaOmega Knowledge Object UUID for a
                MODIFIED record. None for a NEW record.

            source_id:
                AlphaOmega Source UUID.

            source_object_id:
                Stable object identity assigned by the Source of Truth.

            source_parent_object_id:
                Immediate parent identity from the Source of Truth.

            source_path:
                Human-readable source hierarchy/path.

            source_url:
                Source URL when available.

            title:
                Canonical object title.

            object_type:
                Canonical AlphaOmega object type.

            canonical_content:
                Canonical content produced by Extraction.

            content_hash:
                SHA-256 content hash produced by Extraction.

            source_created_at:
                Source-reported creation timestamp.

            source_modified_at:
                Source-reported modification timestamp.

            metadata:
                Canonical metadata to persist.

            processing_job_id:
                Existing Processing Job associated with the
                synchronization run.

            comparison_reason:
                Discovery explanation for the synchronization state.

        Returns:
            str:
                AlphaOmega UUID of the persisted Knowledge Object.

        Raises:
            RuntimeError:
                If the atomic persistence operation fails or does
                not return a Knowledge Object UUID.
        """

        parameters = {
            "p_sync_state": sync_state,
            "p_knowledge_object_id": knowledge_object_id,
            "p_source_id": source_id,
            "p_source_object_id": source_object_id,
            "p_source_parent_object_id": source_parent_object_id,
            "p_source_path": source_path,
            "p_source_url": source_url,
            "p_title": title,
            "p_object_type": object_type,
            "p_canonical_content": canonical_content,
            "p_content_hash": content_hash,
            "p_source_created_at": source_created_at,
            "p_source_modified_at": source_modified_at,
            "p_metadata": dict(metadata),
            "p_processing_job_id": processing_job_id,
            "p_comparison_reason": comparison_reason,
        }

        try:
            response = (
                self._client
                .rpc(
                    self.FUNCTION_NAME,
                    parameters,
                )
                .execute()
            )

        except Exception as error:
            raise RuntimeError(
                "Atomic Load persistence failed."
            ) from error

        knowledge_object_id = response.data

        if (
            knowledge_object_id is None
            or not str(knowledge_object_id).strip()
        ):
            raise RuntimeError(
                "Atomic Load persistence returned no "
                "Knowledge Object identity."
            )

        return str(knowledge_object_id)