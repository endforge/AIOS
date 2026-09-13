"""
Live OneDrive Synchronization Orchestrator MODIFIED Test

Purpose:
    Validates a targeted live end-to-end MODIFIED synchronization run
    conducted by SynchronizationOrchestrator for one known OneDrive object.

Verifies:
    - The controlled OneDrive target begins with an existing Knowledge Object.
    - SynchronizationOrchestrator executes the production synchronization
      stages for exactly one targeted OneDrive object.
    - Discovery classifies the controlled object as MODIFIED.
    - Eligible MODIFIED content proceeds through Extraction and Load.
    - The existing Knowledge Object is updated rather than assigned a new
      identity.
    - Synchronization history records the expected persistence event.
    - The Processing Job completes successfully with the expected sync
      process type and pipeline version.

Does NOT:
    - Synchronize the complete OneDrive Source of Truth.
    - Test the NEW synchronization path.
    - Test the UNCHANGED synchronization path.
    - Modify the OneDrive source object.
"""

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

from scripts.database.processing_job_repository import (
    ProcessingJobRepository,
)

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)

from scripts.connectors.connector_section import (
    ConnectorSection,
)

from scripts.translator.graph_translator import (
    GraphTranslator,
)

from scripts.discovery.discovery_service import (
    DiscoveryService,
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

from scripts.orchestration.sync_orchestrator import (
    SynchronizationOrchestrator,
)

from scripts.sync.sync_state import (
    SyncState,
)


# ============================================================================
# Target
# ============================================================================


ONEDRIVE_FILE_NAME = (
    "Bogmire Introduction Draft v1.docx"
)

ONEDRIVE_OBJECT_ID = (
    "70EE5AA1D6A4DA1F!sac3f611bf898418d8a31206c7780357c"
)


# ============================================================================
# Targeted Connector
# ============================================================================


class TargetedOneDriveConnector(
    GraphConnector
):
    """
    Live Microsoft Graph Connector limited to one known OneDrive
    driveItem.

    This exists only to constrain the first Orchestrator integration
    test to a one-object synchronization scope.

    All retrieval behavior still uses GraphConnector's real Microsoft
    Graph request implementation.
    """

    def run(
        self,
        source_name,
    ):
        """
        Retrieve exactly the controlled OneDrive target.
        """

        if (
            source_name is None
            or str(
                source_name
            ).lower()
            != "onedrive"
        ):
            raise ValueError(
                "TargetedOneDriveConnector supports "
                "OneDrive only."
            )

        raw_object = (
            self._get_json(
                "/me/drive/items/"
                f"{ONEDRIVE_OBJECT_ID}"
            )
        )

        if not isinstance(
            raw_object,
            dict,
        ):
            raise RuntimeError(
                "Targeted OneDrive retrieval did not "
                "return a JSON object."
            )

        if (
            raw_object.get(
                "id"
            )
            != ONEDRIVE_OBJECT_ID
        ):
            raise RuntimeError(
                "Targeted OneDrive source identity mismatch."
            )

        if (
            raw_object.get(
                "name"
            )
            != ONEDRIVE_FILE_NAME
        ):
            raise RuntimeError(
                "Targeted OneDrive object name mismatch."
            )

        wrapped_object = (
            self._wrap_object(
                "driveItem",
                raw_object,
            )
        )

        connector_section = (
            ConnectorSection(
                "onedrive"
            )
        )

        connector_section.raw_objects = [
            wrapped_object
        ]

        connector_section.raw_metadata = {
            "enumeration_complete":
                True,

            "retrieval_strategy":
                "targeted_live_orchestrator_test",

            "objects_retrieved":
                1,

            "target_object_id":
                ONEDRIVE_OBJECT_ID,
        }

        connector_section.connection_succeeded = (
            True
        )

        connector_section.lock()

        print(
            "PASS: Targeted Connector retrieved exactly "
            "one OneDrive object."
        )

        print(
            f"  Name          : "
            f"{raw_object.get('name')}"
        )

        print(
            f"  Object ID     : "
            f"{raw_object.get('id')}"
        )

        print(
            f"  Last modified : "
            f"{raw_object.get('lastModifiedDateTime')}"
        )

        return connector_section


# ============================================================================
# Infrastructure
# ============================================================================


def build_live_orchestrator():
    """
    Construct SynchronizationOrchestrator using real production
    components and an authenticated AlphaOmega database connection.
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

    processing_job_repository = (
        ProcessingJobRepository(
            client
        )
    )

    connector = (
        TargetedOneDriveConnector()
    )

    translator = (
        GraphTranslator()
    )

    discovery_service = (
        DiscoveryService(
            source_repository=(
                source_repository
            ),
            knowledge_object_repository=(
                knowledge_object_repository
            ),
        )
    )

    extraction_service = (
        ExtractionService()
    )

    load_repository = (
        LoadRepository(
            client
        )
    )

    load_service = (
        LoadService(
            source_repository=(
                source_repository
            ),
            load_repository=(
                load_repository
            ),
        )
    )

    orchestrator = (
        SynchronizationOrchestrator(
            connector=connector,
            translator=translator,
            discovery_service=(
                discovery_service
            ),
            extraction_service=(
                extraction_service
            ),
            load_service=(
                load_service
            ),
            processing_job_repository=(
                processing_job_repository
            ),
            pipeline_version=(
                "lab7-live-orchestrator-v1"
            ),
        )
    )

    return (
        client,
        source_repository,
        knowledge_object_repository,
        orchestrator,
    )


# ============================================================================
# Existing Knowledge Object
# ============================================================================


def get_existing_knowledge_object(
    *,
    source_repository,
    knowledge_object_repository,
):
    """
    Capture the existing Knowledge Object state before Orchestration
    runs.
    """

    source_id = (
        source_repository.find_id_by_name(
            "OneDrive"
        )
    )

    if source_id is None:
        raise RuntimeError(
            "OneDrive Source is not registered."
        )

    knowledge_object = (
        knowledge_object_repository
        .find_by_source_identity(
            source_id=source_id,
            source_object_id=(
                ONEDRIVE_OBJECT_ID
            ),
        )
    )

    if knowledge_object is None:
        raise RuntimeError(
            "Controlled OneDrive Knowledge Object "
            "does not exist."
        )

    if (
        knowledge_object[
            "title"
        ]
        != ONEDRIVE_FILE_NAME
    ):
        raise RuntimeError(
            "Controlled Knowledge Object title mismatch."
        )

    print(
        "PASS: Existing controlled Knowledge Object located."
    )

    print(
        f"  Knowledge Object ID : "
        f"{knowledge_object['id']}"
    )

    print(
        f"  Previous hash       : "
        f"{knowledge_object['content_hash']}"
    )

    print(
        f"  Previous modified   : "
        f"{knowledge_object['source_modified_at']}"
    )

    return (
        source_id,
        knowledge_object,
    )


# ============================================================================
# Database Verification
# ============================================================================


def verify_database_result(
    *,
    client,
    source_id,
    previous_knowledge_object,
    processing_job_id,
    expected_hash,
):
    """
    Verify Orchestration updated the existing Knowledge Object
    rather than creating a duplicate.
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
            "content_hash,"
            "source_modified_at"
        )
        .eq(
            "source_id",
            source_id,
        )
        .eq(
            "source_object_id",
            ONEDRIVE_OBJECT_ID,
        )
        .execute()
    )

    records = response.data

    if (
        records is None
        or len(
            records
        )
        != 1
    ):
        raise RuntimeError(
            "Expected exactly one Knowledge Object "
            "after Orchestration."
        )

    persisted = records[0]

    if (
        persisted["id"]
        != previous_knowledge_object["id"]
    ):
        raise RuntimeError(
            "Knowledge Object identity changed."
        )

    if (
        persisted["content_hash"]
        != expected_hash
    ):
        raise RuntimeError(
            "Persisted content hash does not match "
            "Extraction output."
        )

    print(
        "PASS: Existing Knowledge Object updated in place."
    )

    print(
        f"  Knowledge Object ID : "
        f"{persisted['id']}"
    )

    print(
        f"  New hash            : "
        f"{persisted['content_hash']}"
    )

    # ------------------------------------------------------------------------
    # Sync History
    # ------------------------------------------------------------------------

    history_response = (
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
            persisted["id"],
        )
        .execute()
    )

    history_records = (
        history_response.data
    )

    if (
        history_records is None
        or len(
            history_records
        )
        != 1
    ):
        raise RuntimeError(
            "Expected exactly one Sync History event "
            "for the Orchestrator run."
        )

    history = (
        history_records[0]
    )

    if (
        str(
            history[
                "sync_event"
            ]
        ).lower()
        != "modified"
    ):
        raise RuntimeError(
            "Expected Modified Sync History event."
        )

    print(
        "PASS: Modified Sync History event verified."
    )


