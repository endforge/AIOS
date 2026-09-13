"""
Source Container Refresh Status Repository Test

Purpose:
    Performs isolated deterministic tests of active Source Container
    Refresh lookup behavior.

Verifies:
    - Running Source Container Refresh jobs are returned for one Source.
    - Completed Source Container Refresh jobs are excluded.
    - Failed Source Container Refresh jobs are excluded.
    - Running jobs for another process type are excluded.
    - Running Refresh jobs for another Source are excluded.
    - Active Refresh presence can be returned as a boolean.
    - A Source with no active Refresh returns empty state.
    - Required Source identity validation is enforced.

Does NOT:
    - Access the live AlphaOmega database.
    - Reserve Source Container Refresh.
    - Create or update Processing Jobs.
    - Enumerate or persist Source Containers.
    - Execute synchronization.
"""


from scripts.database.source_container_refresh_status_repository import (
    SourceContainerRefreshStatusRepository,
)


SOURCE_A = "source-a"
SOURCE_B = "source-b"

RUNNING_REFRESH = "job-running-refresh"
COMPLETED_REFRESH = "job-completed-refresh"
FAILED_REFRESH = "job-failed-refresh"
RUNNING_SYNC = "job-running-sync"
OTHER_SOURCE_REFRESH = "job-other-source-refresh"


class FakeResponse:
    """
    Minimal database response.
    """

    def __init__(
        self,
        data,
    ):
        self.data = data


class FakeQuery:
    """
    Minimal Supabase-style query behavior.
    """

    def __init__(
        self,
        rows,
    ):
        self._rows = list(
            rows
        )

        self._filters = []

    def select(
        self,
        *_args,
    ):
        return self

    def eq(
        self,
        field_name,
        value,
    ):
        self._filters.append(
            (
                field_name,
                value,
            )
        )

        return self

    def execute(
        self,
    ):
        rows = list(
            self._rows
        )

        for (
            field_name,
            value,
        ) in self._filters:

            rows = [
                row
                for row in rows
                if row.get(
                    field_name
                ) == value
            ]

        return FakeResponse(
            rows
        )


class FakeDatabaseClient:
    """
    Provide deterministic Processing Job state.
    """

    def __init__(
        self,
    ):
        self.tables = {
            "processing_jobs": [
                {
                    "id":
                        RUNNING_REFRESH,

                    "source_id":
                        SOURCE_A,

                    "process_type":
                        "source_container_refresh",

                    "status":
                        "running",
                },
                {
                    "id":
                        COMPLETED_REFRESH,

                    "source_id":
                        SOURCE_A,

                    "process_type":
                        "source_container_refresh",

                    "status":
                        "completed",
                },
                {
                    "id":
                        FAILED_REFRESH,

                    "source_id":
                        SOURCE_A,

                    "process_type":
                        "source_container_refresh",

                    "status":
                        "failed",
                },
                {
                    "id":
                        RUNNING_SYNC,

                    "source_id":
                        SOURCE_A,

                    "process_type":
                        "synchronization",

                    "status":
                        "running",
                },
                {
                    "id":
                        OTHER_SOURCE_REFRESH,

                    "source_id":
                        SOURCE_B,

                    "process_type":
                        "source_container_refresh",

                    "status":
                        "running",
                },
            ],
        }

    def table(
        self,
        table_name,
    ):
        if table_name not in self.tables:
            raise RuntimeError(
                f"Unexpected table requested: {table_name}"
            )

        return FakeQuery(
            self.tables[
                table_name
            ]
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


def test_active_refresh_lookup(
    repository,
):
    """
    Verify only the matching running Refresh is returned.
    """

    result = (
        repository.find_active_by_source(
            SOURCE_A
        )
    )

    require_equal(
        actual=len(
            result
        ),
        expected=1,
        test_name=(
            "Only matching running Source Refresh is active"
        ),
    )

    require_equal(
        actual=result[
            0
        ][
            "id"
        ],
        expected=RUNNING_REFRESH,
        test_name=(
            "Running Refresh Processing Job is returned"
        ),
    )


def test_boolean_active_refresh(
    repository,
):
    """
    Verify boolean active Refresh lookup.
    """

    require_equal(
        actual=repository.has_active_refresh(
            SOURCE_A
        ),
        expected=True,
        test_name=(
            "Active Refresh boolean is True"
        ),
    )

    require_equal(
        actual=repository.has_active_refresh(
            "source-empty"
        ),
        expected=False,
        test_name=(
            "Inactive Refresh boolean is False"
        ),
    )


def test_source_isolation(
    repository,
):
    """
    Verify another Source's Refresh does not conflict.
    """

    result = (
        repository.find_active_by_source(
            SOURCE_B
        )
    )

    require_equal(
        actual=len(
            result
        ),
        expected=1,
        test_name=(
            "Refresh lookup is isolated by Source"
        ),
    )

    require_equal(
        actual=result[
            0
        ][
            "id"
        ],
        expected=OTHER_SOURCE_REFRESH,
        test_name=(
            "Correct Source Refresh is returned"
        ),
    )


def test_empty_source(
    repository,
):
    """
    Verify no active Refresh returns empty state.
    """

    result = (
        repository.find_active_by_source(
            "source-empty"
        )
    )

    require_equal(
        actual=result,
        expected=(),
        test_name=(
            "Source with no running Refresh returns empty tuple"
        ),
    )


def test_missing_source_rejected(
    repository,
):
    """
    Verify Source identity is required.
    """

    try:

        repository.find_active_by_source(
            None
        )

    except ValueError:

        print(
            "PASS: Missing source_id is rejected"
        )

        return

    raise RuntimeError(
        "Missing source_id did not raise ValueError."
    )


def main():

    print()
    print(
        "AlphaOmega Source Container Refresh Status Repository Test"
    )
    print(
        "=========================================================="
    )
    print()

    repository = (
        SourceContainerRefreshStatusRepository(
            FakeDatabaseClient()
        )
    )

    test_active_refresh_lookup(
        repository
    )

    test_boolean_active_refresh(
        repository
    )

    test_source_isolation(
        repository
    )

    test_empty_source(
        repository
    )

    test_missing_source_rejected(
        repository
    )

    print()
    print(
        "SOURCE CONTAINER REFRESH STATUS REPOSITORY TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()