"""
Source Container Refresh Service Failure Test

Purpose:
    Validates controlled failure behavior of SourceContainerRefreshService.

Verifies:
    - Incomplete Source observations are rejected.
    - Failed Refresh processing causes the Processing Job to fail.
    - Failure does not proceed into successful catalog persistence.
    - Reservation and Processing Job failure behavior remain coordinated.

Does NOT:
    - Connect to a live Source of Truth.
    - Connect to the live AlphaOmega database.
    - Apply successful catalog changes.
    - Synchronize content.
"""


from scripts.sync.source_container_observation_validator import (
    SourceContainerObservationValidator,
)

from scripts.sync.source_container_reconciler import (
    SourceContainerReconciler,
)

from scripts.sync.source_container_refresh_service import (
    SourceContainerRefreshService,
)


class FakeIncompleteEnumerator:

    def enumerate(self):

        return {
            "enumeration_complete":
                False,

            "containers":
                [],
        }


class FakeSourceContainerRepository:

    def find_by_source(
        self,
        source_id,
    ):

        raise AssertionError(
            "Catalog read must not occur after "
            "observation validation fails."
        )


class FakeReservationRepository:

    def reserve(
        self,
        **values,
    ):

        return "processing-job-1"


class FakeProcessingJobRepository:

    def __init__(self):

        self.completed_job_id = None
        self.failed_job_id = None
        self.failure = None

    def complete(
        self,
        processing_job_id,
    ):

        self.completed_job_id = (
            processing_job_id
        )

    def fail(
        self,
        processing_job_id,
        error,
    ):

        self.failed_job_id = (
            processing_job_id
        )

        self.failure = error


class FakeDatabaseClient:

    def rpc(
        self,
        rpc_name,
        rpc_arguments,
    ):

        raise AssertionError(
            "Catalog persistence must not occur after "
            "observation validation fails."
        )


def main():

    processing_job_repository = (
        FakeProcessingJobRepository()
    )

    service = SourceContainerRefreshService(
        enumerator=(
            FakeIncompleteEnumerator()
        ),
        observation_validator=(
            SourceContainerObservationValidator()
        ),
        source_container_repository=(
            FakeSourceContainerRepository()
        ),
        reconciler=(
            SourceContainerReconciler()
        ),
        refresh_reservation_repository=(
            FakeReservationRepository()
        ),
        processing_job_repository=(
            processing_job_repository
        ),
        database_client=(
            FakeDatabaseClient()
        ),
        process_type=(
            "source_container_refresh"
        ),
        pipeline_version=(
            "lab8-controlled-test"
        ),
    )

    try:

        service.refresh(
            source_id="source-1"
        )

        raise AssertionError(
            "Incomplete observation was not rejected."
        )

    except ValueError as error:

        assert str(error) == (
            "Source Container enumeration "
            "is not complete."
        )

    assert processing_job_repository.completed_job_id is None

    assert processing_job_repository.failed_job_id == (
        "processing-job-1"
    )

    assert isinstance(
        processing_job_repository.failure,
        ValueError,
    )

    assert str(
        processing_job_repository.failure
    ) == (
        "Source Container enumeration "
        "is not complete."
    )

    print(
        "Source Container Refresh "
        "service failure path: PASS"
    )


if __name__ == "__main__":
    main()