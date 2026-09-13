"""
Synchronization Reservation Repository Test

Purpose:
    Validates SynchronizationReservationRepository using controlled
    database RPC behavior.

Verifies:
    - Synchronization reservation invokes the authoritative database RPC.
    - Source and Source Container identities are passed correctly.
    - Pipeline version and metadata are passed correctly.
    - Successful reservation returns both operational identities.
    - Required reservation inputs are validated.
    - Invalid RPC results are rejected.
    - Database failures are surfaced as reservation failures.

Does NOT:
    - Connect to the live AlphaOmega database.
    - Test PostgreSQL hierarchy conflict logic.
    - Create real Processing Jobs.
    - Create real Synchronization Runs.
    - Execute synchronization.
"""

from scripts.database.synchronization_reservation_repository import (
    SynchronizationReservationRepository,
)


SOURCE_ID = (
    "11111111-1111-1111-1111-111111111111"
)

SOURCE_CONTAINER_ID = (
    "22222222-2222-2222-2222-222222222222"
)

PROCESSING_JOB_ID = (
    "33333333-3333-3333-3333-333333333333"
)

SYNC_RUN_ID = (
    "44444444-4444-4444-4444-444444444444"
)


class FakeResponse:

    def __init__(
        self,
        data,
    ):
        self.data = data


class FakeRpcRequest:

    def __init__(
        self,
        response,
        error=None,
    ):
        self._response = response
        self._error = error

    def execute(
        self,
    ):

        if self._error is not None:
            raise self._error

        return self._response


class FakeDatabaseClient:

    def __init__(
        self,
        *,
        response_data=None,
        error=None,
    ):
        self.response_data = response_data
        self.error = error

        self.rpc_name = None
        self.rpc_arguments = None

    def rpc(
        self,
        rpc_name,
        rpc_arguments,
    ):
        self.rpc_name = rpc_name
        self.rpc_arguments = rpc_arguments

        return FakeRpcRequest(
            FakeResponse(
                self.response_data
            ),
            self.error,
        )


def require_equal(
    *,
    actual,
    expected,
    test_name,
):
    """
    Require one deterministic test result.
    """

    if actual != expected:
        raise RuntimeError(
            f"{test_name} failed. "
            f"Expected {expected}, "
            f"received {actual}."
        )

    print(
        f"PASS: {test_name}"
    )


def test_successful_reservation():
    """
    Verify RPC invocation and successful result mapping.
    """

    client = FakeDatabaseClient(
        response_data={
            "processing_job_id":
                PROCESSING_JOB_ID,

            "sync_run_id":
                SYNC_RUN_ID,

            "source_id":
                SOURCE_ID,

            "source_container_id":
                SOURCE_CONTAINER_ID,
        }
    )

    repository = (
        SynchronizationReservationRepository(
            client
        )
    )

    result = repository.reserve(
        source_id=SOURCE_ID,
        source_container_id=(
            SOURCE_CONTAINER_ID
        ),
        pipeline_version=(
            "lab8-synchronization"
        ),
        metadata={
            "requested_by":
                "controlled-test",
        },
    )

    require_equal(
        actual=client.rpc_name,
        expected="reserve_synchronization",
        test_name=(
            "Correct synchronization reservation RPC invoked"
        ),
    )

    require_equal(
        actual=client.rpc_arguments,
        expected={
            "p_source_id":
                SOURCE_ID,

            "p_source_container_id":
                SOURCE_CONTAINER_ID,

            "p_pipeline_version":
                "lab8-synchronization",

            "p_metadata": {
                "requested_by":
                    "controlled-test",
            },
        },
        test_name=(
            "Reservation arguments preserved"
        ),
    )

    require_equal(
        actual=result[
            "processing_job_id"
        ],
        expected=PROCESSING_JOB_ID,
        test_name=(
            "Processing Job identity returned"
        ),
    )

    require_equal(
        actual=result[
            "sync_run_id"
        ],
        expected=SYNC_RUN_ID,
        test_name=(
            "Synchronization Run identity returned"
        ),
    )

    require_equal(
        actual=result[
            "source_id"
        ],
        expected=SOURCE_ID,
        test_name=(
            "Source identity returned"
        ),
    )

    require_equal(
        actual=result[
            "source_container_id"
        ],
        expected=SOURCE_CONTAINER_ID,
        test_name=(
            "Source Container identity returned"
        ),
    )


