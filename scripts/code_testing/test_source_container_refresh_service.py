"""
Controlled test for SourceContainerRefreshService.

Validates:

- Source Refresh reservation
- complete enumeration
- observation validation
- catalog retrieval
- reconciliation
- atomic persistence request
- Processing Job completion
- reconciliation results
- operational measurements
- Processing Job failure handling
"""

from scripts.sync.source_container_refresh_service import (
    SourceContainerRefreshService,
)


class FakeReservationRepository:

    def __init__(self):
        self.values = None

    def reserve(
        self,
        **values,
    ):
        self.values = values
        return "job-1"


class FakeEnumerator:

    def enumerate(self):
        return {
            "enumeration_complete":
                True,

            "containers": [
                {
                    "source_object_id":
                        "new",

                    "parent_source_object_id":
                        None,

                    "name":
                        "New",
                },
                {
                    "source_object_id":
                        "existing",

                    "parent_source_object_id":
                        None,

                    "name":
                        "Existing Updated",
                },
                {
                    "source_object_id":
                        "returning",

                    "parent_source_object_id":
                        None,

                    "name":
                        "Returning",
                },
            ],
        }


class FakeValidator:

    def validate(
        self,
        observation,
    ):
        return observation[
            "containers"
        ]


class FakeContainerRepository:

    def find_by_source(
        self,
        source_id,
    ):
        if source_id != "source-1":
            raise AssertionError(
                "Unexpected Source ID."
            )

        return [
            {
                "source_object_id":
                    "existing",

                "is_active":
                    True,
            },
            {
                "source_object_id":
                    "returning",

                "is_active":
                    False,
            },
            {
                "source_object_id":
                    "absent",

                "is_active":
                    True,
            },
        ]


class FakeReconciler:

    def reconcile(
        self,
        *,
        observed_containers,
        existing_containers,
    ):
        observed = {
            item["source_object_id"]:
                item
            for item
            in observed_containers
        }

        existing = {
            item["source_object_id"]:
                item
            for item
            in existing_containers
        }

        return {
            "new": [
                {
                    "observed":
                        observed["new"],
                },
            ],

            "existing": [
                {
                    "existing":
                        existing["existing"],

                    "observed":
                        observed["existing"],
                },
            ],

            "reappearing": [
                {
                    "existing":
                        existing["returning"],

                    "observed":
                        observed["returning"],
                },
            ],

            "absent": [
                {
                    "existing":
                        existing["absent"],
                },
            ],
        }


class FakeProcessingJobRepository:

    def __init__(self):
        self.completed = None
        self.failed = None

    def complete(
        self,
        processing_job_id,
    ):
        self.completed = (
            processing_job_id
        )

    def fail(
        self,
        processing_job_id,
        error,
    ):
        self.failed = (
            processing_job_id,
            error,
        )


class FakeResponse:

    data = {
        "upserted":
            3,

        "deactivated":
            1,
    }


class FakeRpc:

    def execute(self):
        return FakeResponse()


class FakeDatabaseClient:

    def __init__(self):
        self.name = None
        self.values = None

    def rpc(
        self,
        name,
        values,
    ):
        self.name = name
        self.values = values

        return FakeRpc()


class FailingRpc:

    def execute(self):
        raise RuntimeError(
            "controlled persistence failure"
        )


class FailingDatabaseClient:

    def rpc(
        self,
        name,
        values,
    ):
        return FailingRpc()


def verify_measurements(
    measurements,
):
    """
    Verify that every required operational measurement was returned.
    Exact elapsed values are intentionally not asserted.
    """

    expected_measurements = {
        "payload_size_bytes",
        "reservation_seconds",
        "enumeration_seconds",
        "validation_seconds",
        "catalog_read_seconds",
        "reconciliation_seconds",
        "persistence_seconds",
        "completion_seconds",
        "total_seconds",
    }

    if set(measurements) != expected_measurements:
        raise AssertionError(
            "Refresh measurements do not contain "
            "the expected fields."
        )

    if (
        not isinstance(
            measurements[
                "payload_size_bytes"
            ],
            int,
        )
        or measurements[
            "payload_size_bytes"
        ] <= 0
    ):
        raise AssertionError(
            "Payload size must be a positive integer."
        )

    duration_names = (
        expected_measurements
        - {
            "payload_size_bytes",
        }
    )

    for duration_name in duration_names:

        duration = measurements[
            duration_name
        ]

        if (
            not isinstance(
                duration,
                (int, float),
            )
            or duration < 0
        ):
            raise AssertionError(
                f"{duration_name} must be a "
                "non-negative duration."
            )

    measured_stage_total = sum(
        measurements[
            duration_name
        ]
        for duration_name in (
            "reservation_seconds",
            "enumeration_seconds",
            "validation_seconds",
            "catalog_read_seconds",
            "reconciliation_seconds",
            "persistence_seconds",
            "completion_seconds",
        )
    )

    if (
        measurements[
            "total_seconds"
        ]
        < measured_stage_total
    ):
        raise AssertionError(
            "Total Refresh duration cannot be less "
            "than the measured stage durations."
        )


