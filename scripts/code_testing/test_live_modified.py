"""
Live MODIFIED Integration Test

Purpose:
    Validates the targeted live AlphaOmega MODIFIED synchronization path for
    controlled OneDrive and OneNote content.

Verifies:
    - Existing target Knowledge Objects can be resolved before processing.
    - Live OneDrive and OneNote source objects can be retrieved and translated.
    - Discovery classifies changed source objects as MODIFIED.
    - MODIFIED records proceed through Extraction.
    - Load updates the existing Knowledge Object rather than creating a new
      identity.
    - MODIFIED synchronization history is recorded.
    - Processing Job state reflects successful or failed processing.

Does NOT:
    - Perform broad OneDrive or OneNote synchronization.
    - Test the NEW synchronization path.
    - Test the UNCHANGED synchronization path.
    - Modify OneDrive or OneNote source content.
"""

from datetime import datetime, timezone
from uuid import uuid4
from scripts.sync.sync_translation_input import (
    TranslationInput,
)

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

from scripts.sync.sync_association import (
    SynchronizationAssociation,
)

from scripts.sync.sync_state import (
    SyncState,
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


# ============================================================================
# Targets
# ============================================================================


ONEDRIVE_FILE_NAME = (
    "Bogmire Introduction Draft v1.docx"
)

ONEDRIVE_OBJECT_ID = (
    "70EE5AA1D6A4DA1F!sac3f611bf898418d8a31206c7780357c"
)


ONENOTE_PAGE_NAME = (
    "Blacksmith Lingo"
)

ONENOTE_PAGE_ID = (
    "0-c95a5657f28b44aca521bda1767279d9!"
    "1-70EE5AA1D6A4DA1F!80852"
)


# ============================================================================
# Database Infrastructure
# ============================================================================


def build_database_infrastructure():

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

    return (
        client,
        source_repository,
        knowledge_object_repository,
        discovery_service,
        load_service,
    )


# ============================================================================
# Processing Job
# ============================================================================


def create_processing_job(
    client,
):

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
                    "lab7-targeted-live-modified",

                "metadata":
                    {
                        "test_type":
                            "targeted_live_modified",

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
            "Unable to create MODIFIED test Processing Job."
        )

    print(
        "PASS: MODIFIED test Processing Job created."
    )

    return records[0]["id"]


def complete_processing_job(
    client,
    processing_job_id,
):

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

    if (
        response.data is None
        or len(response.data) != 1
    ):
        raise RuntimeError(
            "Unable to complete MODIFIED Processing Job."
        )

    print(
        "PASS: MODIFIED test Processing Job completed."
    )


def fail_processing_job(
    client,
    processing_job_id,
    error,
):

    try:

        completed_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        client.table(
            "processing_jobs"
        ).update(
            {
                "status":
                    "failed",

                "completed_at":
                    completed_at,

                "error_message":
                    str(error),
            }
        ).eq(
            "id",
            processing_job_id,
        ).execute()

        print(
            "PASS: Failed Processing Job closed."
        )

    except Exception as cleanup_error:

        print(
            "WARNING: Unable to close failed Processing Job."
        )

        print(
            f"Cleanup error: {cleanup_error}"
        )


# ============================================================================
# Existing State
# ============================================================================


def get_existing_knowledge_object(
    *,
    source_repository,
    knowledge_object_repository,
    source_name,
    source_object_id,
    expected_title,
):

    source_id = (
        source_repository.find_id_by_name(
            source_name
        )
    )

    if source_id is None:

        raise RuntimeError(
            f"Source '{source_name}' is not registered."
        )

    knowledge_object = (
        knowledge_object_repository
        .find_by_source_identity(
            source_id=(
                source_id
            ),
            source_object_id=(
                source_object_id
            ),
        )
    )

    if knowledge_object is None:

        raise RuntimeError(
            f"Existing Knowledge Object not found for "
            f"'{expected_title}'."
        )

    if (
        knowledge_object["title"]
        != expected_title
    ):

        raise RuntimeError(
            f"Knowledge Object title mismatch for "
            f"'{expected_title}'."
        )

    print(
        f"PASS: Existing Knowledge Object located for "
        f"'{expected_title}'."
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
# Exact Graph Retrieval
# ============================================================================


def build_connector_section(
    source_name,
    wrapped_object,
):

    section = (
        ConnectorSection(
            source_name
        )
    )

    section.connection_succeeded = True

    section.raw_objects = [
        wrapped_object,
    ]

    section.raw_metadata = {
        "enumeration_complete":
            True,

        "test_mode":
            True,

        "objects_retrieved":
            1,
    }

    section.lock()

    return section

def get_onedrive_target(
    connector,
):
    """
    Retrieve exactly one current OneDrive driveItem.

    Direct Microsoft Graph object endpoints return a single JSON
    object rather than a collection containing a 'value' field.
    """

    raw_object = (
        connector._get_json(
            "/me/drive/items/"
            f"{ONEDRIVE_OBJECT_ID}"
        )
    )

    if not isinstance(
        raw_object,
        dict,
    ):
        raise RuntimeError(
            "Unexpected OneDrive Graph response. "
            "Expected one JSON object."
        )

    if (
        raw_object.get("id")
        != ONEDRIVE_OBJECT_ID
    ):
        raise RuntimeError(
            "OneDrive source identity mismatch."
        )

    wrapped = (
        connector._wrap_object(
            "driveItem",
            raw_object,
        )
    )

    print(
        "PASS: Current OneDrive source object retrieved."
    )

    print(
        f"  Name             : "
        f"{raw_object.get('name')}"
    )

    print(
        f"  Last modified    : "
        f"{raw_object.get('lastModifiedDateTime')}"
    )

    return build_connector_section(
        "onedrive",
        wrapped,
    )

def get_onenote_target(
    connector,
):
    """
    Retrieve exactly one current OneNote page metadata object.

    Direct Microsoft Graph page endpoints return a single JSON
    object rather than a collection containing a 'value' field.
    """

    raw_object = (
        connector._get_json(
            "/me/onenote/pages/"
            f"{ONENOTE_PAGE_ID}"
        )
    )

    if not isinstance(
        raw_object,
        dict,
    ):
        raise RuntimeError(
            "Unexpected OneNote Graph response. "
            "Expected one JSON object."
        )

    if (
        raw_object.get("id")
        != ONENOTE_PAGE_ID
    ):
        raise RuntimeError(
            "OneNote source identity mismatch."
        )

    wrapped = (
        connector._wrap_object(
            "page",
            raw_object,
        )
    )

    print(
        "PASS: Current OneNote source object retrieved."
    )

    print(
        f"  Name             : "
        f"{raw_object.get('title')}"
    )

    print(
        f"  Last modified    : "
        f"{raw_object.get('lastModifiedTime')}"
    )

    return build_connector_section(
        "onenote",
        wrapped,
    )

# ============================================================================
# Correlation + Translator
# ============================================================================

def translate_target(
    connector_section,
    expected_name,
):
    """
    Apply the real synchronization correlation boundary and execute
    the real Graph Translator.

    TranslationInput represents the current orchestration-owned
    correlation mechanism used immediately after Connector and before
    Translator.
    """

    translation_input = (
        TranslationInput(
            connector_section
        )
    )

    if (
        len(
            translation_input.raw_objects
        )
        != 1
    ):
        raise RuntimeError(
            f"Expected exactly one correlated Connector object "
            f"for '{expected_name}'."
        )

    correlated_object = (
        translation_input.raw_objects[0]
    )

    correlation_id = (
        correlated_object.get(
            "correlation_id"
        )
    )

    if (
        correlation_id is None
        or not str(
            correlation_id
        ).strip()
    ):
        raise RuntimeError(
            f"Synchronization did not assign correlation identity "
            f"for '{expected_name}'."
        )

    translator = (
        GraphTranslator()
    )

    translator_section = (
        translator.run(
            translation_input
        )
    )

    if (
        translator_section.translation_succeeded
        is not True
    ):
        raise RuntimeError(
            f"Translator failed for '{expected_name}'."
        )

    if (
        len(
            translator_section.record_errors
        )
        != 0
    ):
        raise RuntimeError(
            f"Translator errors for '{expected_name}': "
            f"{translator_section.record_errors}"
        )

    if (
        len(
            translator_section.translated_records
        )
        != 1
    ):
        raise RuntimeError(
            f"Translator did not produce exactly one record "
            f"for '{expected_name}'."
        )

    record = (
        translator_section
        .translated_records[0]
    )

    if (
        record.correlation_id
        != correlation_id
    ):
        raise RuntimeError(
            f"Translator did not preserve correlation identity "
            f"for '{expected_name}'."
        )

    print(
        f"PASS: Correlation -> Translator completed for "
        f"'{expected_name}'."
    )

    print(
        f"  Correlation ID     : "
        f"{record.correlation_id}"
    )

    print(
        f"  Source object ID   : "
        f"{record.source_object_id}"
    )

    print(
        f"  Source parent ID   : "
        f"{record.source_parent_object_id}"
    )

    print(
        f"  Source modified at : "
        f"{record.source_modified_at}"
    )

    return (
        translator_section,
        record,
    )

# ============================================================================
# Discovery
# ============================================================================


def run_discovery(
    *,
    discovery_service,
    translator_section,
    expected_name,
    existing_knowledge_object,
):

    discovery_section = (
        discovery_service.run(
            translator_section
        )
    )

    if not (
        discovery_section.discovery_succeeded
    ):

        raise RuntimeError(
            f"Discovery failed for '{expected_name}'."
        )

    if (
        len(
            discovery_section.record_errors
        )
        != 0
    ):

        raise RuntimeError(
            f"Discovery errors for '{expected_name}': "
            f"{discovery_section.record_errors}"
        )

    if (
        len(
            discovery_section.discovery_records
        )
        != 1
    ):

        raise RuntimeError(
            f"Discovery did not produce exactly one record "
            f"for '{expected_name}'."
        )

    record = (
        discovery_section
        .discovery_records[0]
    )

    if (
        record.sync_state
        != SyncState.MODIFIED
    ):

        raise RuntimeError(
            f"Expected MODIFIED for '{expected_name}' but "
            f"received {record.sync_state}."
        )

    if (
        record.requires_extraction
        is not True
    ):

        raise RuntimeError(
            f"MODIFIED record '{expected_name}' does not "
            "require Extraction."
        )

    if (
        record.knowledge_object_id
        != existing_knowledge_object["id"]
    ):

        raise RuntimeError(
            f"Existing Knowledge Object identity was not "
            f"preserved for '{expected_name}'."
        )

    if (
        record.previous_content_hash
        != existing_knowledge_object["content_hash"]
    ):

        raise RuntimeError(
            f"Previous content hash was not preserved for "
            f"'{expected_name}'."
        )

    if not (
        record.comparison_reason
    ):

        raise RuntimeError(
            f"MODIFIED record '{expected_name}' has no "
            "comparison reason."
        )

    print(
        f"PASS: Discovery classified '{expected_name}' "
        "as MODIFIED."
    )

    print(
        f"  Comparison reason : "
        f"{record.comparison_reason}"
    )

    return record


# ============================================================================
# Extraction
# ============================================================================


def extract_target(
    *,
    translator_record,
    discovery_record,
    expected_name,
):

    extraction_service = (
        ExtractionService()
    )

    #
    # Extraction consumes source references. The existing targeted
    # Extraction integration proved this interface.
    #

    extraction_section = (
        extraction_service.run(
            [
                translator_record,
            ]
        )
    )

    if not (
        extraction_section.extraction_succeeded
    ):

        raise RuntimeError(
            f"Extraction failed for '{expected_name}'."
        )

    if (
        len(
            extraction_section.record_errors
        )
        != 0
    ):

        raise RuntimeError(
            f"Extraction errors for '{expected_name}': "
            f"{extraction_section.record_errors}"
        )

    if (
        len(
            extraction_section.extraction_records
        )
        != 1
    ):

        raise RuntimeError(
            f"Extraction did not produce exactly one record "
            f"for '{expected_name}'."
        )

    record = (
        extraction_section
        .extraction_records[0]
    )

    if (
        record.correlation_id
        != translator_record.correlation_id
    ):

        raise RuntimeError(
            f"Extraction correlation mismatch for "
            f"'{expected_name}'."
        )

    if (
        record.content_hash
        == discovery_record.previous_content_hash
    ):

        raise RuntimeError(
            f"Source '{expected_name}' was classified MODIFIED, "
            "but extracted canonical content hash did not change."
        )

    print(
        f"PASS: Extraction completed for '{expected_name}'."
    )

    print(
        f"  Previous hash : "
        f"{discovery_record.previous_content_hash}"
    )

    print(
        f"  New hash      : "
        f"{record.content_hash}"
    )

    return record


# ============================================================================
# Association
# ============================================================================


def build_association(
    *,
    translator_record,
    discovery_record,
    extraction_record,
):

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


def verify_updated_knowledge_object(
    *,
    client,
    source_id,
    source_object_id,
    expected_id,
    expected_hash,
    expected_title,
):

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
            f"Expected exactly one Knowledge Object for "
            f"'{expected_title}'. Found "
            f"{0 if records is None else len(records)}."
        )

    record = records[0]

    if (
        record["id"]
        != expected_id
    ):

        raise RuntimeError(
            f"Knowledge Object identity changed for "
            f"'{expected_title}'."
        )

    if (
        record["content_hash"]
        != expected_hash
    ):

        raise RuntimeError(
            f"Updated content hash mismatch for "
            f"'{expected_title}'."
        )

    print(
        f"PASS: Existing Knowledge Object updated in place for "
        f"'{expected_title}'."
    )

    print(
        f"  Knowledge Object ID : "
        f"{record['id']}"
    )

    print(
        f"  New content hash    : "
        f"{record['content_hash']}"
    )


def verify_modified_sync_history(
    *,
    client,
    processing_job_id,
    knowledge_object_id,
    source_id,
    expected_title,
):

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
            f"Expected exactly one new Sync History event for "
            f"'{expected_title}'."
        )

    record = records[0]

    if (
        record["source_id"]
        != source_id
    ):

        raise RuntimeError(
            f"Sync History source mismatch for "
            f"'{expected_title}'."
        )

    if (
        record["processing_job_id"]
        != processing_job_id
    ):

        raise RuntimeError(
            f"Sync History Processing Job mismatch for "
            f"'{expected_title}'."
        )

    if (
        str(
            record["sync_event"]
        ).lower()
        != "modified"
    ):

        raise RuntimeError(
            f"Expected Modified Sync History event for "
            f"'{expected_title}', received "
            f"'{record['sync_event']}'."
        )

    print(
        f"PASS: Modified Sync History verified for "
        f"'{expected_title}'."
    )


