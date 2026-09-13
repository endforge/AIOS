"""
AlphaOmega Source Container Refresh Status Repository

Purpose:
    Provides read-only database access to active Source Container Refresh
    state for registered AlphaOmega Sources.

Responsibilities:
    - Read running Source Container Refresh Processing Jobs.
    - Limit Refresh status lookup to one requested Source.
    - Determine whether a complete-Source Refresh is currently active.
    - Return the active Refresh Processing Job identities.

Does NOT:
    - Reserve a Source Container Refresh.
    - Create or update Processing Jobs.
    - Enumerate Source Containers.
    - Reconcile or persist Source Container catalogs.
    - Determine synchronization hierarchy conflicts.
    - Execute synchronization.
"""


class SourceContainerRefreshStatusRepository:
    """
    Read active whole-Source Refresh state.
    """

    PROCESS_TYPE = "source_container_refresh"
    ACTIVE_STATUS = "running"

    def __init__(
        self,
        client,
    ):
        if client is None:
            raise ValueError(
                "Database client is required."
            )

        self._client = client

    def find_active_by_source(
        self,
        source_id,
    ):
        """
        Return running Source Container Refresh Processing Jobs
        for one Source.
        """

        source_id = self._require_identifier(
            source_id,
            "source_id",
        )

        response = (
            self._client
            .table(
                "processing_jobs"
            )
            .select(
                "id,"
                "source_id,"
                "process_type,"
                "status"
            )
            .eq(
                "source_id",
                source_id,
            )
            .eq(
                "process_type",
                self.PROCESS_TYPE,
            )
            .eq(
                "status",
                self.ACTIVE_STATUS,
            )
            .execute()
        )

        rows = (
            response.data
            or []
        )

        return tuple(
            rows
        )

    def has_active_refresh(
        self,
        source_id,
    ):
        """
        Return True when the Source currently has a running
        complete Source Container Refresh.
        """

        return bool(
            self.find_active_by_source(
                source_id
            )
        )

    @staticmethod
    def _require_identifier(
        value,
        field_name,
    ):
        """
        Require a non-empty identifier.
        """

        if (
            value is None
            or not str(
                value
            ).strip()
        ):
            raise ValueError(
                f"{field_name} is required."
            )

        return str(
            value
        ).strip()