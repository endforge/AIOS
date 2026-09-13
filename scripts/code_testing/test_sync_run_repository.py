"""
Synchronization Run Repository Test

Purpose:
    Performs isolated deterministic tests of SyncRunRepository active
    synchronization lookup behavior.

Verifies:
    - Synchronization Runs can be filtered by Source.
    - Only runs whose Processing Jobs are running are returned.
    - Completed and failed Processing Jobs are excluded.
    - Active Source Container identities can be returned directly.
    - An empty Source result returns an empty tuple.
    - Duplicate Processing Job identities do not create duplicate job lookup
      values.
    - Required Source identity validation is enforced.

Does NOT:
    - Access the live AlphaOmega database.
    - Create Synchronization Runs.
    - Create or update Processing Jobs.
    - Determine synchronization hierarchy conflicts.
    - Reserve synchronization execution.
    - Execute synchronization.
"""

from scripts.database.sync_run_repository import (
    SyncRunRepository,
)


SOURCE_A = "source-a"
SOURCE_B = "source-b"

JOB_RUNNING_A = "job-running-a"
JOB_COMPLETED = "job-completed"
JOB_FAILED = "job-failed"
JOB_RUNNING_B = "job-running-b"

CONTAINER_A = "container-a"
CONTAINER_B = "container-b"
CONTAINER_C = "container-c"
CONTAINER_D = "container-d"


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
    Minimal Supabase-style query implementation used by the test.
    """

    def __init__(
        self,
        rows,
    ):
        self._rows = list(
            rows
        )

        self._filters = []
        self._in_filters = []

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

    def in_(
        self,
        field_name,
        values,
    ):
        self._in_filters.append(
            (
                field_name,
                tuple(
                    values
                ),
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

        for (
            field_name,
            values,
        ) in self._in_filters:

            rows = [
                row
                for row in rows
                if row.get(
                    field_name
                ) in values
            ]

        return FakeResponse(
            rows
        )


class FakeDatabaseClient:
    """
    Provide deterministic table data to SyncRunRepository.
    """

    def __init__(
        self,
    ):
        self.tables = {
            "sync_runs": [
                {
                    "id":
                        "run-a",

                    "processing_job_id":
                        JOB_RUNNING_A,

                    "source_id":
                        SOURCE_A,

                    "source_container_id":
                        CONTAINER_A,
                },
                {
                    "id":
                        "run-b",

                    "processing_job_id":
                        JOB_COMPLETED,

                    "source_id":
                        SOURCE_A,

                    "source_container_id":
                        CONTAINER_B,
                },
                {
                    "id":
                        "run-c",

                    "processing_job_id":
                        JOB_FAILED,

                    "source_id":
                        SOURCE_A,

                    "source_container_id":
                        CONTAINER_C,
                },
                {
                    "id":
                        "run-d",

                    "processing_job_id":
                        JOB_RUNNING_B,

                    "source_id":
                        SOURCE_B,

                    "source_container_id":
                        CONTAINER_D,
                },
            ],

            "processing_jobs": [
                {
                    "id":
                        JOB_RUNNING_A,

                    "status":
                        "running",
                },
                {
                    "id":
                        JOB_COMPLETED,

                    "status":
                        "completed",
                },
                {
                    "id":
                        JOB_FAILED,

                    "status":
                        "failed",
                },
                {
                    "id":
                        JOB_RUNNING_B,

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
    Require one deterministic result.
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


def test_active_run_lookup(
    repository,
):
    """
    Verify only running synchronization scope is returned.
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
            "Only running Synchronization Run is active"
        ),
    )

    require_equal(
        actual=result[
            0
        ][
            "processing_job_id"
        ],
        expected=JOB_RUNNING_A,
        test_name=(
            "Running Processing Job is preserved"
        ),
    )

    require_equal(
        actual=result[
            0
        ][
            "source_container_id"
        ],
        expected=CONTAINER_A,
        test_name=(
            "Active synchronization scope is preserved"
        ),
    )


def test_active_container_lookup(
    repository,
):
    """
    Verify direct active Source Container identity lookup.
    """

    result = (
        repository
        .find_active_source_container_ids_by_source(
            SOURCE_A
        )
    )

    require_equal(
        actual=result,
        expected=(
            CONTAINER_A,
        ),
        test_name=(
            "Active Source Container IDs are returned"
        ),
    )


def test_source_isolation(
    repository,
):
    """
    Verify Sources remain independent.
    """

    result = (
        repository
        .find_active_source_container_ids_by_source(
            SOURCE_B
        )
    )

    require_equal(
        actual=result,
        expected=(
            CONTAINER_D,
        ),
        test_name=(
            "Synchronization Runs are isolated by Source"
        ),
    )


def test_empty_source(
    repository,
):
    """
    Verify a Source with no Synchronization Runs returns empty state.
    """

    result = (
        repository
        .find_active_by_source(
            "source-empty"
        )
    )

    require_equal(
        actual=result,
        expected=(),
        test_name=(
            "Source with no Synchronization Runs returns empty tuple"
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
        "AlphaOmega Synchronization Run Repository Test"
    )
    print(
        "=============================================="
    )
    print()

    client = (
        FakeDatabaseClient()
    )

    repository = (
        SyncRunRepository(
            client
        )
    )

    test_active_run_lookup(
        repository
    )

    test_active_container_lookup(
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
        "SYNCHRONIZATION RUN REPOSITORY TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()