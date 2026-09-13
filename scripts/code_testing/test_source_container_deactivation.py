"""
Source Container Deactivation Test

Purpose:
    Validates controlled Source Container deactivation behavior in the
    AlphaOmega database.

Verifies:
    - Controlled Source Containers can be upserted for test preparation.
    - Containers identified as absent can be deactivated.
    - Deactivation preserves the expected persisted catalog state.
    - The deactivation database operation affects the intended records.

Does NOT:
    - Infer absence from an incomplete Source observation.
    - Enumerate a Source of Truth.
    - Synchronize content.
    - Delete Source Container history.
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
        "AlphaOmega Source Container Deactivation Test"
    )
    print(
        "============================================================"
    )
    print()

    credential_provider = LocalCredentialProvider()

    database_connection = DatabaseConnection(
        credential_provider
    )

    client = database_connection.connect()

    source_repository = SourceRepository(client)

    source_id = source_repository.find_id_by_name(
        "OneDrive"
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

    test_prefix = f"DEACTIVATE-TEST-{uuid4()}"

    target_object_id = (
        f"{test_prefix}-TARGET"
    )

    control_object_id = (
        f"{test_prefix}-CONTROL"
    )

    rollback_object_id = (
        f"{test_prefix}-ROLLBACK"
    )

    try:

        # -----------------------------------------------------
        # Create legitimate Processing Job
        # -----------------------------------------------------

        processing_job_id = (
            processing_job_repository.create(
                process_type=(
                    "source_container_refresh"
                ),
                pipeline_version=(
                    "lab8-deactivation-test"
                ),
                metadata={
                    "purpose":
                        "Source Container deactivation test"
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

        # -----------------------------------------------------
        # Create three disposable active Containers using the
        # already-tested atomic upsert RPC.
        # -----------------------------------------------------

        observed_at = datetime.now(
            timezone.utc
        ).isoformat()

        response = client.rpc(
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
                            target_object_id,
                        "parent_source_object_id":
                            None,
                        "name":
                            "Deactivation Target",
                    },
                    {
                        "source_object_id":
                            control_object_id,
                        "parent_source_object_id":
                            None,
                        "name":
                            "Active Control",
                    },
                    {
                        "source_object_id":
                            rollback_object_id,
                        "parent_source_object_id":
                            None,
                        "name":
                            "Rollback Target",
                    },
                ],
            },
        ).execute()

        if response.data != 3:
            raise RuntimeError(
                "Expected three temporary "
                "Source Containers."
            )

        print(
            "PASS: Three active test Containers created."
        )
        print()

        # -----------------------------------------------------
        # Capture persistent UUIDs before deactivation.
        # -----------------------------------------------------

        rows = (
            client
            .table("source_containers")
            .select(
                "id,source_object_id,is_active"
            )
            .eq(
                "source_id",
                source_id,
            )
            .like(
                "source_object_id",
                f"{test_prefix}%"
            )
            .execute()
            .data
            or []
        )

        rows_by_identity = {
            row["source_object_id"]: row
            for row in rows
        }

        if len(rows_by_identity) != 3:
            raise RuntimeError(
                "Expected exactly three persisted "
                "test Containers."
            )

        target_alphaomega_id = (
            rows_by_identity[
                target_object_id
            ]["id"]
        )

        control_alphaomega_id = (
            rows_by_identity[
                control_object_id
            ]["id"]
        )

        rollback_alphaomega_id = (
            rows_by_identity[
                rollback_object_id
            ]["id"]
        )

        # -----------------------------------------------------
        # Test 1: Deactivate exactly one Container.
        # -----------------------------------------------------

        response = client.rpc(
            "deactivate_source_containers",
            {
                "p_source_id":
                    source_id,

                "p_processing_job_id":
                    processing_job_id,

                "p_source_object_ids": [
                    target_object_id
                ],
            },
        ).execute()

        if response.data != 1:
            raise RuntimeError(
                "Expected exactly one Container "
                "to be deactivated."
            )

        rows = (
            client
            .table("source_containers")
            .select(
                "id,source_object_id,is_active"
            )
            .eq(
                "source_id",
                source_id,
            )
            .like(
                "source_object_id",
                f"{test_prefix}%"
            )
            .execute()
            .data
            or []
        )

        rows_by_identity = {
            row["source_object_id"]: row
            for row in rows
        }

        target = rows_by_identity[
            target_object_id
        ]

        control = rows_by_identity[
            control_object_id
        ]

        rollback_target = rows_by_identity[
            rollback_object_id
        ]

        if target["is_active"] is not False:
            raise RuntimeError(
                "Target Container remained active."
            )

        if target["id"] != target_alphaomega_id:
            raise RuntimeError(
                "Deactivation changed the target "
                "AlphaOmega UUID."
            )

        if control["is_active"] is not True:
            raise RuntimeError(
                "Control Container was incorrectly "
                "deactivated."
            )

        if control["id"] != control_alphaomega_id:
            raise RuntimeError(
                "Control Container AlphaOmega UUID changed."
            )

        print(
            "PASS: Target Container deactivated."
        )
        print(
            "PASS: Target AlphaOmega UUID preserved."
        )
        print(
            "PASS: Unspecified Container remained active."
        )
        print()

        # -----------------------------------------------------
        # Test 2: Prove atomic rollback.
        #
        # First identity is valid and would deactivate.
        # Second identity is deliberately invalid.
        #
        # The function must fail and the first UPDATE must
        # roll back.
        # -----------------------------------------------------

        failed_as_expected = False

        try:

            client.rpc(
                "deactivate_source_containers",
                {
                    "p_source_id":
                        source_id,

                    "p_processing_job_id":
                        processing_job_id,

                    "p_source_object_ids": [
                        rollback_object_id,
                        "",
                    ],
                },
            ).execute()

        except Exception:

            failed_as_expected = True

        if not failed_as_expected:
            raise RuntimeError(
                "Invalid deactivation batch did not fail."
            )

        rows = (
            client
            .table("source_containers")
            .select(
                "id,source_object_id,is_active"
            )
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

        if len(rows) != 1:
            raise RuntimeError(
                "Rollback test Container was not found."
            )

        rollback_target = rows[0]

        if rollback_target["is_active"] is not True:
            raise RuntimeError(
                "Atomic rollback failed. "
                "The first deactivation survived "
                "the failed batch."
            )

        if (
            rollback_target["id"]
            != rollback_alphaomega_id
        ):
            raise RuntimeError(
                "Rollback test Container UUID changed."
            )

        print(
            "PASS: Invalid deactivation batch failed."
        )
        print(
            "PASS: Earlier UPDATE in failed batch "
            "was rolled back."
        )
        print()

        print(
            "SOURCE CONTAINER DEACTIVATION TEST: PASS"
        )
        print()

    finally:

        # -----------------------------------------------------
        # Remove disposable Source Containers.
        # -----------------------------------------------------

        try:

            (
                client
                .table("source_containers")
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
        # Remove disposable Processing Job.
        # -----------------------------------------------------

        if processing_job_id is not None:

            try:

                (
                    client
                    .table("processing_jobs")
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