def test_required_inputs():
    """
    Verify required input validation.
    """

    repository = (
        SynchronizationReservationRepository(
            FakeDatabaseClient()
        )
    )

    test_cases = (
        {
            "source_id":
                "",

            "source_container_id":
                SOURCE_CONTAINER_ID,

            "pipeline_version":
                "lab8",

            "metadata":
                {},

            "name":
                "Missing source_id rejected",
        },
        {
            "source_id":
                SOURCE_ID,

            "source_container_id":
                "",

            "pipeline_version":
                "lab8",

            "metadata":
                {},

            "name":
                "Missing source_container_id rejected",
        },
        {
            "source_id":
                SOURCE_ID,

            "source_container_id":
                SOURCE_CONTAINER_ID,

            "pipeline_version":
                "",

            "metadata":
                {},

            "name":
                "Missing pipeline_version rejected",
        },
    )

    for test_case in test_cases:

        try:

            repository.reserve(
                source_id=(
                    test_case[
                        "source_id"
                    ]
                ),
                source_container_id=(
                    test_case[
                        "source_container_id"
                    ]
                ),
                pipeline_version=(
                    test_case[
                        "pipeline_version"
                    ]
                ),
                metadata=(
                    test_case[
                        "metadata"
                    ]
                ),
            )

        except ValueError:

            print(
                "PASS: "
                f"{test_case['name']}"
            )

        else:

            raise RuntimeError(
                f"{test_case['name']} failed."
            )

    try:

        repository.reserve(
            source_id=SOURCE_ID,
            source_container_id=(
                SOURCE_CONTAINER_ID
            ),
            pipeline_version="lab8",
            metadata=None,
        )

    except ValueError:

        print(
            "PASS: Invalid metadata rejected"
        )

    else:

        raise RuntimeError(
            "Invalid metadata was not rejected."
        )


def test_invalid_rpc_result():
    """
    Verify malformed database responses are rejected.
    """

    invalid_results = (
        None,
        {},
        {
            "processing_job_id":
                PROCESSING_JOB_ID,
        },
        {
            "processing_job_id":
                PROCESSING_JOB_ID,

            "sync_run_id":
                SYNC_RUN_ID,

            "source_id":
                SOURCE_ID,

            "source_container_id":
                "",
        },
    )

    for invalid_result in invalid_results:

        repository = (
            SynchronizationReservationRepository(
                FakeDatabaseClient(
                    response_data=(
                        invalid_result
                    )
                )
            )
        )

        try:

            repository.reserve(
                source_id=SOURCE_ID,
                source_container_id=(
                    SOURCE_CONTAINER_ID
                ),
                pipeline_version="lab8",
                metadata={},
            )

        except RuntimeError:

            pass

        else:

            raise RuntimeError(
                "Invalid reservation result "
                "was accepted."
            )

    print(
        "PASS: Invalid RPC results rejected"
    )


def test_database_failure():
    """
    Verify database failures remain reservation failures.
    """

    repository = (
        SynchronizationReservationRepository(
            FakeDatabaseClient(
                error=RuntimeError(
                    "controlled database failure"
                )
            )
        )
    )

    try:

        repository.reserve(
            source_id=SOURCE_ID,
            source_container_id=(
                SOURCE_CONTAINER_ID
            ),
            pipeline_version="lab8",
            metadata={},
        )

    except RuntimeError as error:

        require_equal(
            actual=str(
                error
            ),
            expected=(
                "Synchronization reservation failed."
            ),
            test_name=(
                "Database failure propagated through reservation boundary"
            ),
        )

        return

    raise RuntimeError(
        "Database failure was not propagated."
    )


def main():

    print()
    print(
        "AlphaOmega Synchronization Reservation Repository Test"
    )
    print(
        "======================================================"
    )
    print()

    test_successful_reservation()
    test_required_inputs()
    test_invalid_rpc_result()
    test_database_failure()

    print()
    print(
        "SYNCHRONIZATION RESERVATION REPOSITORY TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()