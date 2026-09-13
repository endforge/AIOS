"""
AlphaOmega Synchronization Run Repository

Purpose:
    Provides database read operations for persisted AlphaOmega
    Synchronization Runs.

Responsibilities:
    - Read Synchronization Runs for one registered Source.
    - Determine which Synchronization Runs have running Processing Jobs.
    - Return active synchronization scope using persisted AlphaOmega
      Source Container identities.
    - Keep synchronization-specific persistence access isolated from
      application services.

Does NOT:
    - Create Synchronization Runs.
    - Create or update Processing Jobs.
    - Determine synchronization scope conflicts.
    - Reserve synchronization execution.
    - Execute synchronization.
    - Access a Source of Truth.
"""


class SyncRunRepository:
    """
    Read persisted Synchronization Run state.
    """

    def __init__(
        self,
        client,
    ):
        """
        Initialize the repository with an authenticated database client.
        """

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
        Return Synchronization Runs for one Source whose associated
        Processing Jobs are currently running.

        Returns:
            tuple[dict, ...]:
                Persisted Synchronization Run records containing:

                - id
                - processing_job_id
                - source_id
                - source_container_id
        """

        source_id = self._require_identifier(
            source_id,
            "source_id",
        )

        sync_run_response = (
            self._client
            .table(
                "sync_runs"
            )
            .select(
                "id,"
                "processing_job_id,"
                "source_id,"
                "source_container_id"
            )
            .eq(
                "source_id",
                source_id,
            )
            .execute()
        )

        sync_runs = (
            sync_run_response.data
            or []
        )

        if not sync_runs:
            return ()

        processing_job_ids = []

        seen_processing_job_ids = set()

        for sync_run in sync_runs:

            processing_job_id = (
                self._require_record_identifier(
                    sync_run,
                    "processing_job_id",
                )
            )

            if (
                processing_job_id
                in seen_processing_job_ids
            ):
                continue

            seen_processing_job_ids.add(
                processing_job_id
            )

            processing_job_ids.append(
                processing_job_id
            )

        processing_job_response = (
            self._client
            .table(
                "processing_jobs"
            )
            .select(
                "id,status"
            )
            .in_(
                "id",
                processing_job_ids,
            )
            .eq(
                "status",
                "running",
            )
            .execute()
        )

        active_jobs = (
            processing_job_response.data
            or []
        )

        active_processing_job_ids = {
            self._require_record_identifier(
                job,
                "id",
            )
            for job in active_jobs
        }

        return tuple(
            sync_run
            for sync_run in sync_runs
            if str(
                sync_run[
                    "processing_job_id"
                ]
            ).strip()
            in active_processing_job_ids
        )

    def find_active_source_container_ids_by_source(
        self,
        source_id,
    ):
        """
        Return the AlphaOmega Source Container IDs currently reserved
        by running Synchronization Runs for one Source.
        """

        active_runs = (
            self.find_active_by_source(
                source_id
            )
        )

        return tuple(
            self._require_record_identifier(
                sync_run,
                "source_container_id",
            )
            for sync_run in active_runs
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

    @staticmethod
    def _require_record_identifier(
        record,
        field_name,
    ):
        """
        Require one identifier from a persisted database record.
        """

        if not isinstance(
            record,
            dict,
        ):
            raise RuntimeError(
                "Persisted database records must be dictionaries."
            )

        value = record.get(
            field_name
        )

        if (
            value is None
            or not str(
                value
            ).strip()
        ):
            raise RuntimeError(
                "Persisted database record is missing "
                f"{field_name}."
            )

        return str(
            value
        ).strip()