# ============================================================================
# Processing Job Verification
# ============================================================================


def verify_processing_job(
    *,
    client,
    processing_job_id,
):
    """
    Verify Orchestration completed its Processing Job.
    """

    response = (
        client
        .table(
            "processing_jobs"
        )
        .select(
            "id,"
            "process_type,"
            "status,"
            "pipeline_version,"
            "completed_at,"
            "error_message"
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
        or len(
            records
        )
        != 1
    ):
        raise RuntimeError(
            "Processing Job could not be verified."
        )

    job = (
        records[0]
    )

    if (
        job["status"]
        != "completed"
    ):
        raise RuntimeError(
            "Processing Job was not completed."
        )

    if (
        job["process_type"]
        != "sync"
    ):
        raise RuntimeError(
            "Processing Job process type incorrect."
        )

    if (
        job["pipeline_version"]
        != "lab7-live-orchestrator-v1"
    ):
        raise RuntimeError(
            "Processing Job pipeline version incorrect."
        )

    if (
        job["completed_at"]
        is None
    ):
        raise RuntimeError(
            "Processing Job has no completion timestamp."
        )

    if (
        job["error_message"]
        is not None
    ):
        raise RuntimeError(
            "Completed Processing Job contains an error."
        )

    print(
        "PASS: Orchestrator Processing Job completed correctly."
    )


# ============================================================================
# Main
# ============================================================================


def main():
    """
    Execute first targeted live SynchronizationOrchestrator test.
    """

    print()

    print(
        "============================================================"
    )

    print(
        "AlphaOmega First Live SynchronizationOrchestrator Test"
    )

    print(
        "============================================================"
    )

    print()

    print(
        "TARGET SCOPE: EXACTLY ONE ONEDRIVE OBJECT"
    )

    print(
        f"Target: {ONEDRIVE_FILE_NAME}"
    )

    print()

    print(
        "WARNING: This test intentionally writes to AlphaOmega."
    )

    print()

    (
        client,
        source_repository,
        knowledge_object_repository,
        orchestrator,
    ) = build_live_orchestrator()

    print(
        "PASS: Live Orchestrator infrastructure constructed."
    )

    (
        source_id,
        existing_knowledge_object,
    ) = get_existing_knowledge_object(
        source_repository=(
            source_repository
        ),
        knowledge_object_repository=(
            knowledge_object_repository
        ),
    )

    # ------------------------------------------------------------------------
    # Execute real SynchronizationOrchestrator.
    # ------------------------------------------------------------------------

    print()

    print(
        "Executing SynchronizationOrchestrator..."
    )

    print()

    result = (
        orchestrator.run(
            source_name="OneDrive",

            job_metadata={
                "test_type":
                    "targeted_live_orchestrator",

                "target":
                    ONEDRIVE_FILE_NAME,

                "target_object_id":
                    ONEDRIVE_OBJECT_ID,
            },
        )
    )

    # ------------------------------------------------------------------------
    # Basic orchestration result
    # ------------------------------------------------------------------------

    processing_job_id = (
        result[
            "processing_job_id"
        ]
    )

    associations = (
        result[
            "associations"
        ]
    )

    counts = (
        result[
            "counts"
        ]
    )

    if (
        len(
            associations
        )
        != 1
    ):
        raise RuntimeError(
            "Orchestrator did not produce exactly "
            "one association."
        )

    association = (
        associations[0]
    )

    # ------------------------------------------------------------------------
    # Translator
    # ------------------------------------------------------------------------

    if (
        association.translator_record
        is None
    ):
        raise RuntimeError(
            "Association is missing TranslatorRecord."
        )

    print(
        "PASS: TranslatorRecord attached."
    )

    # ------------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------------

    if (
        association.discovery_record
        is None
    ):
        raise RuntimeError(
            "Association is missing DiscoveryRecord."
        )

    discovery_record = (
        association.discovery_record
    )

    if (
        discovery_record.sync_state
        != SyncState.MODIFIED
    ):
        raise RuntimeError(
            "Expected MODIFIED but received "
            f"{discovery_record.sync_state}."
        )

    if (
        discovery_record.requires_extraction
        is not True
    ):
        raise RuntimeError(
            "MODIFIED record does not require Extraction."
        )

    if (
        discovery_record.knowledge_object_id
        != existing_knowledge_object["id"]
    ):
        raise RuntimeError(
            "Discovery did not preserve existing "
            "Knowledge Object identity."
        )

    print(
        "PASS: Orchestrator routed Discovery MODIFIED correctly."
    )

    print(
        f"  Comparison reason : "
        f"{discovery_record.comparison_reason}"
    )

    # ------------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------------

    if (
        association.extraction_record
        is None
    ):
        raise RuntimeError(
            "MODIFIED association has no ExtractionRecord."
        )

    extraction_record = (
        association.extraction_record
    )

    if (
        extraction_record.content_hash
        == existing_knowledge_object[
            "content_hash"
        ]
    ):
        raise RuntimeError(
            "Extracted content hash did not change."
        )

    print(
        "PASS: Orchestrator routed record through Extraction."
    )

    print(
        f"  Previous hash : "
        f"{existing_knowledge_object['content_hash']}"
    )

    print(
        f"  New hash      : "
        f"{extraction_record.content_hash}"
    )

    # ------------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------------

    expected_counts = {
        "associations":
            1,

        "translated":
            1,

        "discovered":
            1,

        "extracted":
            1,

        "new":
            0,

        "modified":
            1,

        "unchanged":
            0,
    }

    if (
        counts
        != expected_counts
    ):
        raise RuntimeError(
            "Unexpected Orchestration counts.\n"
            f"Expected: {expected_counts}\n"
            f"Actual:   {counts}"
        )

    print(
        "PASS: Orchestration counts correct."
    )

    # ------------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------------

    verify_database_result(
        client=client,
        source_id=source_id,
        previous_knowledge_object=(
            existing_knowledge_object
        ),
        processing_job_id=(
            processing_job_id
        ),
        expected_hash=(
            extraction_record.content_hash
        ),
    )

    # ------------------------------------------------------------------------
    # Processing Job
    # ------------------------------------------------------------------------

    verify_processing_job(
        client=client,
        processing_job_id=(
            processing_job_id
        ),
    )

    # ------------------------------------------------------------------------
    # Final
    # ------------------------------------------------------------------------

    print()

    print(
        "============================================================"
    )

    print(
        "FINAL RESULT"
    )

    print(
        "============================================================"
    )

    print()

    print(
        "Targeted Connector       : PASS"
    )

    print(
        "Processing Job creation  : PASS"
    )

    print(
        "TranslationInput         : PASS"
    )

    print(
        "GraphTranslator          : PASS"
    )

    print(
        "Discovery MODIFIED       : PASS"
    )

    print(
        "Extraction               : PASS"
    )

    print(
        "Load                     : PASS"
    )

    print(
        "Existing KO ID preserved : PASS"
    )

    print(
        "Modified Sync History    : PASS"
    )

    print(
        "Processing Job completion: PASS"
    )

    print()

    print(
        "FIRST LIVE SYNCHRONIZATION ORCHESTRATOR "
        "TEST PASSED."
    )

    print()


if __name__ == "__main__":
    main()