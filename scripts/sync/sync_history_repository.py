"""
AlphaOmega Synchronization History Repository

Purpose:
    Provides database persistence operations for synchronization history.

Responsibilities:
    - Create synchronization history records.
    - Persist the factual synchronization event data supplied by Load.
    - Own storage-specific operations against the sync_history table.
    - Validate required persistence inputs and database results.

Does NOT:
    - Determine synchronization state.
    - Decide whether synchronization history should be created.
    - Modify Knowledge Objects.
    - Execute synchronization stages.
"""

from typing import Any, Mapping

from supabase import Client


class SyncHistoryRepository:
    """
    Provide repository access to AlphaOmega synchronization history.
    """

    TABLE_NAME = "sync_history"

    def __init__(self, client: Client):
        """
        Initialize the Synchronization History repository.

        Args:
            client:
                Authenticated Supabase client constrained by RLS.
        """

        if client is None:
            raise ValueError(
                "Authenticated Supabase client is required."
            )

        self._client = client

    def create(
        self,
        values: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """
        Create a synchronization history event.

        The database owns generation of the synchronization
        history UUID.

        Args:
            values:
                Synchronization history values to persist.

        Returns:
            Mapping:
                The persisted synchronization history record.

        Raises:
            ValueError:
                If persistence values are missing.

            RuntimeError:
                If the synchronization history event cannot be
                created or the database does not return exactly
                one persisted row.
        """

        if values is None or not isinstance(values, Mapping):
            raise ValueError(
                "Synchronization history persistence values are required."
            )

        if not values:
            raise ValueError(
                "Synchronization history persistence values cannot be empty."
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
                "Synchronization history repository create failed."
            ) from error

        records = response.data

        if records is None:
            raise RuntimeError(
                "Synchronization history repository create returned "
                "no result data."
            )

        if len(records) != 1:
            raise RuntimeError(
                "Synchronization history repository create did not "
                "return exactly one persisted row."
            )

        return records[0]