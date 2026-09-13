"""
Processing Job Repository Test

Purpose:
    Provides isolated validation of ProcessingJobRepository using mocked
    database behavior.

Verifies:
    - Processing Jobs can be created.
    - Processing Jobs can be completed.
    - Processing Jobs can be failed.
    - Required creation inputs are validated.
    - Processing Job identities are validated.
    - Database responses must contain the expected single record.
    - Failure operations require error information.
    - Missing database clients are rejected.

Does NOT:
    - Connect to the live AlphaOmega database.
    - Execute synchronization stages.
    - Decide Processing Job lifecycle state.
    - Modify production Processing Jobs.
"""

from unittest.mock import Mock

from scripts.database.processing_job_repository import (
    ProcessingJobRepository,
)


# ============================================================================
# Test Infrastructure
# ============================================================================


def build_mock_client(
    *,
    insert_data=None,
    update_data=None,
):
    """
    Build a mock Supabase-style client/table chain.
    """

    client = Mock()
    table = Mock()

    insert_builder = Mock()
    update_builder = Mock()
    filtered_update_builder = Mock()

    client.table.return_value = table

    # ------------------------------------------------------------------------
    # INSERT chain
    # ------------------------------------------------------------------------

    table.insert.return_value = (
        insert_builder
    )

    insert_response = Mock()
    insert_response.data = insert_data

    insert_builder.execute.return_value = (
        insert_response
    )

    # ------------------------------------------------------------------------
    # UPDATE chain
    # ------------------------------------------------------------------------

    table.update.return_value = (
        update_builder
    )

    update_builder.eq.return_value = (
        filtered_update_builder
    )

    update_response = Mock()
    update_response.data = update_data

    filtered_update_builder.execute.return_value = (
        update_response
    )

    return (
        client,
        table,
        insert_builder,
        update_builder,
        filtered_update_builder,
    )


# ============================================================================
# Constructor
# ============================================================================


def test_missing_client_rejected():
    """
    Repository requires an authenticated database client.
    """

    try:
        ProcessingJobRepository(
            None
        )

        raise AssertionError(
            "Missing database client was accepted."
        )

    except ValueError:
        pass

    print(
        "PASS: Missing database client rejected."
    )


# ============================================================================
# Create
# ============================================================================


def test_create_processing_job():
    """
    Verify creation of one running Processing Job.
    """

    expected_id = (
        "11111111-1111-1111-1111-111111111111"
    )

    (
        client,
        table,
        insert_builder,
        _update_builder,
        _filtered_update_builder,
    ) = build_mock_client(
        insert_data=[
            {
                "id":
                    expected_id,
            }
        ],
    )

    repository = (
        ProcessingJobRepository(
            client
        )
    )

    metadata = {
        "source":
            "OneDrive",

        "scope":
            "targeted-test",
    }

    result = repository.create(
        process_type="sync",
        pipeline_version="lab7-orchestration",
        metadata=metadata,
    )

    if result != expected_id:
        raise AssertionError(
            "Processing Job ID was not returned correctly."
        )

    client.table.assert_called_once_with(
        "processing_jobs"
    )

    table.insert.assert_called_once_with(
        {
            "process_type":
                "sync",

            "status":
                "running",

            "pipeline_version":
                "lab7-orchestration",

            "metadata":
                metadata,
        }
    )

    insert_builder.execute.assert_called_once()

    print(
        "PASS: Processing Job created correctly."
    )


def test_create_defaults_metadata():
    """
    Verify missing metadata becomes an empty dictionary.
    """

    expected_id = (
        "22222222-2222-2222-2222-222222222222"
    )

    (
        client,
        table,
        _insert_builder,
        _update_builder,
        _filtered_update_builder,
    ) = build_mock_client(
        insert_data=[
            {
                "id":
                    expected_id,
            }
        ],
    )

    repository = (
        ProcessingJobRepository(
            client
        )
    )

    result = repository.create(
        process_type="sync",
        pipeline_version="lab7-orchestration",
    )

    if result != expected_id:
        raise AssertionError(
            "Processing Job ID was not returned correctly."
        )

    table.insert.assert_called_once_with(
        {
            "process_type":
                "sync",

            "status":
                "running",

            "pipeline_version":
                "lab7-orchestration",

            "metadata":
                {},
        }
    )

    print(
        "PASS: Processing Job metadata defaulted correctly."
    )


