"""
Live OneNote Orchestrator MODIFIED Test

Purpose:
    Validates a controlled live multi-record OneNote MODIFIED synchronization
    run through SynchronizationOrchestrator.

Verifies:
    - Existing persisted state can be captured before synchronization.
    - The controlled OneNote scope is processed through the production
      synchronization stages.
    - Expected records enter the MODIFIED path.
    - Eligible changed content proceeds through Extraction and Load.
    - Existing Knowledge Object identities are preserved during updates.
    - Database results match orchestration decisions.
    - Processing Job state reflects successful completion.

Does NOT:
    - Synchronize the complete OneNote Source of Truth.
    - Test the NEW-only scenario.
    - Modify OneNote source content.
    - Create replacement Knowledge Object identities for MODIFIED records.
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


NOTEBOOK_NAME = "Mimic's Tavern"
SECTION_NAME = "House Rules"

EXPECTED_PAGE_COUNT = 16
EXPECTED_CONTAINER_COUNT = 1
EXPECTED_ASSOCIATION_COUNT = 17

PIPELINE_VERSION = (
    "lab7-live-onenote-section-modified-v1"
)


# ============================================================================
# Bounded Connector
# ============================================================================

class HouseRulesOneNoteConnector(
    GraphConnector
):

    @staticmethod
    def _find_named_object(
        objects,
        expected_name,
        name_field,
        object_type,
    ):

        matches = []

        for item in objects:

            actual_name = item.get(
                name_field
            )

            if (
                actual_name
                and actual_name.strip().casefold()
                == expected_name.casefold()
            ):
                matches.append(
                    item
                )

        if not matches:
            raise RuntimeError(
                f"{object_type} not found: "
                f"'{expected_name}'."
            )

        if len(matches) > 1:
            raise RuntimeError(
                f"Multiple {object_type} objects found "
                f"with the name '{expected_name}'."
            )

        return matches[0]

    def run(
        self,
        source_name,
    ):

        if (
            source_name is None
            or str(source_name).lower()
            != "onenote"
        ):
            raise ValueError(
                "Controlled Connector supports "
                "OneNote only."
            )

        notebooks = (
            self._get_collection(
                "/me/onenote/notebooks"
            )
        )

        notebook = (
            self._find_named_object(
                notebooks,
                NOTEBOOK_NAME,
                "displayName",
                "notebook",
            )
        )

        notebook_id = (
            notebook.get("id")
        )

        if not notebook_id:
            raise RuntimeError(
                "Notebook is missing Graph ID."
            )

        sections = (
            self._get_collection(
                "/me/onenote/notebooks/"
                f"{notebook_id}/sections"
            )
        )

        section = (
            self._find_named_object(
                sections,
                SECTION_NAME,
                "displayName",
                "section",
            )
        )

        section_id = (
            section.get("id")
        )

        if not section_id:
            raise RuntimeError(
                "Section is missing Graph ID."
            )

        live_section = (
            self._get_json(
                "/me/onenote/sections/"
                f"{section_id}"
            )
        )

        if (
            live_section.get("id")
            != section_id
        ):
            raise RuntimeError(
                "Section identity mismatch."
            )

        section_modified_at = (
            live_section.get(
                "lastModifiedDateTime"
            )
        )

        if not section_modified_at:
            raise RuntimeError(
                "Section is missing "
                "lastModifiedDateTime."
            )

        raw_objects = []

        section_path = (
            self._join_source_path(
                NOTEBOOK_NAME,
                SECTION_NAME,
            )
        )

        raw_objects.append(
            self._wrap_object(
                "section",
                live_section,
                connector_metadata={
                    "source_parent_object_id":
                        notebook_id,

                    "source_path":
                        NOTEBOOK_NAME,

                    "object_path":
                        section_path,

                    "hierarchy_verified":
                        True,
                },
            )
        )

        section_context = {
            "raw_object":
                live_section,

            "object_path":
                section_path,
        }

        self._enumerate_onenote_section_pages(
            section_context=section_context,
            raw_objects=raw_objects,
        )

        pages = [
            item
            for item in raw_objects
            if (
                item.get(
                    "source_object_type"
                )
                == "page"
            )
        ]

        if (
            len(pages)
            != EXPECTED_PAGE_COUNT
        ):
            raise RuntimeError(
                "Unexpected page count.\n"
                f"Expected: {EXPECTED_PAGE_COUNT}\n"
                f"Actual:   {len(pages)}"
            )

        page_ids = [
            page["raw_object"].get("id")
            for page in pages
        ]

        if (
            len(set(page_ids))
            != EXPECTED_PAGE_COUNT
        ):
            raise RuntimeError(
                "Page identities are not unique."
            )

        if (
            len(raw_objects)
            != EXPECTED_ASSOCIATION_COUNT
        ):
            raise RuntimeError(
                "Unexpected Connector object count."
            )

        connector_section = (
            ConnectorSection(
                "onenote"
            )
        )

        connector_section.raw_objects = (
            raw_objects
        )

        connector_section.raw_metadata = {
            "enumeration_complete":
                True,

            "test_mode":
                True,

            "target_notebook":
                NOTEBOOK_NAME,

            "target_section":
                SECTION_NAME,

            "target_section_id":
                section_id,

            "source_section_modified_at":
                section_modified_at,

            "pages_retrieved":
                len(pages),

            "objects_retrieved":
                len(raw_objects),
        }

        connector_section.connection_succeeded = (
            True
        )

        self._validate_completed_section(
            connector_section
        )

        connector_section.lock()

        print(
            "PASS: Controlled Connector enumerated "
            "House Rules."
        )

        print(
            f"  Section modified : "
            f"{section_modified_at}"
        )

        print(
            f"  Pages            : {len(pages)}"
        )

        print(
            f"  Connector objects: {len(raw_objects)}"
        )

        return connector_section


# ============================================================================
# Infrastructure
# ============================================================================

def build_live_orchestrator():

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
        HouseRulesOneNoteConnector()
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
                PIPELINE_VERSION
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
# Pre-Test Snapshot
# ============================================================================

def snapshot_existing_state(
    *,
    source_repository,
    knowledge_object_repository,
):

    connector = (
        HouseRulesOneNoteConnector()
    )

    connector_section = (
        connector.run(
            "OneNote"
        )
    )

    pages = [
        item
        for item in connector_section.raw_objects
        if (
            item.get(
                "source_object_type"
            )
            == "page"
        )
    ]

    source_id = (
        source_repository.find_id_by_name(
            "OneNote"
        )
    )

    if source_id is None:
        raise RuntimeError(
            "OneNote Source is not registered."
        )

    snapshot = {}

    for page in pages:

        raw_page = (
            page["raw_object"]
        )

        page_id = (
            raw_page.get("id")
        )

        page_title = (
            raw_page.get("title")
            or "Untitled"
        )

        knowledge_object = (
            knowledge_object_repository
            .find_by_source_identity(
                source_id=source_id,
                source_object_id=page_id,
            )
        )

        if knowledge_object is None:
            raise RuntimeError(
                "MODIFIED test requires every page "
                "to already exist.\n"
                f"Missing: {page_title}"
            )

        if not knowledge_object.get(
            "content_hash"
        ):
            raise RuntimeError(
                "Existing Knowledge Object has no "
                f"content hash: {page_title}"
            )

        snapshot[page_id] = {
            "title":
                page_title,

            "id":
                knowledge_object.get("id"),

            "content_hash":
                knowledge_object.get(
                    "content_hash"
                ),

            "source_modified_at":
                knowledge_object.get(
                    "source_modified_at"
                ),
        }

    if (
        len(snapshot)
        != EXPECTED_PAGE_COUNT
    ):
        raise RuntimeError(
            "Pre-test Knowledge Object snapshot "
            "did not reconcile."
        )

    print(
        "PASS: Pre-test database snapshot captured."
    )

    print(
        f"  Existing Knowledge Objects : "
        f"{len(snapshot)}"
    )

    return (
        source_id,
        snapshot,
    )


# ============================================================================
# Association Verification
# ============================================================================

def split_associations(
    associations,
):

    if (
        len(associations)
        != EXPECTED_ASSOCIATION_COUNT
    ):
        raise RuntimeError(
            "Unexpected association count.\n"
            f"Expected: {EXPECTED_ASSOCIATION_COUNT}\n"
            f"Actual:   {len(associations)}"
        )

    containers = []
    contents = []

    for association in associations:

        translator_record = (
            association.translator_record
        )

        if translator_record is None:
            raise RuntimeError(
                "Association is missing TranslatorRecord."
            )

        if (
            translator_record.object_type
            == "CONTAINER"
        ):
            containers.append(
                association
            )

        elif (
            translator_record.object_type
            == "CONTENT"
        ):
            contents.append(
                association
            )

        else:
            raise RuntimeError(
                "Unexpected canonical object type: "
                f"{translator_record.object_type}"
            )

    if len(containers) != 1:
        raise RuntimeError(
            "Expected exactly one CONTAINER."
        )

    if (
        len(contents)
        != EXPECTED_PAGE_COUNT
    ):
        raise RuntimeError(
            "Expected exactly 16 CONTENT associations."
        )

    return (
        containers,
        contents,
    )


def verify_pipeline(
    *,
    associations,
    snapshot,
):

    (
        containers,
        contents,
    ) = split_associations(
        associations
    )

    container = (
        containers[0]
    )

    if (
        container.discovery_record
        is not None
    ):
        raise RuntimeError(
            "CONTAINER unexpectedly reached Discovery."
        )

    if (
        container.extraction_record
        is not None
    ):
        raise RuntimeError(
            "CONTAINER unexpectedly reached Extraction."
        )

    changed = []
    same_hash = []

    for association in contents:

        translator_record = (
            association.translator_record
        )

        source_object_id = (
            translator_record.source_object_id
        )

        previous = (
            snapshot.get(
                source_object_id
            )
        )

        if previous is None:
            raise RuntimeError(
                "Association source identity was not "
                "present in pre-test snapshot."
            )

        discovery_record = (
            association.discovery_record
        )

        if discovery_record is None:
            raise RuntimeError(
                "CONTENT association is missing "
                "DiscoveryRecord."
            )

        if (
            discovery_record.sync_state
            != SyncState.MODIFIED
        ):
            raise RuntimeError(
                "Expected every CONTENT record to be "
                "Discovery MODIFIED.\n"
                f"Page: {previous['title']}\n"
                f"Actual: {discovery_record.sync_state}"
            )

        if (
            discovery_record.requires_extraction
            is not True
        ):
            raise RuntimeError(
                "MODIFIED record did not require Extraction."
            )

        if (
            discovery_record.knowledge_object_id
            != previous["id"]
        ):
            raise RuntimeError(
                "Discovery did not preserve existing "
                "Knowledge Object identity."
            )

        if (
            discovery_record.previous_content_hash
            != previous["content_hash"]
        ):
            raise RuntimeError(
                "Discovery previous content hash does "
                "not match pre-test database state."
            )

        extraction_record = (
            association.extraction_record
        )

        if extraction_record is None:
            raise RuntimeError(
                "MODIFIED record is missing ExtractionRecord."
            )

        if (
            extraction_record.correlation_id
            != association.correlation_id
        ):
            raise RuntimeError(
                "Extraction correlation mismatch."
            )

        if (
            extraction_record.content_hash
            == previous["content_hash"]
        ):
            same_hash.append(
                association
            )

        else:
            changed.append(
                association
            )

    if len(changed) != 1:
        raise RuntimeError(
            "Blind change detection failed.\n"
            "Expected exactly 1 changed canonical hash.\n"
            f"Actual: {len(changed)}"
        )

    if len(same_hash) != 15:
        raise RuntimeError(
            "Same-hash count incorrect.\n"
            "Expected: 15\n"
            f"Actual:   {len(same_hash)}"
        )

    changed_record = (
        changed[0].translator_record
    )

    print(
        "PASS: Blind canonical hash classification."
    )

    print(
        "  Changed canonical content : 1"
    )

    print(
        "  Same canonical content    : 15"
    )

    print()

    print(
        "ALPHAOMEGA IDENTIFIED THE CHANGED PAGE:"
    )

    print(
        f"  {changed_record.name}"
    )

    return (
        changed,
        same_hash,
    )


# ============================================================================
# Counts
# ============================================================================

def verify_counts(
    counts,
):

    expected = {
        "associations":
            17,

        "translated":
            16,

        "discovered":
            16,

        "extracted":
            16,

        "new":
            0,

        "modified":
            16,

        "unchanged":
            0,
    }

    if counts != expected:
        raise RuntimeError(
            "Unexpected Orchestration counts.\n"
            f"Expected: {expected}\n"
            f"Actual:   {counts}"
        )

    print(
        "PASS: Orchestration counts reconcile."
    )


# ============================================================================
# Database Verification
# ============================================================================

def verify_database(
    *,
    client,
    source_id,
    snapshot,
    changed,
    same_hash,
    processing_job_id,
):

    changed_association = (
        changed[0]
    )

    changed_record = (
        changed_association.translator_record
    )

    changed_extraction = (
        changed_association.extraction_record
    )

    changed_id = (
        changed_record.source_object_id
    )

    previous_changed = (
        snapshot[changed_id]
    )

    # ------------------------------------------------------------------------
    # Changed record
    # ------------------------------------------------------------------------

    response = (
        client
        .table(
            "knowledge_objects"
        )
        .select(
            "id,"
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
            changed_id,
        )
        .execute()
    )

    records = (
        response.data
        or []
    )

    if len(records) != 1:
        raise RuntimeError(
            "Changed Knowledge Object could not "
            "be uniquely verified."
        )

    persisted_changed = (
        records[0]
    )

    if (
        persisted_changed["id"]
        != previous_changed["id"]
    ):
        raise RuntimeError(
            "Changed Knowledge Object identity changed."
        )

    if (
        persisted_changed["content_hash"]
        != changed_extraction.content_hash
    ):
        raise RuntimeError(
            "Changed Knowledge Object did not persist "
            "the extracted canonical hash."
        )

    if (
        persisted_changed["content_hash"]
        == previous_changed["content_hash"]
    ):
        raise RuntimeError(
            "Changed Knowledge Object still has "
            "its previous content hash."
        )

    if (
        persisted_changed["source_modified_at"]
        != changed_record.source_modified_at
    ):
        raise RuntimeError(
            "Changed Knowledge Object did not persist "
            "the new source modification timestamp."
        )

    print(
        "PASS: Genuine MODIFIED Knowledge Object "
        "updated in place."
    )

    # ------------------------------------------------------------------------
    # Same-hash records
    # ------------------------------------------------------------------------

    for association in same_hash:

        translator_record = (
            association.translator_record
        )

        source_object_id = (
            translator_record.source_object_id
        )

        previous = (
            snapshot[source_object_id]
        )

        response = (
            client
            .table(
                "knowledge_objects"
            )
            .select(
                "id,"
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

        records = (
            response.data
            or []
        )

        if len(records) != 1:
            raise RuntimeError(
                "Same-hash Knowledge Object could "
                "not be uniquely verified."
            )

        persisted = (
            records[0]
        )

        if (
            persisted["id"]
            != previous["id"]
        ):
            raise RuntimeError(
                "Same-hash Knowledge Object identity changed."
            )

        if (
            persisted["content_hash"]
            != previous["content_hash"]
        ):
            raise RuntimeError(
                "Same-hash Knowledge Object content changed."
            )

        if (
            persisted["source_modified_at"]
            != previous["source_modified_at"]
        ):
            raise RuntimeError(
                "Same-hash Knowledge Object "
                "source_modified_at changed."
            )

    print(
        "PASS: 15 same-hash Knowledge Objects "
        "remained unchanged."
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
            "knowledge_object_id,"
            "sync_event"
        )
        .eq(
            "processing_job_id",
            processing_job_id,
        )
        .execute()
    )

    history = (
        history_response.data
        or []
    )

    if len(history) != 1:
        raise RuntimeError(
            "Expected exactly one Sync History event.\n"
            f"Actual: {len(history)}"
        )

    event = (
        history[0]
    )

    if (
        event["knowledge_object_id"]
        != persisted_changed["id"]
    ):
        raise RuntimeError(
            "Sync History event belongs to the "
            "wrong Knowledge Object."
        )

    if (
        str(event["sync_event"]).lower()
        != "modified"
    ):
        raise RuntimeError(
            "Expected MODIFIED Sync History event."
        )

    print(
        "PASS: Exactly one MODIFIED "
        "Sync History event created."
    )


# ============================================================================
# Processing Job
# ============================================================================

def verify_processing_job(
    *,
    client,
    processing_job_id,
):

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

    records = (
        response.data
        or []
    )

    if len(records) != 1:
        raise RuntimeError(
            "Processing Job could not be verified."
        )

    job = (
        records[0]
    )

    if job["status"] != "completed":
        raise RuntimeError(
            "Processing Job was not completed."
        )

    if job["process_type"] != "sync":
        raise RuntimeError(
            "Processing Job process type incorrect."
        )

    if (
        job["pipeline_version"]
        != PIPELINE_VERSION
    ):
        raise RuntimeError(
            "Processing Job pipeline version incorrect."
        )

    if job["completed_at"] is None:
        raise RuntimeError(
            "Processing Job has no completion timestamp."
        )

    if job["error_message"] is not None:
        raise RuntimeError(
            "Completed Processing Job contains an error."
        )

    print(
        "PASS: Processing Job completed correctly."
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
        "AlphaOmega Blind Live OneNote MODIFIED Test"
    )

    print(
        "============================================================"
    )

    print()

    print(
        f"Notebook : {NOTEBOOK_NAME}"
    )

    print(
        f"Section  : {SECTION_NAME}"
    )

    print(
        f"Pages    : {EXPECTED_PAGE_COUNT}"
    )

    print()

    print(
        "EXPECTED:"
    )

    print(
        "  16 Discovery MODIFIED"
    )

    print(
        "  16 Extraction"
    )

    print(
        "  1 canonical hash changed"
    )

    print(
        "  15 canonical hashes unchanged"
    )

    print(
        "  1 Load / MODIFIED persistence"
    )

    print(
        "  1 MODIFIED Sync History event"
    )

    print()

    print(
        "The changed page is intentionally UNKNOWN "
        "to this test."
    )

    print()

    print(
        "WARNING: THIS TEST WRITES TO ALPHAOMEGA."
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

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        "PRE-TEST SNAPSHOT"
    )

    print(
        "------------------------------------------------------------"
    )

    print()

    (
        source_id,
        snapshot,
    ) = snapshot_existing_state(
        source_repository=(
            source_repository
        ),
        knowledge_object_repository=(
            knowledge_object_repository
        ),
    )

    print()

    print(
        "Preconditions satisfied."
    )

    print(
        "Executing SynchronizationOrchestrator..."
    )

    print()

    result = (
        orchestrator.run(
            source_name="OneNote",

            job_metadata={
                "test_type":
                    "blind_live_multi_record_modified",

                "target_notebook":
                    NOTEBOOK_NAME,

                "target_section":
                    SECTION_NAME,

                "expected_pages":
                    EXPECTED_PAGE_COUNT,

                "expected_changed_content":
                    1,
            },
        )
    )

    processing_job_id = (
        result["processing_job_id"]
    )

    associations = (
        result["associations"]
    )

    counts = (
        result["counts"]
    )

    print(
        "PASS: SynchronizationOrchestrator returned."
    )

    print(
        f"  Processing Job ID : "
        f"{processing_job_id}"
    )

    print()

    (
        changed,
        same_hash,
    ) = verify_pipeline(
        associations=associations,
        snapshot=snapshot,
    )

    print()

    verify_counts(
        counts
    )

    print()

    verify_database(
        client=client,
        source_id=source_id,
        snapshot=snapshot,
        changed=changed,
        same_hash=same_hash,
        processing_job_id=(
            processing_job_id
        ),
    )

    print()

    verify_processing_job(
        client=client,
        processing_job_id=(
            processing_job_id
        ),
    )

    print()

    changed_record = (
        changed[0].translator_record
    )

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
        "Synchronization associations : 17 : PASS"
    )

    print(
        "  CONTAINER                   : 1 : PASS"
    )

    print(
        "  CONTENT                     : 16 : PASS"
    )

    print(
        "Discovery MODIFIED            : 16 : PASS"
    )

    print(
        "Extraction                    : 16 : PASS"
    )

    print(
        "Canonical hash changed        : 1 : PASS"
    )

    print(
        "Canonical hash unchanged      : 15 : PASS"
    )

    print(
        "Knowledge Objects updated     : 1 : PASS"
    )

    print(
        "Knowledge Objects unchanged   : 15 : PASS"
    )

    print(
        "MODIFIED Sync History events  : 1 : PASS"
    )

    print(
        "Processing Job completion     : PASS"
    )

    print()

    print(
        "CHANGED PAGE IDENTIFIED BY ALPHAOMEGA:"
    )

    print(
        f"  {changed_record.name}"
    )

    print()

    print(
        "BLIND LIVE MULTI-RECORD "
        "MODIFIED TEST PASSED."
    )

    print()


if __name__ == "__main__":
    main()