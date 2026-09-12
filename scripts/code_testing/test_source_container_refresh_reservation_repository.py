"""
Controlled test for SourceContainerRefreshReservationRepository.

No database connection is used.
No records are created.
"""


from scripts.database.source_container_refresh_reservation_repository import (
    SourceContainerRefreshReservationRepository,
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

    def execute(self):

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


def main():

    processing_job_id = (
        "11111111-1111-1111-1111-111111111111"
    )

    client = FakeDatabaseClient(
        response_data=processing_job_id
    )

    repository = (
        SourceContainerRefreshReservationRepository(
            client
        )
    )

    returned_job_id = repository.reserve(
        source_id=(
            "22222222-2222-2222-2222-222222222222"
        ),
        process_type=(
            "source_container_refresh"
        ),
        pipeline_version=(
            "lab8-reservation-test"
        ),
        metadata={
            "requested_by":
                "controlled-test",
        },
    )

    assert returned_job_id == processing_job_id

    assert client.rpc_name == (
        "reserve_source_container_refresh"
    )

    assert client.rpc_arguments == {
        "p_source_id":
            "22222222-2222-2222-2222-222222222222",

        "p_process_type":
            "source_container_refresh",

        "p_pipeline_version":
            "lab8-reservation-test",

        "p_metadata": {
            "requested_by":
                "controlled-test",
        },
    }

    try:

        repository.reserve(
            source_id="",
            process_type=(
                "source_container_refresh"
            ),
            pipeline_version=(
                "lab8-reservation-test"
            ),
            metadata={},
        )

        raise AssertionError(
            "Empty source_id was not rejected."
        )

    except ValueError:
        pass

    failing_client = FakeDatabaseClient(
        error=RuntimeError(
            "controlled database failure"
        )
    )

    failing_repository = (
        SourceContainerRefreshReservationRepository(
            failing_client
        )
    )

    try:

        failing_repository.reserve(
            source_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            process_type=(
                "source_container_refresh"
            ),
            pipeline_version=(
                "lab8-reservation-test"
            ),
            metadata={},
        )

        raise AssertionError(
            "Database failure was not propagated."
        )

    except RuntimeError as error:

        assert str(error) == (
            "Source Container Refresh "
            "reservation failed."
        )

    print(
        "Source Container Refresh "
        "reservation repository: PASS"
    )


if __name__ == "__main__":
    main()