def test_create_missing_process_type():
    """
    Verify process_type is required.
    """

    client = Mock()

    repository = (
        ProcessingJobRepository(
            client
        )
    )

    for value in (
        None,
        "",
        "   ",
    ):
        try:
            repository.create(
                process_type=value,
                pipeline_version="test",
            )

            raise AssertionError(
                "Invalid process_type was accepted."
            )

        except ValueError:
            pass

    print(
        "PASS: Missing process_type rejected."
    )


def test_create_missing_pipeline_version():
    """
    Verify pipeline_version is required.
    """

    client = Mock()

    repository = (
        ProcessingJobRepository(
            client
        )
    )

    for value in (
        None,
        "",
        "   ",
    ):
        try:
            repository.create(
                process_type="sync",
                pipeline_version=value,
            )

            raise AssertionError(
                "Invalid pipeline_version was accepted."
            )

        except ValueError:
            pass

    print(
        "PASS: Missing pipeline_version rejected."
    )


def test_create_requires_single_record():
    """
    Verify creation requires exactly one database record.
    """

    invalid_results = (
        None,
        [],
        [
            {
                "id": "one",
            },
            {
                "id": "two",
            },
        ],
    )

    for result in invalid_results:

        (
            client,
            _table,
            _insert_builder,
            _update_builder,
            _filtered_update_builder,
        ) = build_mock_client(
            insert_data=result,
        )

        repository = (
            ProcessingJobRepository(
                client
            )
        )

        try:
            repository.create(
                process_type="sync",
                pipeline_version="test",
            )

            raise AssertionError(
                "Invalid create response was accepted."
            )

        except RuntimeError:
            pass

    print(
        "PASS: Invalid Processing Job create responses rejected."
    )


def test_create_requires_returned_id():
    """
    Verify created Processing Job must return an ID.
    """

    (
        client,
        _table,
        _insert_builder,
        _update_builder,
        _filtered_update_builder,
    ) = build_mock_client(
        insert_data=[
            {
                "id":
                    None,
            }
        ],
    )

    repository = (
        ProcessingJobRepository(
            client
        )
    )

    try:
        repository.create(
            process_type="sync",
            pipeline_version="test",
        )

        raise AssertionError(
            "Processing Job without an ID was accepted."
        )

    except RuntimeError:
        pass

    print(
        "PASS: Missing created Processing Job ID rejected."
    )


# ============================================================================
# Complete
# ============================================================================


def test_complete_processing_job():
    """
    Verify one Processing Job can be marked completed.
    """

    processing_job_id = (
        "33333333-3333-3333-3333-333333333333"
    )

    (
        client,
        table,
        _insert_builder,
        update_builder,
        filtered_update_builder,
    ) = build_mock_client(
        update_data=[
            {
                "id":
                    processing_job_id,
            }
        ],
    )

    repository = (
        ProcessingJobRepository(
            client
        )
    )

    repository.complete(
        processing_job_id
    )

    client.table.assert_called_once_with(
        "processing_jobs"
    )

    if table.update.call_count != 1:
        raise AssertionError(
            "Processing Job completion did not issue "
            "exactly one update."
        )

    update_payload = (
        table.update.call_args.args[0]
    )

    if (
        update_payload.get(
            "status"
        )
        != "completed"
    ):
        raise AssertionError(
            "Processing Job completion status incorrect."
        )

    if (
        update_payload.get(
            "completed_at"
        )
        is None
    ):
        raise AssertionError(
            "Processing Job completion timestamp missing."
        )

    if (
        update_payload.get(
            "error_message"
        )
        is not None
    ):
        raise AssertionError(
            "Completed Processing Job did not clear "
            "error_message."
        )

    update_builder.eq.assert_called_once_with(
        "id",
        processing_job_id,
    )

    filtered_update_builder.execute.assert_called_once()

    print(
        "PASS: Processing Job completed correctly."
    )


# ============================================================================
# Fail
# ============================================================================