# ============================================================================
# Main
# ============================================================================


def main():

    print()
    print(
        "============================================================"
    )

    print(
        "AlphaOmega Targeted Live MODIFIED Integration Test"
    )

    print(
        "============================================================"
    )

    print()
    print(
        "WARNING: This test intentionally updates the two "
        "existing controlled Knowledge Objects."
    )

    print()

    (
        client,
        source_repository,
        knowledge_object_repository,
        discovery_service,
        load_service,
    ) = build_database_infrastructure()

    print(
        "PASS: Authenticated AlphaOmega database access established."
    )

    # ------------------------------------------------------------------------
    # Capture existing state BEFORE any writes.
    # ------------------------------------------------------------------------

    (
        onedrive_source_id,
        onedrive_existing,
    ) = get_existing_knowledge_object(
        source_repository=(
            source_repository
        ),
        knowledge_object_repository=(
            knowledge_object_repository
        ),
        source_name="OneDrive",
        source_object_id=(
            ONEDRIVE_OBJECT_ID
        ),
        expected_title=(
            ONEDRIVE_FILE_NAME
        ),
    )

    (
        onenote_source_id,
        onenote_existing,
    ) = get_existing_knowledge_object(
        source_repository=(
            source_repository
        ),
        knowledge_object_repository=(
            knowledge_object_repository
        ),
        source_name="OneNote",
        source_object_id=(
            ONENOTE_PAGE_ID
        ),
        expected_title=(
            ONENOTE_PAGE_NAME
        ),
    )

    # ------------------------------------------------------------------------
    # Retrieve exact current Source-of-Truth objects.
    # ------------------------------------------------------------------------

    connector = (
        GraphConnector()
    )

    print()
    print(
        "Retrieving current OneDrive source object..."
    )

    onedrive_connector_section = (
        get_onedrive_target(
            connector
        )
    )

    print(
        "Retrieving current OneNote source object..."
    )

    onenote_connector_section = (
        get_onenote_target(
            connector
        )
    )

    # ------------------------------------------------------------------------
    # Real Synchronization correlation -> Translator.
    # ------------------------------------------------------------------------

    (
        onedrive_translator_section,
        onedrive_translator_record,
    ) = translate_target(
        onedrive_connector_section,
        ONEDRIVE_FILE_NAME,
    )

    (
        onenote_translator_section,
        onenote_translator_record,
    ) = translate_target(
        onenote_connector_section,
        ONENOTE_PAGE_NAME,
    )

    # ------------------------------------------------------------------------
    # Real Discovery.
    # ------------------------------------------------------------------------

    onedrive_discovery_record = (
        run_discovery(
            discovery_service=(
                discovery_service
            ),
            translator_section=(
                onedrive_translator_section
            ),
            expected_name=(
                ONEDRIVE_FILE_NAME
            ),
            existing_knowledge_object=(
                onedrive_existing
            ),
        )
    )

    onenote_discovery_record = (
        run_discovery(
            discovery_service=(
                discovery_service
            ),
            translator_section=(
                onenote_translator_section
            ),
            expected_name=(
                ONENOTE_PAGE_NAME
            ),
            existing_knowledge_object=(
                onenote_existing
            ),
        )
    )

    # ------------------------------------------------------------------------
    # Real Extraction.
    # ------------------------------------------------------------------------

    onedrive_extraction_record = (
        extract_target(
            translator_record=(
                onedrive_translator_record
            ),
            discovery_record=(
                onedrive_discovery_record
            ),
            expected_name=(
                ONEDRIVE_FILE_NAME
            ),
        )
    )

    onenote_extraction_record = (
        extract_target(
            translator_record=(
                onenote_translator_record
            ),
            discovery_record=(
                onenote_discovery_record
            ),
            expected_name=(
                ONENOTE_PAGE_NAME
            ),
        )
    )

    # ------------------------------------------------------------------------
    # Build real synchronization associations.
    # ------------------------------------------------------------------------

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

    # ------------------------------------------------------------------------
    # Processing Job begins immediately before persistence.
    # ------------------------------------------------------------------------

    processing_job_id = (
        create_processing_job(
            client
        )
    )

    try:

        # --------------------------------------------------------------------
        # Real MODIFIED Load.
        # --------------------------------------------------------------------

        print()
        print(
            "Executing real MODIFIED Load..."
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

        if not (
            load_section.load_succeeded
        ):

            raise RuntimeError(
                "Load stage did not complete successfully."
            )

        if (
            len(
                load_section.record_errors
            )
            != 0
        ):

            print()
            print(
                "Load produced record-level errors:"
            )

            for error in (
                load_section.record_errors
            ):

                print(
                    dict(error)
                )

            raise RuntimeError(
                "Load produced record-level errors."
            )

        if not (
            load_section.is_locked
        ):

            raise RuntimeError(
                "LoadSection was not locked."
            )

        print(
            "PASS: MODIFIED Load completed with zero "
            "record-level errors."
        )

        # --------------------------------------------------------------------
        # Verify update-in-place.
        # --------------------------------------------------------------------

        verify_updated_knowledge_object(
            client=client,
            source_id=(
                onedrive_source_id
            ),
            source_object_id=(
                ONEDRIVE_OBJECT_ID
            ),
            expected_id=(
                onedrive_existing["id"]
            ),
            expected_hash=(
                onedrive_extraction_record
                .content_hash
            ),
            expected_title=(
                ONEDRIVE_FILE_NAME
            ),
        )

        verify_updated_knowledge_object(
            client=client,
            source_id=(
                onenote_source_id
            ),
            source_object_id=(
                ONENOTE_PAGE_ID
            ),
            expected_id=(
                onenote_existing["id"]
            ),
            expected_hash=(
                onenote_extraction_record
                .content_hash
            ),
            expected_title=(
                ONENOTE_PAGE_NAME
            ),
        )

        # --------------------------------------------------------------------
        # Verify Modified Sync History.
        # --------------------------------------------------------------------

        verify_modified_sync_history(
            client=client,
            processing_job_id=(
                processing_job_id
            ),
            knowledge_object_id=(
                onedrive_existing["id"]
            ),
            source_id=(
                onedrive_source_id
            ),
            expected_title=(
                ONEDRIVE_FILE_NAME
            ),
        )

        verify_modified_sync_history(
            client=client,
            processing_job_id=(
                processing_job_id
            ),
            knowledge_object_id=(
                onenote_existing["id"]
            ),
            source_id=(
                onenote_source_id
            ),
            expected_title=(
                ONENOTE_PAGE_NAME
            ),
        )

        complete_processing_job(
            client,
            processing_job_id,
        )

    except Exception as error:

        fail_processing_job(
            client,
            processing_job_id,
            error,
        )

        raise

    # ------------------------------------------------------------------------
    # Final Result
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

    print(
        f"OneDrive: {ONEDRIVE_FILE_NAME} : MODIFIED : PASS"
    )

    print(
        f"OneNote : {ONENOTE_PAGE_NAME} : MODIFIED : PASS"
    )

    print()

    print(
        "Discovery MODIFIED       : PASS"
    )

    print(
        "Extraction new content   : PASS"
    )

    print(
        "Existing KO IDs preserved: PASS"
    )

    print(
        "Knowledge Objects updated: PASS"
    )

    print(
        "Modified Sync History    : PASS"
    )

    print()

    print(
        "Targeted live MODIFIED integration test PASSED."
    )

    print()


if __name__ == "__main__":
    main()