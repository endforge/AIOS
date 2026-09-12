"""
File:
    source_repository.py

Purpose:
    Provides database access to AlphaOmega Source records required
    by synchronization and application services.
"""

from typing import Optional

from supabase import Client


class SourceRepository:
    """
    Provides repository access to AlphaOmega Sources.

    The repository performs storage-specific Source lookups.
    It does not make synchronization or application decisions.
    """

    TABLE_NAME = "sources"

    def __init__(
        self,
        client: Client,
    ):
        """
        Initialize the Source repository.

        Args:
            client:
                Authenticated Supabase client constrained by RLS.
        """

        if client is None:
            raise ValueError(
                "Authenticated Supabase client is required."
            )

        self._client = client

    def find_id_by_name(
        self,
        source_name: str,
    ) -> Optional[str]:
        """
        Resolve an AlphaOmega Source ID using its canonical source name.

        Args:
            source_name:
                Canonical Source of Truth name.

        Returns:
            str:
                AlphaOmega UUID identifying the Source of Truth.

            None:
                No Source exists with the supplied name.

        Raises:
            ValueError:
                If source_name is missing.

            RuntimeError:
                If the repository lookup cannot be completed or
                multiple Sources exist with the same name.
        """

        if (
            source_name is None
            or not str(
                source_name
            ).strip()
        ):
            raise ValueError(
                "source_name is required."
            )

        try:
            response = (
                self._client
                .table(
                    self.TABLE_NAME
                )
                .select(
                    "id"
                )
                .eq(
                    "name",
                    str(
                        source_name
                    ).strip(),
                )
                .limit(
                    2
                )
                .execute()
            )

        except Exception as error:
            raise RuntimeError(
                "Source repository lookup failed."
            ) from error

        records = response.data

        if records is None:
            raise RuntimeError(
                "Source repository returned no result data."
            )

        if len(records) == 0:
            return None

        if len(records) > 1:
            raise RuntimeError(
                "Multiple Sources were found with the same name."
            )

        return records[0][
            "id"
        ]

    def find_by_id(
        self,
        source_id,
    ):
        """
        Find one registered AlphaOmega Source by UUID.
        """

        if (
            source_id is None
            or not str(
                source_id
            ).strip()
        ):
            raise ValueError(
                "source_id is required."
            )

        source_id = (
            str(
                source_id
            ).strip()
        )

        try:
            response = (
                self._client
                .table(
                    self.TABLE_NAME
                )
                .select(
                    "id,"
                    "name,"
                    "source_type,"
                    "description,"
                    "is_enabled"
                )
                .eq(
                    "id",
                    source_id,
                )
                .limit(
                    2
                )
                .execute()
            )

        except Exception as error:
            raise RuntimeError(
                "Source repository lookup failed."
            ) from error

        records = response.data

        if records is None:
            raise RuntimeError(
                "Source repository returned no result data."
            )

        if len(records) == 0:
            return None

        if len(records) > 1:
            raise RuntimeError(
                "Multiple Sources were found with the same ID."
            )

        return records[0]

    def find_enabled(
        self,
    ):
        """
        Return every enabled registered AlphaOmega Source.

        Sources are returned in canonical name order.
        """

        try:
            response = (
                self._client
                .table(
                    self.TABLE_NAME
                )
                .select(
                    "id,"
                    "name,"
                    "source_type,"
                    "description,"
                    "is_enabled"
                )
                .eq(
                    "is_enabled",
                    True,
                )
                .order(
                    "name"
                )
                .execute()
            )

        except Exception as error:
            raise RuntimeError(
                "Source repository lookup failed."
            ) from error

        records = response.data

        if records is None:
            raise RuntimeError(
                "Source repository returned no result data."
            )

        return records