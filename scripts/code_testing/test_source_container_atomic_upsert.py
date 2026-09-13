"""
Source Container Atomic Upsert Test

Purpose:
    Validates atomic persistence of Source Container observations through the
    upsert_source_containers database operation.

Verifies:
    - Controlled Source Container records can be submitted atomically.
    - New and existing container identities are handled correctly.
    - Processing Job attribution is persisted with the catalog records.
    - The database operation produces the expected persisted state.

Does NOT:
    - Enumerate a Source of Truth.
    - Perform Source Container reconciliation.
    - Synchronize content.
    - Create Knowledge Objects.
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
from scripts.database.source_repository import (
    SourceRepository,
)


def main():

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega Source Container Atomic Upsert Test"
    )
    print(
        "============================================================"
    )
    print()

    credential_provider = (
        LocalCredentialProvider()
    )

    database_connection = (
        DatabaseConnection(
            credential_provider
        )
    )

    client = (
        database_connection.connect()
    )

    source_repository = (
        SourceRepository(client)
    )

    source_id = (
        source_repository.find_id_by_name(
            "OneDrive"
        )
    )

    if source_id is None:
        raise RuntimeError(
            "Registered OneDrive Source was not found."
        )

    print(
        "PASS: Registered OneDrive Source resolved."
    )
    print(
        f"  Source ID : {source_id}"
    )
    print()

    processing_job_repository = (
        ProcessingJobRepository(client)
    )

    processing_job_id = None

    test_prefix = (
        f"ATOMIC-TEST-{uuid4()}"
    )

    first_object_id = (
        f"{test_prefix}-A"
    )

    rollback_object_id = (
        f"{test_prefix}-ROLLBACK"
    )

    try:

        # -----------------------------------------------------
        # Create legitimate Processing Job fixture
        # -----------------------------------------------------

        processing_job_id = (
            processing_job_repository.create(
                process_type=(
                    "source_container_refresh"
                ),
                pipeline_version=(
                    "lab8-atomic-test"
                ),
                metadata={
                    "purpose":
                        "Source Container atomic upsert test"
                },
            )
        )

        print(
            "PASS: Temporary Processing Job created."
        )
        print(
            f"  Processing Job ID : "
            f"{processing_job_id}"
        )
        print()

        observed_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        # -----------------------------------------------------
        # Test 1: NEW Container
        # -----------------------------------------------------

        response = (
            client.rpc(
                "upsert_source_containers",
                {
                    "p_source_id":
                        source_id,

                    "p_processing_job_id":
                        processing_job_id,

                    "p_observed_at":
                        observed_at,

                    "p_containers": [
                        {
                            "source_object_id":
                                first_object_id,

                            "parent_source_object_id":
                                None,

                            "name":
                                "Atomic Test Container",
                        }
                    ],
                },
            ).execute()
        )

        if response.data != 1:
            raise RuntimeError(
                "Expected RPC to process exactly "
                "1 Container."
            )

        rows = (
            client
            .table(
                "source_containers"
            )
            .select("*")
            .eq(
                "source_id",
                source_id,
            )
            .eq(
                "source_object_id",
                first_object_id,
            )
            .execute()
            .data
            or []
        )

        if len(rows) != 1:
            raise RuntimeError(
                "Expected exactly one persisted "
                "Source Container."
            )

        first_row = rows[0]

        alphaomega_id = (
            first_row["id"]
        )

        if not alphaomega_id:
            raise RuntimeError(
                "Persisted Source Container "
                "has no AlphaOmega UUID."
            )

        print(
            "PASS: NEW Container persisted."
        )
        print(
            f"  AlphaOmega ID : {alphaomega_id}"
        )
        print()

        # -----------------------------------------------------
        # Test 2: Existing identity preserves AlphaOmega UUID
        # -----------------------------------------------------

        response = (
            client.rpc(
                "upsert_source_containers",
                {
                    "p_source_id":
                        source_id,

                    "p_processing_job_id":
                        processing_job_id,

                    "p_observed_at":
                        datetime.now(
                            timezone.utc
                        ).isoformat(),

                    "p_containers": [
                        {
                            "source_object_id":
                                first_object_id,

                            "parent_source_object_id":
                                None,

                            "name":
                                "Atomic Test Container Renamed",
                        }
                    ],
                },
            ).execute()
        )

        if response.data != 1:
            raise RuntimeError(
                "Expected RPC to process exactly "
                "1 existing Container."
            )

        rows = (
            client
            .table(
                "source_containers"
            )
            .select("*")
            .eq(
                "source_id",
                source_id,
            )
            .eq(
                "source_object_id",
                first_object_id,
            )
            .execute()
            .data
            or []
        )

        if len(rows) != 1:
            raise RuntimeError(
                "Expected exactly one existing "
                "Source Container."
            )

        updated_row = rows[0]

        if (
            updated_row["id"]
            != alphaomega_id
        ):
            raise RuntimeError(
                "Existing Source Container "
                "lost its AlphaOmega identity."
            )

        if (
            updated_row["name"]
            != "Atomic Test Container Renamed"
        ):
            raise RuntimeError(
                "Existing Source Container "
                "was not updated."
            )

        print(
            "PASS: Existing Container updated."
        )
        print(
            "PASS: AlphaOmega UUID preserved."
        )
        print()

        # -----------------------------------------------------
        # Test 3: Atomic rollback
        #
        # First record is valid.
        # Second record is deliberately invalid.
        #
        # If PostgreSQL atomicity works correctly,
        # NEITHER record survives.
        # -----------------------------------------------------

        rollback_failed_as_expected = False

        try:

            client.rpc(
                "upsert_source_containers",
                {
                    "p_source_id":
                        source_id,

                    "p_processing_job_id":
                        processing_job_id,

                    "p_observed_at":
                        datetime.now(
                            timezone.utc
                        ).isoformat(),

                    "p_containers": [
                        {
                            "source_object_id":
                                rollback_object_id,

                            "parent_source_object_id":
                                None,

                            "name":
                                "Should Roll Back",
                        },
                        {
                            "source_object_id":
                                f"{test_prefix}-INVALID",

                            "parent_source_object_id":
                                None,

                            "name":
                                "",
                        },
                    ],
                },
            ).execute()

        except Exception:

            rollback_failed_as_expected = True

        if not rollback_failed_as_expected:
            raise RuntimeError(
                "Invalid RPC batch did not fail."
            )

        rollback_rows = (
            client
            .table(
                "source_containers"
            )
            .select("id")
            .eq(
                "source_id",
                source_id,
            )
            .eq(
                "source_object_id",
                rollback_object_id,
            )
            .execute()
            .data
            or []
        )

        if rollback_rows:
            raise RuntimeError(
                "Atomic rollback failed. "
                "The valid record from the failed "
                "batch was persisted."
            )

        print(
            "PASS: Invalid batch failed."
        )
        print(
            "PASS: Earlier INSERT in failed batch "
            "was rolled back."
        )
        print()

        print(
            "SOURCE CONTAINER ATOMIC UPSERT TEST: PASS"
        )
        print()

    finally:

        # -----------------------------------------------------
        # Remove disposable Source Container test records
        # -----------------------------------------------------

        try:

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
                .like(
                    "source_object_id",
                    f"{test_prefix}%"
                )
                .execute()
            )

            print(
                "Temporary Source Container "
                "records removed."
            )

        except Exception as cleanup_error:

            print(
                "WARNING: Source Container cleanup failed:"
            )
            print(
                cleanup_error
            )

        # -----------------------------------------------------
        # Remove disposable Processing Job
        # -----------------------------------------------------

        if processing_job_id is not None:

            try:

                (
                    client
                    .table(
                        "processing_jobs"
                    )
                    .delete()
                    .eq(
                        "id",
                        processing_job_id,
                    )
                    .execute()
                )

                print(
                    "Temporary Processing Job removed."
                )

            except Exception as cleanup_error:

                print(
                    "WARNING: Processing Job cleanup failed:"
                )
                print(
                    cleanup_error
                )

        print()


if __name__ == "__main__":
    main()