def test_success_path():

    reservation = (
        FakeReservationRepository()
    )

    jobs = (
        FakeProcessingJobRepository()
    )

    database = (
        FakeDatabaseClient()
    )

    service = (
        SourceContainerRefreshService(
            enumerator=(
                FakeEnumerator()
            ),

            observation_validator=(
                FakeValidator()
            ),

            source_container_repository=(
                FakeContainerRepository()
            ),

            reconciler=(
                FakeReconciler()
            ),

            refresh_reservation_repository=(
                reservation
            ),

            processing_job_repository=(
                jobs
            ),

            database_client=database,

            process_type=(
                "source_container_refresh"
            ),

            pipeline_version=(
                "lab8"
            ),
        )
    )

    result = service.refresh(
        source_id="source-1",

        job_metadata={
            "operation":
                "controlled_test",
        },
    )

    assert result[
        "processing_job_id"
    ] == "job-1"

    assert result[
        "source_id"
    ] == "source-1"

    assert result[
        "observed"
    ] == 3

    assert result[
        "new"
    ] == 1

    assert result[
        "existing"
    ] == 1

    assert result[
        "reappearing"
    ] == 1

    assert result[
        "absent"
    ] == 1

    assert result[
        "persistence"
    ] == {
        "upserted":
            3,

        "deactivated":
            1,
    }

    verify_measurements(
        result[
            "measurements"
        ]
    )

    assert reservation.values == {
        "source_id":
            "source-1",

        "process_type":
            "source_container_refresh",

        "pipeline_version":
            "lab8",

        "metadata": {
            "operation":
                "controlled_test",
        },
    }

    assert jobs.completed == "job-1"
    assert jobs.failed is None

    assert (
        database.name
        == "apply_source_container_refresh"
    )

    assert (
        database.values[
            "p_source_id"
        ]
        == "source-1"
    )

    assert (
        database.values[
            "p_processing_job_id"
        ]
        == "job-1"
    )

    assert (
        database.values[
            "p_observation_complete"
        ]
        is True
    )

    assert (
        database.values[
            "p_absent_source_object_ids"
        ]
        == [
            "absent",
        ]
    )

    assert len(
        database.values[
            "p_upsert_containers"
        ]
    ) == 3

    print(
        "Source Container Refresh service "
        "success path: PASS"
    )


def test_failure_path():

    failed_jobs = (
        FakeProcessingJobRepository()
    )

    service = (
        SourceContainerRefreshService(
            enumerator=(
                FakeEnumerator()
            ),

            observation_validator=(
                FakeValidator()
            ),

            source_container_repository=(
                FakeContainerRepository()
            ),

            reconciler=(
                FakeReconciler()
            ),

            refresh_reservation_repository=(
                FakeReservationRepository()
            ),

            processing_job_repository=(
                failed_jobs
            ),

            database_client=(
                FailingDatabaseClient()
            ),

            process_type=(
                "source_container_refresh"
            ),

            pipeline_version=(
                "lab8"
            ),
        )
    )

    try:
        service.refresh(
            source_id="source-1"
        )

        raise AssertionError(
            "Expected controlled persistence failure."
        )

    except RuntimeError as error:

        assert (
            str(error)
            == "controlled persistence failure"
        )

    assert failed_jobs.completed is None

    assert failed_jobs.failed is not None

    assert (
        failed_jobs.failed[0]
        == "job-1"
    )

    assert isinstance(
        failed_jobs.failed[1],
        RuntimeError,
    )

    print(
        "Source Container Refresh service "
        "failure path: PASS"
    )


def main():

    test_success_path()
    test_failure_path()

    print(
        "Source Container Refresh service "
        "controlled test: PASS"
    )


if __name__ == "__main__":
    main()