"""
Live Microsoft Graph Load Test

Purpose:
    Validates the NEW Load path using controlled live Microsoft Graph source
    objects and the AlphaOmega database.

Verifies:
    - Controlled live source objects are absent from knowledge_objects before
      NEW processing begins.
    - Live source content can be extracted for Load.
    - NEW Knowledge Objects can be persisted through LoadService.
    - Persisted Knowledge Objects contain the expected synchronized data.
    - NEW synchronization history events are recorded.
    - Processing Job state can be completed for successful test processing.

Does NOT:
    - Test the MODIFIED Load path.
    - Test the UNCHANGED synchronization path.
    - Modify Microsoft Graph source content.
    - Perform broad Source of Truth synchronization.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)
from scripts.database.source_repository import (
    SourceRepository,
)
from scripts.database.knowledge_object_repository import (
    KnowledgeObjectRepository,
)

from scripts.extraction.extraction_service import (
    ExtractionService,
)

from scripts.load.load_repository import (
    LoadRepository,
)
from scripts.load.load_service import (
    LoadService,
)

from scripts.sync.sync_association import (
    SynchronizationAssociation,
)
from scripts.sync.sync_state import (
    SyncState,
)


# ============================================================================
# Live Test Targets
# ============================================================================


ONEDRIVE_FILE_NAME = (
    "Bogmire Introduction Draft v1.docx"
)

ONEDRIVE_OBJECT_ID = (
    "70EE5AA1D6A4DA1F!sac3f611bf898418d8a31206c7780357c"
)

ONEDRIVE_SOURCE_PATH = (
    "Mimics Tavern/D&D/Created Adventures/"
    "Bogmire Adventures/Drafts/"
    "Bogmire Introduction Draft v1.docx"
)


ONENOTE_PAGE_NAME = (
    "Blacksmith Lingo"
)

ONENOTE_PAGE_ID = (
    "0-c95a5657f28b44aca521bda1767279d9!"
    "1-70EE5AA1D6A4DA1F!80852"
)

ONENOTE_SOURCE_PATH = (
    "Mimic's Tavern/Lingo/Blacksmith Lingo"
)


# ============================================================================
# Database Infrastructure
# ============================================================================


def build_database_infrastructure():
    """
    Establish authenticated AlphaOmega database access.
    """

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
        SourceRepository(
            client
        )
    )

    knowledge_object_repository = (
        KnowledgeObjectRepository(
            client
        )
    )

    load_repository = (
        LoadRepository(
            client
        )
    )

    load_service = (
        LoadService(
            source_repository=source_repository,
            load_repository=load_repository,
        )
    )

    return (
        client,
        source_repository,
        knowledge_object_repository,
        load_service,
    )


# ============================================================================
# Precondition Validation
# ============================================================================


def verify_target_is_new(
    source_repository,
    knowledge_object_repository,
    source_name,
    source_object_id,
):
    """
    Verify the live target does not already exist in AlphaOmega.

    This test intentionally validates the NEW Load path.
    """

    source_id = (
        source_repository.find_id_by_name(
            source_name
        )
    )

    if source_id is None:
        raise RuntimeError(
            f"Source '{source_name}' is not registered "
            "in AlphaOmega."
        )

    existing_record = (
        knowledge_object_repository
        .find_by_source_identity(
            source_id=source_id,
            source_object_id=source_object_id,
        )
    )

    if existing_record is not None:
        raise RuntimeError(
            f"Target '{source_name}' object "
            f"'{source_object_id}' already exists in "
            "knowledge_objects. This test requires NEW state."
        )

    print(
        f"PASS: {source_name} target is not already "
        "present in knowledge_objects."
    )


# ============================================================================
# Processing Job Test Scaffolding
# ============================================================================


def create_test_processing_job(
    client,
):
    """
    Create the Processing Job required by the Load contract.

    This is test scaffolding. LoadService does not create
    Processing Jobs.
    """

    response = (
        client
        .table(
            "processing_jobs"
        )
        .insert(
            {
                "process_type":
                    "sync",

                "status":
                    "running",

                "pipeline_version":
                    "lab7-targeted-live-load",

                "metadata":
                    {
                        "test_type":
                            "targeted_live_load",

                        "targets":
                            [
                                ONEDRIVE_FILE_NAME,
                                ONENOTE_PAGE_NAME,
                            ],
                    },
            }
        )
        .execute()
    )

    records = response.data

    if (
        records is None
        or len(records) != 1
    ):
        raise RuntimeError(
            "Unable to create targeted Load test "
            "Processing Job."
        )

    processing_job_id = (
        records[0]["id"]
    )

    print(
        "PASS: Test Processing Job created."
    )

    return processing_job_id


def complete_test_processing_job(
    client,
    processing_job_id,
):
    """
    Mark the test Processing Job completed.
    """

    completed_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    response = (
        client
        .table(
            "processing_jobs"
        )
        .update(
            {
                "status":
                    "completed",

                "completed_at":
                    completed_at,

                "error_message":
                    None,
            }
        )
        .eq(
            "id",
            processing_job_id,
        )
        .execute()
    )

    records = response.data

    if (
        records is None
        or len(records) != 1
    ):
        raise RuntimeError(
            "Unable to complete targeted Load test "
            "Processing Job."
        )

    print(
        "PASS: Test Processing Job completed."
    )


def fail_test_processing_job(
    client,
    processing_job_id,
    error,
):
    """
    Mark the test Processing Job failed.

    This function is best-effort failure cleanup. The original test
    exception must remain the primary failure if job finalization
    itself encounters an error.
    """

    completed_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    error_message = str(
        error
    )

    try:
        response = (
            client
            .table(
                "processing_jobs"
            )
            .update(
                {
                    "status":
                        "failed",

                    "completed_at":
                        completed_at,

                    "error_message":
                        error_message,
                }
            )
            .eq(
                "id",
                processing_job_id,
            )
            .execute()
        )

        records = response.data

        if (
            records is None
            or len(records) != 1
        ):
            print(
                "WARNING: Test Processing Job could not "
                "be confirmed as failed."
            )

            return

        print(
            "PASS: Failed test Processing Job closed "
            "with status 'failed'."
        )

    except Exception as cleanup_error:
        print(
            "WARNING: Unable to mark failed test "
            "Processing Job as failed."
        )

        print(
            f"Cleanup error: {cleanup_error}"
        )


# ============================================================================
# Extraction
# ============================================================================


def extract_live_target(
    *,
    correlation_id,
    source_name,
    source_object_id,
    object_type,
    name,
):
    """
    Retrieve and extract one exact Microsoft Graph object.
    """

    extraction_service = (
        ExtractionService()
    )

    extraction_input = (
        SimpleNamespace(
            correlation_id=correlation_id,
            source_name=source_name,
            source_object_id=source_object_id,
            object_type=object_type,
            name=name,
        )
    )

    section = (
        extraction_service.run(
            [
                extraction_input,
            ]
        )
    )

    if not section.extraction_succeeded:
        raise RuntimeError(
            f"Extraction did not succeed for '{name}'."
        )

    if len(section.record_errors) != 0:
        raise RuntimeError(
            f"Extraction produced errors for '{name}': "
            f"{section.record_errors}"
        )

    if len(section.extraction_records) != 1:
        raise RuntimeError(
            f"Extraction did not produce exactly one "
            f"record for '{name}'."
        )

    record = (
        section.extraction_records[0]
    )

    if (
        record.correlation_id
        != correlation_id
    ):
        raise RuntimeError(
            f"Extraction correlation identity was not "
            f"preserved for '{name}'."
        )

    print(
        f"PASS: Live Extraction succeeded for '{name}'."
    )

    print(
        "  Canonical content length: "
        f"{len(record.canonical_content)}"
    )

    print(
        "  SHA-256 length: "
        f"{len(record.content_hash)}"
    )

    return record


# ============================================================================
# Controlled Upstream Records
# ============================================================================


def build_translator_record(
    *,
    correlation_id,
    source_name,
    source_object_id,
    source_path,
    name,
    object_type,
):
    """
    Build the trusted Translator information required by Load.

    Translator itself is not under test here.
    """

    return SimpleNamespace(
        correlation_id=correlation_id,
        source_name=source_name,
        source_object_id=source_object_id,
        source_parent_object_id=None,
        source_path=source_path,
        source_url=None,
        name=name,
        object_type=object_type,
        source_created_at=None,
        source_modified_at=None,
        metadata={
            "live_load_test": True,
        },
    )


def build_discovery_record(
    *,
    correlation_id,
):
    """
    Build the trusted NEW Discovery result required by Load.

    Discovery itself is not under test here.
    """

    return SimpleNamespace(
        correlation_id=correlation_id,
        sync_state=SyncState.NEW,
        knowledge_object_id=None,
        comparison_reason=None,
    )


def build_association(
    *,
    translator_record,
    discovery_record,
    extraction_record,
):
    """
    Build the real orchestration association consumed by Load.
    """

    association = (
        SynchronizationAssociation(
            translator_record.correlation_id
        )
    )

    association.attach_translator(
        translator_record
    )

    association.attach_discovery(
        discovery_record
    )

    association.attach_extraction(
        extraction_record
    )

    return association


# ============================================================================
# Database Verification
# ============================================================================


def verify_knowledge_object(
    *,
    client,
    source_id,
    source_object_id,
    expected_title,
    expected_hash,
):
    """
    Verify the persisted Knowledge Object.
    """

    response = (
        client
        .table(
            "knowledge_objects"
        )
        .select(
            "id,"
            "source_id,"
            "source_object_id,"
            "title,"
            "canonical_content,"
            "content_hash,"
            "metadata"
        )
        .eq(
            "source_id",
            source_id,
        )
        .eq(
            "source_object_id",
            source_object_id,
        )
        .execute()
    )

    records = response.data

    if (
        records is None
        or len(records) != 1
    ):
        raise RuntimeError(
            f"Expected exactly one persisted Knowledge Object "
            f"for '{expected_title}'."
        )

    record = records[0]

    if (
        record["title"]
        != expected_title
    ):
        raise RuntimeError(
            f"Persisted title mismatch for "
            f"'{expected_title}'."
        )

    if (
        record["content_hash"]
        != expected_hash
    ):
        raise RuntimeError(
            f"Persisted content hash mismatch for "
            f"'{expected_title}'."
        )

    if not isinstance(
        record["canonical_content"],
        str,
    ):
        raise RuntimeError(
            f"Persisted canonical content is not text "
            f"for '{expected_title}'."
        )

    if (
        len(
            record["canonical_content"]
        )
        == 0
    ):
        raise RuntimeError(
            f"Persisted canonical content is empty "
            f"for '{expected_title}'."
        )

    print(
        f"PASS: Knowledge Object verified for "
        f"'{expected_title}'."
    )

    return record["id"]


def verify_sync_history(
    *,
    client,
    processing_job_id,
    knowledge_object_id,
    source_id,
):
    """
    Verify the corresponding synchronization history event.
    """

    response = (
        client
        .table(
            "sync_history"
        )
        .select(
            "id,"
            "source_id,"
            "knowledge_object_id,"
            "processing_job_id,"
            "sync_event"
        )
        .eq(
            "processing_job_id",
            processing_job_id,
        )
        .eq(
            "knowledge_object_id",
            knowledge_object_id,
        )
        .execute()
    )

    records = response.data

    if (
        records is None
        or len(records) != 1
    ):
        raise RuntimeError(
            "Expected exactly one Sync History record "
            "for the persisted Knowledge Object."
        )

    record = records[0]

    if (
        record["source_id"]
        != source_id
    ):
        raise RuntimeError(
            "Sync History Source identity mismatch."
        )

    if (
        record["processing_job_id"]
        != processing_job_id
    ):
        raise RuntimeError(
            "Sync History Processing Job identity mismatch."
        )

    print(
        "PASS: Sync History verified."
    )


# ============================================================================
# Main
# ============================================================================


def main():
    """
    Run the targeted live Graph -> Extraction -> Load test.
    """

    print(
        "\n============================================================"
    )

    print(
        "AlphaOmega Targeted Live Load Integration Test"
    )

    print(
        "============================================================\n"
    )

    print(
        "WARNING: This test intentionally writes exactly "
        "two controlled Knowledge Objects to AlphaOmega.\n"
    )

    (
        client,
        source_repository,
        knowledge_object_repository,
        load_service,
    ) = build_database_infrastructure()

    print(
        "PASS: Authenticated AlphaOmega database access established.\n"
    )

    # ------------------------------------------------------------------
    # Resolve canonical Sources
    # ------------------------------------------------------------------

    onedrive_source_id = (
        source_repository.find_id_by_name(
            "OneDrive"
        )
    )

    onenote_source_id = (
        source_repository.find_id_by_name(
            "OneNote"
        )
    )

    if onedrive_source_id is None:
        raise RuntimeError(
            "OneDrive is not registered in AlphaOmega."
        )

    if onenote_source_id is None:
        raise RuntimeError(
            "OneNote is not registered in AlphaOmega."
        )

    # ------------------------------------------------------------------
    # NEW preconditions
    #
    # These occur before Processing Job creation. A failed precondition
    # therefore does not create test scaffolding that needs cleanup.
    # ------------------------------------------------------------------

    verify_target_is_new(
        source_repository=source_repository,
        knowledge_object_repository=(
            knowledge_object_repository
        ),
        source_name="OneDrive",
        source_object_id=ONEDRIVE_OBJECT_ID,
    )

    verify_target_is_new(
        source_repository=source_repository,
        knowledge_object_repository=(
            knowledge_object_repository
        ),
        source_name="OneNote",
        source_object_id=ONENOTE_PAGE_ID,
    )

    # ------------------------------------------------------------------
    # Create Processing Job
    # ------------------------------------------------------------------

    processing_job_id = (
        create_test_processing_job(
            client
        )
    )

    # ------------------------------------------------------------------
    # Everything after Processing Job creation is protected so any
    # failure closes the job as failed.
    # ------------------------------------------------------------------

    try:

        # --------------------------------------------------------------
        # OneDrive
        # --------------------------------------------------------------

        onedrive_correlation_id = str(
            uuid4()
        )

        onedrive_extraction_record = (
            extract_live_target(
                correlation_id=(
                    onedrive_correlation_id
                ),
                source_name="OneDrive",
                source_object_id=(
                    ONEDRIVE_OBJECT_ID
                ),
                object_type="CONTENT",
                name=ONEDRIVE_FILE_NAME,
            )
        )

        onedrive_translator_record = (
            build_translator_record(
                correlation_id=(
                    onedrive_correlation_id
                ),
                source_name="OneDrive",
                source_object_id=(
                    ONEDRIVE_OBJECT_ID
                ),
                source_path=(
                    ONEDRIVE_SOURCE_PATH
                ),
                name=ONEDRIVE_FILE_NAME,
                object_type="CONTENT",
            )
        )

        onedrive_discovery_record = (
            build_discovery_record(
                correlation_id=(
                    onedrive_correlation_id
                ),
            )
        )

        onedrive_association = (
            build_association(
                translator_record=(
                    onedrive_translator_record
                ),
                discovery_record=(
                    onedrive_discovery_record
                ),
                extraction_record=(
                    onedrive_extraction_record
                ),
            )
        )

        # --------------------------------------------------------------
        # OneNote
        # --------------------------------------------------------------

        onenote_correlation_id = str(
            uuid4()
        )

        onenote_extraction_record = (
            extract_live_target(
                correlation_id=(
                    onenote_correlation_id
                ),
                source_name="OneNote",
                source_object_id=(
                    ONENOTE_PAGE_ID
                ),
                object_type="page",
                name=ONENOTE_PAGE_NAME,
            )
        )

        onenote_translator_record = (
            build_translator_record(
                correlation_id=(
                    onenote_correlation_id
                ),
                source_name="OneNote",
                source_object_id=(
                    ONENOTE_PAGE_ID
                ),
                source_path=(
                    ONENOTE_SOURCE_PATH
                ),
                name=ONENOTE_PAGE_NAME,
                object_type="page",
            )
        )

        onenote_discovery_record = (
            build_discovery_record(
                correlation_id=(
                    onenote_correlation_id
                ),
            )
        )

        onenote_association = (
            build_association(
                translator_record=(
                    onenote_translator_record
                ),
                discovery_record=(
                    onenote_discovery_record
                ),
                extraction_record=(
                    onenote_extraction_record
                ),
            )
        )

        # --------------------------------------------------------------
        # Real Load
        # --------------------------------------------------------------

        print(
            "\nExecuting real Load..."
        )

        load_section = (
            load_service.run(
                associations=[
                    onedrive_association,
                    onenote_association,
                ],
                processing_job_id=(
                    processing_job_id
                ),
            )
        )

        if not load_section.load_succeeded:
            raise RuntimeError(
                "Load stage did not complete successfully."
            )

        if len(
            load_section.record_errors
        ) != 0:

            print(
                "\nLoad produced record-level errors:"
            )

            for error in (
                load_section.record_errors
            ):
                print(
                    f"\n{dict(error)}"
                )

            raise RuntimeError(
                "Load produced record-level errors."
            )

        if not load_section.is_locked:
            raise RuntimeError(
                "LoadSection was not locked."
            )

        print(
            "PASS: LoadService completed with zero "
            "record-level errors."
        )

        # --------------------------------------------------------------
        # Verify Knowledge Objects
        # --------------------------------------------------------------

        onedrive_knowledge_object_id = (
            verify_knowledge_object(
                client=client,
                source_id=(
                    onedrive_source_id
                ),
                source_object_id=(
                    ONEDRIVE_OBJECT_ID
                ),
                expected_title=(
                    ONEDRIVE_FILE_NAME
                ),
                expected_hash=(
                    onedrive_extraction_record
                    .content_hash
                ),
            )
        )

        onenote_knowledge_object_id = (
            verify_knowledge_object(
                client=client,
                source_id=(
                    onenote_source_id
                ),
                source_object_id=(
                    ONENOTE_PAGE_ID
                ),
                expected_title=(
                    ONENOTE_PAGE_NAME
                ),
                expected_hash=(
                    onenote_extraction_record
                    .content_hash
                ),
            )
        )

        # --------------------------------------------------------------
        # Verify Sync History
        # --------------------------------------------------------------

        verify_sync_history(
            client=client,
            processing_job_id=(
                processing_job_id
            ),
            knowledge_object_id=(
                onedrive_knowledge_object_id
            ),
            source_id=(
                onedrive_source_id
            ),
        )

        verify_sync_history(
            client=client,
            processing_job_id=(
                processing_job_id
            ),
            knowledge_object_id=(
                onenote_knowledge_object_id
            ),
            source_id=(
                onenote_source_id
            ),
        )

        # --------------------------------------------------------------
        # Complete Processing Job
        # --------------------------------------------------------------

        complete_test_processing_job(
            client=client,
            processing_job_id=(
                processing_job_id
            ),
        )

    except Exception as error:

        fail_test_processing_job(
            client=client,
            processing_job_id=(
                processing_job_id
            ),
            error=error,
        )

        raise

    # ------------------------------------------------------------------
    # Final Result
    # ------------------------------------------------------------------

    print(
        "\n============================================================"
    )

    print(
        "FINAL RESULT"
    )

    print(
        "============================================================"
    )

    print(
        f"OneDrive: {ONEDRIVE_FILE_NAME} : PASS"
    )

    print(
        f"OneNote : {ONENOTE_PAGE_NAME} : PASS"
    )

    print(
        "\nTargeted live Graph -> Extraction -> Load "
        "integration test PASSED.\n"
    )


if __name__ == "__main__":
    main()