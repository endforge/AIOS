"""
Live OneNote Orchestrator UNCHANGED Test

Purpose:
    Validates a controlled live multi-record OneNote UNCHANGED synchronization
    run through SynchronizationOrchestrator.

Verifies:
    - Pretest persisted state can be captured for the controlled scope.
    - Existing OneNote content is classified correctly when source facts
      remain unchanged.
    - UNCHANGED records do not proceed through unnecessary Extraction or Load.
    - Existing Knowledge Object state remains unchanged.
    - Synchronization associations reconcile to the expected counts.
    - The Processing Job completes successfully.

Does NOT:
    - Modify existing Knowledge Objects for UNCHANGED records.
    - Synchronize the complete OneNote Source of Truth.
    - Modify OneNote source content.
    - Test the NEW-only or MODIFIED-only scenario.
"""

from common.object_types import (
    CONTAINER,
    CONTENT,
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
EXPECTED_ASSOCIATION_COUNT = 17

PIPELINE_VERSION = (
    "lab7-live-onenote-section-unchanged-v1"
)


# ============================================================================
# Controlled Connector
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
                f"with name '{expected_name}'."
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
                "Unexpected live page count.\n"
                f"Expected: {EXPECTED_PAGE_COUNT}\n"
                f"Actual:   {len(pages)}"
            )

        if (
            len(raw_objects)
            != EXPECTED_ASSOCIATION_COUNT
        ):
            raise RuntimeError(
                "Unexpected Connector object count.\n"
                f"Expected: {EXPECTED_ASSOCIATION_COUNT}\n"
                f"Actual:   {len(raw_objects)}"
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
            "PASS: Controlled live Connector "
            "enumerated House Rules."
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
# Pre-Test Database Snapshot
# ============================================================================

def capture_pretest_snapshot(
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

        title = (
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
                "UNCHANGED test requires all "
                "16 Knowledge Objects to exist.\n"
                f"Missing: {title}"
            )

        snapshot[page_id] = {
            "id":
                knowledge_object.get("id"),

            "title":
                title,

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
            "Pre-test database snapshot "
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

def verify_associations(
    *,
    associations,
    snapshot,
):

    if (
        len(associations)
        != EXPECTED_ASSOCIATION_COUNT
    ):
        raise RuntimeError(
            "Unexpected synchronization "
            "association count.\n"
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
                "Association is missing "
                "TranslatorRecord."
            )

        if (
            translator_record.object_type
            == CONTAINER
        ):
            containers.append(
                association
            )

        elif (
            translator_record.object_type
            == CONTENT
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
            "Expected exactly 16 CONTENT records."
        )

    # ------------------------------------------------------------------------
    # CONTAINER boundary
    # ------------------------------------------------------------------------

    container = (
        containers[0]
    )

    if (
        container.discovery_record
        is not None
    ):
        raise RuntimeError(
            "CONTAINER crossed into Discovery."
        )

    if (
        container.extraction_record
        is not None
    ):
        raise RuntimeError(
            "CONTAINER crossed into Extraction."
        )

    print(
        "PASS: CONTAINER terminated after Translator."
    )

    # ------------------------------------------------------------------------
    # CONTENT behavior
    # ------------------------------------------------------------------------

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
                "CONTENT association was not present "
                "in the pre-test snapshot."
            )

        discovery_record = (
            association.discovery_record
        )

        if discovery_record is None:
            raise RuntimeError(
                "CONTENT association did not "
                "reach Discovery."
            )

        if (
            discovery_record.sync_state
            != SyncState.UNCHANGED
        ):
            raise RuntimeError(
                "Expected CONTENT record to be "
                "UNCHANGED.\n"
                f"Page: {previous['title']}\n"
                f"Actual: {discovery_record.sync_state}"
            )

        if (
            discovery_record.requires_extraction
            is not False
        ):
            raise RuntimeError(
                "UNCHANGED record incorrectly "
                "requires Extraction."
            )

        if (
            discovery_record.knowledge_object_id
            != previous["id"]
        ):
            raise RuntimeError(
                "Discovery Knowledge Object "
                "identity mismatch."
            )

        if (
            discovery_record.previous_content_hash
            != previous["content_hash"]
        ):
            raise RuntimeError(
                "Discovery previous content hash "
                "does not match stored state."
            )

        if (
            association.extraction_record
            is not None
        ):
            raise RuntimeError(
                "UNCHANGED record reached Extraction."
            )

    print(
        "PASS: All 16 CONTENT records classified "
        "UNCHANGED."
    )

    print(
        "PASS: No CONTENT record reached Extraction."
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
            17,

        "discovered":
            16,

        "extracted":
            0,

        "new":
            0,

        "modified":
            0,

        "unchanged":
            16,
    }

    if counts != expected:
        raise RuntimeError(
            "Unexpected orchestration counts.\n"
            f"Expected: {expected}\n"
            f"Actual:   {counts}"
        )

    print(
        "PASS: Orchestration counts reconcile."
    )


# ============================================================================
# Database Verification
# ============================================================================

def verify_database_unchanged(
    *,
    client,
    source_id,
    snapshot,
    processing_job_id,
):

    for (
        source_object_id,
        previous,
    ) in snapshot.items():

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
                "Knowledge Object could not "
                "be uniquely verified.\n"
                f"Page: {previous['title']}"
            )

        current = (
            records[0]
        )

        if (
            current["id"]
            != previous["id"]
        ):
            raise RuntimeError(
                "Knowledge Object identity changed.\n"
                f"Page: {previous['title']}"
            )

        if (
            current["content_hash"]
            != previous["content_hash"]
        ):
            raise RuntimeError(
                "UNCHANGED Knowledge Object hash changed.\n"
                f"Page: {previous['title']}"
            )

        if (
            current["source_modified_at"]
            != previous["source_modified_at"]
        ):
            raise RuntimeError(
                "UNCHANGED Knowledge Object timestamp changed.\n"
                f"Page: {previous['title']}"
            )

    print(
        "PASS: All 16 Knowledge Objects remained "
        "unchanged in the database."
    )

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

    if history:
        raise RuntimeError(
            "UNCHANGED synchronization unexpectedly "
            "created Sync History events.\n"
            f"Actual: {len(history)}"
        )

    print(
        "PASS: No Sync History events created."
    )


# ============================================================================
# Processing Job Verification
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
            "Processing Job could not "
            "be uniquely verified."
        )

    job = (
        records[0]
    )

    if job["process_type"] != "sync":
        raise RuntimeError(
            "Unexpected Processing Job process_type."
        )

    if job["status"] != "completed":
        raise RuntimeError(
            "Processing Job did not complete."
        )

    if (
        job["pipeline_version"]
        != PIPELINE_VERSION
    ):
        raise RuntimeError(
            "Unexpected Processing Job "
            "pipeline_version."
        )

    if job["completed_at"] is None:
        raise RuntimeError(
            "Processing Job has no completed_at."
        )

    if job["error_message"] is not None:
        raise RuntimeError(
            "Completed Processing Job contains "
            "an error_message."
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
        "AlphaOmega Live Multi-Record OneNote "
        "UNCHANGED Test"
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
        "  17 associations"
    )

    print(
        "  17 translated"
    )

    print(
        "  1 CONTAINER stops after Translator"
    )

    print(
        "  16 CONTENT reach Discovery"
    )

    print(
        "  16 UNCHANGED"
    )

    print(
        "  0 Extraction"
    )

    print(
        "  0 Load"
    )

    print(
        "  0 Sync History"
    )

    print()

    print(
        "WARNING: This test creates a "
        "Processing Job in AlphaOmega."
    )

    print()

    (
        client,
        source_repository,
        knowledge_object_repository,
        orchestrator,
    ) = build_live_orchestrator()

    print(
        "PASS: Live Orchestrator infrastructure "
        "constructed."
    )

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        "PRECONDITION PHASE"
    )

    print(
        "------------------------------------------------------------"
    )

    print()

    (
        source_id,
        snapshot,
    ) = capture_pretest_snapshot(
        source_repository=(
            source_repository
        ),
        knowledge_object_repository=(
            knowledge_object_repository
        ),
    )

    print()

    print(
        "ALL PRECONDITIONS PASSED."
    )

    print()

    print(
        "Executing normal SynchronizationOrchestrator..."
    )

    print()

    result = (
        orchestrator.run(
            source_name="OneNote",

            job_metadata={
                "test_type":
                    "live_multi_record_unchanged",

                "target_notebook":
                    NOTEBOOK_NAME,

                "target_section":
                    SECTION_NAME,

                "expected_pages":
                    EXPECTED_PAGE_COUNT,
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

    verify_associations(
        associations=associations,
        snapshot=snapshot,
    )

    print()

    verify_counts(
        counts
    )

    print()

    verify_database_unchanged(
        client=client,
        source_id=source_id,
        snapshot=snapshot,
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
        "Associations                  : 17 : PASS"
    )

    print(
        "Translator records            : 17 : PASS"
    )

    print(
        "CONTAINER stopped             :  1 : PASS"
    )

    print(
        "Discovery CONTENT records     : 16 : PASS"
    )

    print(
        "UNCHANGED                     : 16 : PASS"
    )

    print(
        "Extraction                    :  0 : PASS"
    )

    print(
        "Load                          :  0 : PASS"
    )

    print(
        "Sync History events           :  0 : PASS"
    )

    print(
        "Knowledge Objects altered     :  0 : PASS"
    )

    print(
        "Processing Job                : COMPLETED"
    )

    print()

    print(
        "LIVE MULTI-RECORD ONENOTE "
        "UNCHANGED TEST PASSED."
    )

    print()


if __name__ == "__main__":
    main()