def test_fail_processing_job():
    """
    Verify one Processing Job can be marked failed.
    """

    processing_job_id = (
        "44444444-4444-4444-4444-444444444444"
    )

    (
        client,
        table,
        _insert_builder,
        update_builder,
        filtered_update_builder,
    ) = build_mock_client(
        update_data=[
            {
                "id":
                    processing_job_id,
            }
        ],
    )

    repository = (
        ProcessingJobRepository(
            client
        )
    )

    error = RuntimeError(
        "Synthetic orchestration failure."
    )

    repository.fail(
        processing_job_id,
        error,
    )

    if table.update.call_count != 1:
        raise AssertionError(
            "Processing Job failure did not issue "
            "exactly one update."
        )

    update_payload = (
        table.update.call_args.args[0]
    )

    if (
        update_payload.get(
            "status"
        )
        != "failed"
    ):
        raise AssertionError(
            "Processing Job failure status incorrect."
        )

    if (
        update_payload.get(
            "completed_at"
        )
        is None
    ):
        raise AssertionError(
            "Processing Job failure timestamp missing."
        )

    if (
        update_payload.get(
            "error_message"
        )
        != "Synthetic orchestration failure."
    ):
        raise AssertionError(
            "Processing Job failure message incorrect."
        )

    update_builder.eq.assert_called_once_with(
        "id",
        processing_job_id,
    )

    filtered_update_builder.execute.assert_called_once()

    print(
        "PASS: Processing Job failed correctly."
    )


# ============================================================================
# Lifecycle Validation
# ============================================================================


def test_missing_processing_job_id():
    """
    Verify complete/fail require Processing Job identity.
    """

    client = Mock()

    repository = (
        ProcessingJobRepository(
            client
        )
    )

    for value in (
        None,
        "",
        "   ",
    ):

        try:
            repository.complete(
                value
            )

            raise AssertionError(
                "Complete accepted invalid Processing Job ID."
            )

        except ValueError:
            pass

        try:
            repository.fail(
                value,
                RuntimeError(
                    "test"
                ),
            )

            raise AssertionError(
                "Fail accepted invalid Processing Job ID."
            )

        except ValueError:
            pass

    print(
        "PASS: Missing Processing Job identity rejected."
    )


def test_fail_requires_error():
    """
    Verify failed Processing Jobs require failure information.
    """

    client = Mock()

    repository = (
        ProcessingJobRepository(
            client
        )
    )

    try:
        repository.fail(
            "55555555-5555-5555-5555-555555555555",
            None,
        )

        raise AssertionError(
            "Processing Job failure without error was accepted."
        )

    except ValueError:
        pass

    print(
        "PASS: Missing Processing Job failure error rejected."
    )


def test_complete_requires_single_record():
    """
    Verify completion requires exactly one updated database record.
    """

    invalid_results = (
        None,
        [],
        [
            {
                "id": "one",
            },
            {
                "id": "two",
            },
        ],
    )

    for result in invalid_results:

        (
            client,
            _table,
            _insert_builder,
            _update_builder,
            _filtered_update_builder,
        ) = build_mock_client(
            update_data=result,
        )

        repository = (
            ProcessingJobRepository(
                client
            )
        )

        try:
            repository.complete(
                "66666666-6666-6666-6666-666666666666"
            )

            raise AssertionError(
                "Invalid completion response was accepted."
            )

        except RuntimeError:
            pass

    print(
        "PASS: Invalid Processing Job completion "
        "responses rejected."
    )


def test_fail_requires_single_record():
    """
    Verify failure requires exactly one updated database record.
    """

    invalid_results = (
        None,
        [],
        [
            {
                "id": "one",
            },
            {
                "id": "two",
            },
        ],
    )

    for result in invalid_results:

        (
            client,
            _table,
            _insert_builder,
            _update_builder,
            _filtered_update_builder,
        ) = build_mock_client(
            update_data=result,
        )

        repository = (
            ProcessingJobRepository(
                client
            )
        )

        try:
            repository.fail(
                "77777777-7777-7777-7777-777777777777",
                RuntimeError(
                    "Synthetic failure."
                ),
            )

            raise AssertionError(
                "Invalid failure response was accepted."
            )

        except RuntimeError:
            pass

    print(
        "PASS: Invalid Processing Job failure "
        "responses rejected."
    )


# ============================================================================
# Main
# ============================================================================


def main():
    """
    Run isolated ProcessingJobRepository tests.
    """

    print()
    print(
        "Running ProcessingJobRepository isolated tests..."
    )

    print()

    test_missing_client_rejected()

    test_create_processing_job()
    test_create_defaults_metadata()
    test_create_missing_process_type()
    test_create_missing_pipeline_version()
    test_create_requires_single_record()
    test_create_requires_returned_id()

    test_complete_processing_job()
    test_fail_processing_job()

    test_missing_processing_job_id()
    test_fail_requires_error()

    test_complete_requires_single_record()
    test_fail_requires_single_record()

    print()

    print(
        "ProcessingJobRepository isolated tests PASSED."
    )

    print()


if __name__ == "__main__":
    main()