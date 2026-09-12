"""
Controlled database-backed test for SourceContainerRefreshService.

The test:

1. Creates one disposable Source.
2. Uses a fake complete Container observation.
3. Runs the production reservation and Refresh database functions.
4. Verifies the Containers and completed Processing Job.
5. Removes every disposable record in finally.

No Microsoft Graph connection is used.
"""


from datetime import datetime, timezone
from uuid import uuid4

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)

from scripts.database.processing_job_repository import (
    ProcessingJobRepository,
)

from scripts.database.source_container_repository import (
    SourceContainerRepository,
)

from scripts.database.source_container_refresh_reservation_repository import (
    SourceContainerRefreshReservationRepository,
)

from scripts.sync.source_container_observation_validator import (
    SourceContainerObservationValidator,
)

from scripts.sync.source_container_reconciler import (
    SourceContainerReconciler,
)

from scripts.sync.source_container_refresh_service import (
    SourceContainerRefreshService,
)


class ExistingDatabaseConnection:
    """
    Supply an existing authenticated client to repositories that
    expect DatabaseConnection.connect().
    """

    def __init__(
        self,
        client,
    ):
        self._client = client

    def connect(self):
        return self._client


class ControlledEnumerator:
    """
    Return one complete disposable Source Container observation.
    """

    def __init__(
        self,
        root_id,
        child_id,
    ):
        self._root_id = root_id
        self._child_id = child_id

    def enumerate(self):

        return {
            "enumeration_complete":
                True,

            "delta_link":
                "controlled-database-test",

            "containers": [
                {
                    "source_object_id":
                        self._root_id,

                    "parent_source_object_id":
                        None,

                    "name":
                        "Controlled Root",
                },
                {
                    "source_object_id":
                        self._child_id,

                    "parent_source_object_id":
                        self._root_id,

                    "name":
                        "Controlled Child",
                },
            ],
        }


def delete_disposable_records(
    client,
    source_id,
):
    """
    Remove disposable records in foreign-key-safe order.
    """

    if source_id is None:
        return

    (
        client
        .table(
            "source_containers"
        )
        .delete()
        .eq(
            "source_id",
            source_id,
        )
        .execute()
    )

    (
        client
        .table(
            "processing_jobs"
        )
        .delete()
        .eq(
            "source_id",
            source_id,
        )
        .execute()
    )

    (
        client
        .table(
            "sources"
        )
        .delete()
        .eq(
            "id",
            source_id,
        )
        .execute()
    )


def main():

    credential_provider = (
        LocalCredentialProvider()
    )

    database_connection = (
        DatabaseConnection(
            credential_provider
        )
    )

    client = database_connection.connect()

    source_id = str(
        uuid4()
    )

    root_source_object_id = (
        f"controlled-root-{uuid4()}"
    )

    child_source_object_id = (
        f"controlled-child-{uuid4()}"
    )

    test_name = (
        f"lab8-controlled-refresh-{uuid4()}"
    )

    now = datetime.now(
        timezone.utc
    ).isoformat()

    try:

        # -----------------------------------------------------
        # Create one isolated disposable Source.
        # -----------------------------------------------------

        source_response = (
            client
            .table(
                "sources"
            )
            .insert(
                {
                    "id":
                        source_id,

                    "name":
                        test_name,

                    "source_type":
                        "onedrive",

                    "description":
                        "Disposable Lab 8 Refresh test Source.",

                    "is_enabled":
                        False,

                    "created_at":
                        now,

                    "updated_at":
                        now,

                    "last_sync_at":
                        None,

                    "metadata": {
                        "test":
                            True,
                    },
                }
            )
            .execute()
        )

        if (
            source_response.data is None
            or len(
                source_response.data
            ) != 1
        ):
            raise RuntimeError(
                "Disposable Source was not created."
            )

        source_container_repository = (
            SourceContainerRepository(
                ExistingDatabaseConnection(
                    client
                )
            )
        )

        processing_job_repository = (
            ProcessingJobRepository(
                client
            )
        )

        reservation_repository = (
            SourceContainerRefreshReservationRepository(
                client
            )
        )

        service = SourceContainerRefreshService(
            enumerator=(
                ControlledEnumerator(
                    root_source_object_id,
                    child_source_object_id,
                )
            ),
            observation_validator=(
                SourceContainerObservationValidator()
            ),
            source_container_repository=(
                source_container_repository
            ),
            reconciler=(
                SourceContainerReconciler()
            ),
            refresh_reservation_repository=(
                reservation_repository
            ),
            processing_job_repository=(
                processing_job_repository
            ),
            database_client=(
                client
            ),
            process_type=(
                "source_container_refresh"
            ),
            pipeline_version=(
                "lab8-database-test"
            ),
        )

        result = service.refresh(
            source_id=source_id,
            job_metadata={
                "test":
                    "controlled-database-refresh",
            },
        )

        # -----------------------------------------------------
        # Verify the service result.
        # -----------------------------------------------------

        assert result[
            "source_id"
        ] == source_id

        assert result[
            "observed"
        ] == 2

        assert result[
            "new"
        ] == 2

        assert result[
            "existing"
        ] == 0

        assert result[
            "reappearing"
        ] == 0

        assert result[
            "absent"
        ] == 0

        assert result[
            "persistence"
        ] == {
            "upserted":
                2,

            "deactivated":
                0,
        }

        processing_job_id = result[
            "processing_job_id"
        ]

        # -----------------------------------------------------
        # Verify persisted Source Containers.
        # -----------------------------------------------------

        containers = (
            client
            .table(
                "source_containers"
            )
            .select(
                "*"
            )
            .eq(
                "source_id",
                source_id,
            )
            .execute()
            .data
            or []
        )

        assert len(
            containers
        ) == 2

        containers_by_identity = {
            container[
                "source_object_id"
            ]:
                container

            for container in containers
        }

        assert set(
            containers_by_identity
        ) == {
            root_source_object_id,
            child_source_object_id,
        }

        for container in containers:

            assert container[
                "is_active"
            ] is True

            assert container[
                "last_seen_processing_job_id"
            ] == processing_job_id

        assert containers_by_identity[
            child_source_object_id
        ][
            "parent_source_object_id"
        ] == root_source_object_id

        # -----------------------------------------------------
        # Verify the completed Processing Job.
        # -----------------------------------------------------

        job_response = (
            client
            .table(
                "processing_jobs"
            )
            .select(
                "*"
            )
            .eq(
                "id",
                processing_job_id,
            )
            .execute()
        )

        jobs = job_response.data or []

        assert len(
            jobs
        ) == 1

        job = jobs[0]

        assert job[
            "source_id"
        ] == source_id

        assert job[
            "process_type"
        ] == "source_container_refresh"

        assert job[
            "status"
        ] == "completed"

        assert job[
            "completed_at"
        ] is not None

        assert job[
            "error_message"
        ] is None

        print(
            "Source Container Refresh "
            "database test: PASS"
        )

    finally:

        delete_disposable_records(
            client,
            source_id,
        )

        remaining_sources = (
            client
            .table(
                "sources"
            )
            .select(
                "id"
            )
            .eq(
                "id",
                source_id,
            )
            .execute()
            .data
            or []
        )

        if remaining_sources:
            raise RuntimeError(
                "Controlled Refresh test cleanup failed."
            )

        print(
            "Source Container Refresh "
            "database cleanup: PASS"
        )


if __name__ == "__main__":
    main()