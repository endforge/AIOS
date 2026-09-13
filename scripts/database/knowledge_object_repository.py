"""
AlphaOmega Knowledge Object Repository

Purpose:
    Provides database access to canonical AlphaOmega Knowledge Objects.

Responsibilities:
    - Find Knowledge Objects by source identity.
    - Create new Knowledge Objects.
    - Update existing Knowledge Objects.
    - Validate persistence inputs and expected database results.
    - Own storage-specific operations against the knowledge_objects table.

Does NOT:
    - Determine synchronization state.
    - Decide whether a Knowledge Object should be created or updated.
    - Extract or transform source content.
    - Execute synchronization stages.
"""

from typing import Any, Mapping, Optional

from supabase import Client


class KnowledgeObjectRepository:
    """
    Provide repository access to AlphaOmega Knowledge Objects.
    """

    TABLE_NAME = "knowledge_objects"

    DISCOVERY_FIELDS = (
        "id,"
        "title,"
        "source_parent_object_id,"
        "source_modified_at,"
        "content_hash"
    )

    def __init__(self, client: Client):
        """
        Initialize the Knowledge Object repository.

        Args:
            client:
                Authenticated Supabase client constrained by RLS.
        """

        if client is None:
            raise ValueError(
                "Authenticated Supabase client is required."
            )

        self._client = client

    def find_by_source_identity(
        self,
        source_id: str,
        source_object_id: str,
    ) -> Optional[Mapping[str, Any]]:
        """
        Locate a Knowledge Object using its stable source identity.

        Args:
            source_id:
                AlphaOmega identifier for the Source of Truth.

            source_object_id:
                Unique identifier assigned by the Source of Truth.

        Returns:
            Mapping:
                Stored Knowledge Object facts required by Discovery.

            None:
                No Knowledge Object exists for the supplied source identity.

        Raises:
            ValueError:
                If required source identity is missing.

            RuntimeError:
                If the repository lookup cannot be completed.
        """

        if source_id is None or not str(source_id).strip():
            raise ValueError(
                "source_id is required."
            )

        if source_object_id is None or not str(source_object_id).strip():
            raise ValueError(
                "source_object_id is required."
            )

        try:
            response = (
                self._client
                .table(self.TABLE_NAME)
                .select(self.DISCOVERY_FIELDS)
                .eq("source_id", source_id)
                .eq("source_object_id", source_object_id)
                .limit(2)
                .execute()
            )
        except Exception as error:
            raise RuntimeError(
                "Knowledge Object repository lookup failed."
            ) from error

        records = response.data

        if records is None:
            raise RuntimeError(
                "Knowledge Object repository returned no result data."
            )

        if len(records) == 0:
            return None

        if len(records) > 1:
            raise RuntimeError(
                "Multiple Knowledge Objects were found for the same "
                "source identity."
            )

        return records[0]

    def create(
        self,
        values: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """
        Create a new canonical Knowledge Object.

        The database owns generation of the Knowledge Object UUID.

        Args:
            values:
                Canonical Knowledge Object values to persist.

        Returns:
            Mapping:
                The persisted Knowledge Object.

        Raises:
            ValueError:
                If persistence values are missing.

            RuntimeError:
                If the Knowledge Object cannot be created or the
                database does not return exactly one persisted row.
        """

        if values is None or not isinstance(values, Mapping):
            raise ValueError(
                "Knowledge Object persistence values are required."
            )

        if not values:
            raise ValueError(
                "Knowledge Object persistence values cannot be empty."
            )

        try:
            response = (
                self._client
                .table(self.TABLE_NAME)
                .insert(dict(values))
                .execute()
            )
        except Exception as error:
            raise RuntimeError(
                "Knowledge Object repository create failed."
            ) from error

        records = response.data

        if records is None:
            raise RuntimeError(
                "Knowledge Object repository create returned no result data."
            )

        if len(records) != 1:
            raise RuntimeError(
                "Knowledge Object repository create did not return "
                "exactly one persisted row."
            )

        return records[0]

    def update(
        self,
        knowledge_object_id: str,
        values: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """
        Update an existing canonical Knowledge Object.

        Args:
            knowledge_object_id:
                AlphaOmega UUID of the Knowledge Object to update.

            values:
                Canonical Knowledge Object values to persist.

        Returns:
            Mapping:
                The updated Knowledge Object.

        Raises:
            ValueError:
                If the Knowledge Object identity or persistence
                values are missing.

            RuntimeError:
                If the Knowledge Object cannot be updated or the
                database does not return exactly one persisted row.
        """

        if (
            knowledge_object_id is None
            or not str(knowledge_object_id).strip()
        ):
            raise ValueError(
                "knowledge_object_id is required."
            )

        if values is None or not isinstance(values, Mapping):
            raise ValueError(
                "Knowledge Object persistence values are required."
            )

        if not values:
            raise ValueError(
                "Knowledge Object persistence values cannot be empty."
            )

        try:
            response = (
                self._client
                .table(self.TABLE_NAME)
                .update(dict(values))
                .eq("id", knowledge_object_id)
                .execute()
            )
        except Exception as error:
            raise RuntimeError(
                "Knowledge Object repository update failed."
            ) from error

        records = response.data

        if records is None:
            raise RuntimeError(
                "Knowledge Object repository update returned no result data."
            )

        if len(records) != 1:
            raise RuntimeError(
                "Knowledge Object repository update did not affect "
                "exactly one row."
            )

        return records[0]