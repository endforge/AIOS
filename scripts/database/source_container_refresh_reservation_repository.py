"""
AlphaOmega Source Container Refresh Reservation Repository

Purpose:
    Provides the database boundary for atomically reserving one complete
    Source Container Refresh operation.

Responsibilities:
    - Check for an active operation against the Source through the
      database reservation operation.
    - Reserve the complete Source for Refresh.
    - Create the running Processing Job as part of the same atomic operation.
    - Return the Processing Job identity created by the reservation.
    - Invoke the reserve_source_container_refresh database RPC.

Does NOT:
    - Enumerate Source Containers.
    - Reconcile the Source Container Catalog.
    - Apply catalog changes.
    - Complete or fail Processing Jobs.
"""


class SourceContainerRefreshReservationRepository:
    """
    Reserve one whole-Source Container Refresh operation.
    """

    RPC_NAME = "reserve_source_container_refresh"

    def __init__(
        self,
        client,
    ):
        """
        Initialize the repository with an authenticated database client.
        """

        if client is None:
            raise ValueError(
                "Authenticated database client is required."
            )

        self._client = client

    def reserve(
        self,
        *,
        source_id,
        process_type,
        pipeline_version,
        metadata,
    ):
        """
        Reserve the Source and create its running Processing Job.

        Returns:
            str:
                The Processing Job UUID created by the database.

        Raises:
            ValueError:
                If required input is missing or invalid.

            RuntimeError:
                If the database cannot reserve the operation.
        """

        source_id = self._require_text(
            source_id,
            "source_id",
        )

        process_type = self._require_text(
            process_type,
            "process_type",
        )

        pipeline_version = self._require_text(
            pipeline_version,
            "pipeline_version",
        )

        if not isinstance(
            metadata,
            dict,
        ):
            raise ValueError(
                "metadata must be a dictionary."
            )

        try:

            response = (
                self._client
                .rpc(
                    self.RPC_NAME,
                    {
                        "p_source_id":
                            source_id,

                        "p_process_type":
                            process_type,

                        "p_pipeline_version":
                            pipeline_version,

                        "p_metadata":
                            metadata,
                    },
                )
                .execute()
            )

        except Exception as error:

            raise RuntimeError(
                "Source Container Refresh reservation failed."
            ) from error

        processing_job_id = response.data

        if (
            processing_job_id is None
            or not str(
                processing_job_id
            ).strip()
        ):
            raise RuntimeError(
                "Source Container Refresh reservation returned "
                "no Processing Job identity."
            )

        return str(
            processing_job_id
        ).strip()

    @staticmethod
    def _require_text(
        value,
        field_name,
    ):
        """
        Require and normalize a non-empty text value.
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