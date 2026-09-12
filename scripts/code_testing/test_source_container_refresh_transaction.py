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
    print("=" * 60)
    print("Source Container Refresh Transaction Test")
    print("=" * 60)
    print()

    # ---------------------------------------------------------
    # Connect
    # ---------------------------------------------------------

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

    print("PASS: OneDrive Source resolved.")
    print(f"  Source ID: {source_id}")
    print()

    job_repository = ProcessingJobRepository(client)

    processing_job_id = None

    prefix = f"REFRESH-TEST-{uuid4()}"

    existing_id = f"{prefix}-EXISTING"
    reappearing_id = f"{prefix}-REAPPEARING"
    absent_id = f"{prefix}-ABSENT"
    new_id = f"{prefix}-NEW"
    rollback_new_id = f"{prefix}-ROLLBACK"

    try:

        # -----------------------------------------------------
        # Processing Job
        # -----------------------------------------------------

        processing_job_id = job_repository.create(
            process_type="source_container_refresh",
            pipeline_version="lab8-refresh-test",
            metadata={
                "purpose":
                    "Source Container refresh transaction test"
            },
        )

        print("PASS: Processing Job created.")
        print(f"  Job ID: {processing_job_id}")
        print()

        # -----------------------------------------------------
        # Seed EXISTING, REAPPEARING and ABSENT.
        # -----------------------------------------------------

        seed = client.rpc(
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
                            existing_id,
                        "parent_source_object_id":
                            None,
                        "name":
                            "Existing Before",
                    },
                    {
                        "source_object_id":
                            reappearing_id,
                        "parent_source_object_id":
                            None,
                        "name":
                            "Reappearing Before",
                    },
                    {
                        "source_object_id":
                            absent_id,
                        "parent_source_object_id":
                            None,
                        "name":
                            "Absent Before",
                    },
                ],
            },
        ).execute()

        if seed.data != 3:
            raise RuntimeError(
                "Fixture creation failed."
            )

        # Make REAPPEARING inactive.

        result = client.rpc(
            "deactivate_source_containers",
            {
                "p_source_id":
                    source_id,
                "p_processing_job_id":
                    processing_job_id,
                "p_source_object_ids": [
                    reappearing_id
                ],
            },
        ).execute()

        if result.data != 1:
            raise RuntimeError(
                "Could not prepare REAPPEARING fixture."
            )

        # Capture original UUIDs.

        rows = (
            client
            .table("source_containers")
            .select(
                "id,source_object_id,is_active"
            )
            .eq("source_id", source_id)
            .like(
                "source_object_id",
                f"{prefix}%"
            )
            .execute()
            .data
            or []
        )

        by_identity = {
            row["source_object_id"]: row
            for row in rows
        }

        if len(by_identity) != 3:
            raise RuntimeError(
                "Expected three fixture records."
            )

        existing_uuid = by_identity[
            existing_id
        ]["id"]

        reappearing_uuid = by_identity[
            reappearing_id
        ]["id"]

        absent_uuid = by_identity[
            absent_id
        ]["id"]

        print("PASS: Test fixtures prepared.")
        print()

        # -----------------------------------------------------
        # VALID COMPLETE REFRESH
        # -----------------------------------------------------

        result = client.rpc(
            "apply_source_container_refresh",
            {
                "p_source_id":
                    source_id,
                "p_processing_job_id":
                    processing_job_id,
                "p_observation_complete":
                    True,
                "p_upsert_containers": [
                    {
                        "source_object_id":
                            existing_id,
                        "parent_source_object_id":
                            None,
                        "name":
                            "Existing After",
                    },
                    {
                        "source_object_id":
                            reappearing_id,
                        "parent_source_object_id":
                            None,
                        "name":
                            "Reappearing After",
                    },
                    {
                        "source_object_id":
                            new_id,
                        "parent_source_object_id":
                            None,
                        "name":
                            "New",
                    },
                ],
                "p_absent_source_object_ids": [
                    absent_id
                ],
            },
        ).execute()

        if result.data.get("upserted") != 3:
            raise RuntimeError(
                "Expected three upserts."
            )

        if result.data.get("deactivated") != 1:
            raise RuntimeError(
                "Expected one deactivation."
            )

        rows = (
            client
            .table("source_containers")
            .select(
                "id,source_object_id,name,is_active"
            )
            .eq("source_id", source_id)
            .like(
                "source_object_id",
                f"{prefix}%"
            )
            .execute()
            .data
            or []
        )

        by_identity = {
            row["source_object_id"]: row
            for row in rows
        }

        if len(by_identity) != 4:
            raise RuntimeError(
                "Expected four records after refresh."
            )

        # EXISTING

        if by_identity[existing_id]["id"] != existing_uuid:
            raise RuntimeError(
                "EXISTING UUID changed."
            )

        if (
            by_identity[existing_id]["name"]
            != "Existing After"
        ):
            raise RuntimeError(
                "EXISTING was not updated."
            )

        # REAPPEARING

        if (
            by_identity[reappearing_id]["id"]
            != reappearing_uuid
        ):
            raise RuntimeError(
                "REAPPEARING UUID changed."
            )

        if (
            by_identity[
                reappearing_id
            ]["is_active"]
            is not True
        ):
            raise RuntimeError(
                "REAPPEARING was not reactivated."
            )

        # ABSENT

        if by_identity[absent_id]["id"] != absent_uuid:
            raise RuntimeError(
                "ABSENT UUID changed."
            )

        if (
            by_identity[absent_id]["is_active"]
            is not False
        ):
            raise RuntimeError(
                "ABSENT was not deactivated."
            )

        # NEW

        if not by_identity[new_id]["id"]:
            raise RuntimeError(
                "NEW has no AlphaOmega UUID."
            )

        print("PASS: NEW inserted.")
        print("PASS: EXISTING updated; UUID preserved.")
        print("PASS: REAPPEARING reactivated; UUID preserved.")
        print("PASS: ABSENT deactivated; UUID preserved.")
        print()

        # -----------------------------------------------------
        # INCOMPLETE OBSERVATION MUST FAIL
        # -----------------------------------------------------

        incomplete_id = f"{prefix}-INCOMPLETE"

        try:

            client.rpc(
                "apply_source_container_refresh",
                {
                    "p_source_id":
                        source_id,
                    "p_processing_job_id":
                        processing_job_id,
                    "p_observation_complete":
                        False,
                    "p_upsert_containers": [
                        {
                            "source_object_id":
                                incomplete_id,
                            "parent_source_object_id":
                                None,
                            "name":
                                "Must Not Exist",
                        }
                    ],
                    "p_absent_source_object_ids":
                        [],
                },
            ).execute()

            raise RuntimeError(
                "Incomplete observation was accepted."
            )

        except RuntimeError:
            raise

        except Exception:
            pass

        rows = (
            client
            .table("source_containers")
            .select("id")
            .eq("source_id", source_id)
            .eq(
                "source_object_id",
                incomplete_id
            )
            .execute()
            .data
            or []
        )

        if rows:
            raise RuntimeError(
                "Incomplete observation changed the catalog."
            )

        print("PASS: Incomplete observation rejected.")
        print()

        # -----------------------------------------------------
        # CROSS-PHASE TRANSACTION ROLLBACK
        #
        # Phase 1 inserts ROLLBACK-NEW.
        #
        # Phase 2 first deactivates EXISTING, then receives an
        # invalid blank identity and fails.
        #
        # The NEW insert and deactivation must BOTH disappear.
        # -----------------------------------------------------

        failed = False

        try:

            client.rpc(
                "apply_source_container_refresh",
                {
                    "p_source_id":
                        source_id,
                    "p_processing_job_id":
                        processing_job_id,
                    "p_observation_complete":
                        True,
                    "p_upsert_containers": [
                        {
                            "source_object_id":
                                rollback_new_id,
                            "parent_source_object_id":
                                None,
                            "name":
                                "Must Roll Back",
                        }
                    ],
                    "p_absent_source_object_ids": [
                        existing_id,
                        "",
                    ],
                },
            ).execute()

        except Exception:
            failed = True

        if not failed:
            raise RuntimeError(
                "Invalid combined refresh did not fail."
            )

        # The NEW insert must have rolled back.

        rows = (
            client
            .table("source_containers")
            .select("id")
            .eq("source_id", source_id)
            .eq(
                "source_object_id",
                rollback_new_id
            )
            .execute()
            .data
            or []
        )

        if rows:
            raise RuntimeError(
                "NEW insert survived failed transaction."
            )

        # EXISTING must still be active.

        rows = (
            client
            .table("source_containers")
            .select("id,is_active")
            .eq("source_id", source_id)
            .eq(
                "source_object_id",
                existing_id
            )
            .execute()
            .data
            or []
        )

        if len(rows) != 1:
            raise RuntimeError(
                "EXISTING record was not found."
            )

        if rows[0]["is_active"] is not True:
            raise RuntimeError(
                "Deactivation survived failed transaction."
            )

        if rows[0]["id"] != existing_uuid:
            raise RuntimeError(
                "EXISTING UUID changed."
            )

        print(
            "PASS: Invalid combined refresh failed."
        )
        print(
            "PASS: Earlier NEW insert rolled back."
        )
        print(
            "PASS: Earlier deactivation rolled back."
        )
        print()

        print(
            "SOURCE CONTAINER REFRESH TRANSACTION TEST: PASS"
        )
        print()

    finally:

        # -----------------------------------------------------
        # Cleanup
        # -----------------------------------------------------

        try:

            (
                client
                .table("source_containers")
                .delete()
                .eq("source_id", source_id)
                .like(
                    "source_object_id",
                    f"{prefix}%"
                )
                .execute()
            )

            print(
                "Temporary Source Container records removed."
            )

        except Exception as error:

            print(
                "WARNING: Source Container cleanup failed:"
            )
            print(error)

        if processing_job_id is not None:

            try:

                (
                    client
                    .table("processing_jobs")
                    .delete()
                    .eq(
                        "id",
                        processing_job_id
                    )
                    .execute()
                )

                print(
                    "Temporary Processing Job removed."
                )

            except Exception as error:

                print(
                    "WARNING: Processing Job cleanup failed:"
                )
                print(error)

        print()


if __name__ == "__main__":
    main()