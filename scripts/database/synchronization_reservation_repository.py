"""
AlphaOmega Synchronization Reservation Repository

Purpose:
    Provides the database boundary for atomically reserving one admitted
    synchronization scope.

Responsibilities:
    - Invoke the authoritative reserve_synchronization database RPC.
    - Submit the admitted Source and Source Container identities.
    - Submit Processing Job pipeline version and metadata.
    - Return the Processing Job and Synchronization Run identities created
      by the database reservation.
    - Preserve the database transaction as the authoritative reservation
      boundary.

Does NOT:
    - Perform persisted synchronization admission.
    - Communicate with a Source of Truth.
    - Perform preliminary conflict detection.
    - Determine hierarchy overlap in Python.
    - Create Processing Jobs independently.
    - Create Synchronization Runs independently.
    - Execute synchronization.
"""


class SynchronizationReservationRepository:
    """
    Reserve one synchronization scope through the atomic database boundary.
    """

    RPC_NAME = "reserve_synchronization"

    def __init__(
        self,
        client,
    ):
        """
        Initialize with an authenticated AlphaOmega database client.
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
        source_container_id,
        pipeline_version,
        metadata,
    ):
        """
        Atomically reserve one admitted synchronization scope.

        Returns:
            dict:
                processing_job_id
                sync_run_id
                source_id
                source_container_id
        """

        source_id = self._require_text(
            source_id,
            "source_id",
        )

        source_container_id = self._require_text(
            source_container_id,
            "source_container_id",
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

                        "p_source_container_id":
                            source_container_id,

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
                "Synchronization reservation failed."
            ) from error

        result = response.data

        if not isinstance(
            result,
            dict,
        ):
            raise RuntimeError(
                "Synchronization reservation returned "
                "an invalid result."
            )

        required_fields = (
            "processing_job_id",
            "sync_run_id",
            "source_id",
            "source_container_id",
        )

        for field_name in required_fields:

            value = result.get(
                field_name
            )

            if (
                value is None
                or not str(
                    value
                ).strip()
            ):
                raise RuntimeError(
                    "Synchronization reservation returned "
                    f"no {field_name}."
                )

        return {
            "processing_job_id":
                str(
                    result[
                        "processing_job_id"
                    ]
                ).strip(),

            "sync_run_id":
                str(
                    result[
                        "sync_run_id"
                    ]
                ).strip(),

            "source_id":
                str(
                    result[
                        "source_id"
                    ]
                ).strip(),

            "source_container_id":
                str(
                    result[
                        "source_container_id"
                    ]
                ).strip(),
        }

    @staticmethod
    def _require_text(
        value,
        field_name,
    ):
        """
        Require and normalize one non-empty identifier or text value.
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