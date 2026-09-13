"""
AlphaOmega Processing Job Repository

Purpose:
    Provides database persistence operations for AlphaOmega Processing Jobs.

Responsibilities:
    - Create Processing Job records.
    - Mark Processing Jobs completed.
    - Mark Processing Jobs failed.
    - Validate Processing Job identity and expected update results.
    - Own storage-specific lifecycle updates against the processing_jobs table.

Does NOT:
    - Decide when a Processing Job should be created.
    - Coordinate synchronization stages.
    - Determine synchronization success or failure.
    - Execute Connector, Translator, Discovery, Extraction, or Load.
    - Generate synchronization correlation identity.
"""

from datetime import datetime, timezone


class ProcessingJobRepository:
    """
    Persist Processing Job lifecycle state.
    """

    def __init__(
        self,
        client,
    ):
        """
        Initialize the repository.

        Args:
            client:
                Authenticated AlphaOmega database client.
        """

        if client is None:
            raise ValueError(
                "Database client is required."
            )

        self._client = client

    def create(
        self,
        *,
        process_type,
        pipeline_version,
        metadata=None,
    ):
        """
        Create one running Processing Job.

        Returns:
            str:
                Database-generated Processing Job UUID.
        """

        if (
            process_type is None
            or not str(
                process_type
            ).strip()
        ):
            raise ValueError(
                "process_type is required."
            )

        if (
            pipeline_version is None
            or not str(
                pipeline_version
            ).strip()
        ):
            raise ValueError(
                "pipeline_version is required."
            )

        if metadata is None:
            metadata = {}

        response = (
            self._client
            .table(
                "processing_jobs"
            )
            .insert(
                {
                    "process_type":
                        str(
                            process_type
                        ).strip(),

                    "status":
                        "running",

                    "pipeline_version":
                        str(
                            pipeline_version
                        ).strip(),

                    "metadata":
                        metadata,
                }
            )
            .execute()
        )

        records = response.data

        if (
            records is None
            or len(records) != 1
        ):
            raise RuntimeError(
                "Unable to create Processing Job."
            )

        processing_job_id = (
            records[0].get(
                "id"
            )
        )

        if (
            processing_job_id is None
            or not str(
                processing_job_id
            ).strip()
        ):
            raise RuntimeError(
                "Created Processing Job did not return an ID."
            )

        return processing_job_id

    def complete(
        self,
        processing_job_id,
    ):
        """
        Mark one Processing Job completed.
        """

        self._validate_processing_job_id(
            processing_job_id
        )

        completed_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        response = (
            self._client
            .table(
                "processing_jobs"
            )
            .update(
                {
                    "status":
                        "completed",

                    "completed_at":
                        completed_at,

                    "error_message":
                        None,
                }
            )
            .eq(
                "id",
                processing_job_id,
            )
            .execute()
        )

        self._validate_single_update(
            response=response,
            action="complete",
        )

    def fail(
        self,
        processing_job_id,
        error,
    ):
        """
        Mark one Processing Job failed.
        """

        self._validate_processing_job_id(
            processing_job_id
        )

        if error is None:
            raise ValueError(
                "Processing Job failure error is required."
            )

        completed_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        response = (
            self._client
            .table(
                "processing_jobs"
            )
            .update(
                {
                    "status":
                        "failed",

                    "completed_at":
                        completed_at,

                    "error_message":
                        str(
                            error
                        ),
                }
            )
            .eq(
                "id",
                processing_job_id,
            )
            .execute()
        )

        self._validate_single_update(
            response=response,
            action="fail",
        )

    @staticmethod
    def _validate_processing_job_id(
        processing_job_id,
    ):
        """
        Validate Processing Job identity.
        """

        if (
            processing_job_id is None
            or not str(
                processing_job_id
            ).strip()
        ):
            raise ValueError(
                "processing_job_id is required."
            )

    @staticmethod
    def _validate_single_update(
        *,
        response,
        action,
    ):
        """
        Verify exactly one Processing Job was updated.
        """

        records = getattr(
            response,
            "data",
            None,
        )

        if (
            records is None
            or len(records) != 1
        ):
            raise RuntimeError(
                f"Unable to {action} Processing Job."
            )