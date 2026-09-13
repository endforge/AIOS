"""
Live OneNote Orchestrator NEW Test

Purpose:
    Validates a controlled live multi-record OneNote NEW synchronization run
    through SynchronizationOrchestrator.

Verifies:
    - The Mimic's Tavern House Rules Section is identified exactly.
    - The expected controlled page inventory exists before synchronization.
    - Target page identities do not already exist in knowledge_objects.
    - The controlled scope produces the expected synchronization associations.
    - CONTENT records are classified NEW.
    - NEW content proceeds through Extraction and Load.
    - New Knowledge Objects are persisted.
    - NEW synchronization history events are recorded.
    - The Processing Job completes successfully.

Does NOT:
    - Execute synchronization when safety preconditions fail.
    - Synchronize the complete OneNote Source of Truth.
    - Modify OneNote source content.
    - Treat the containing Section as a Knowledge Object.
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
# Controlled Test Scope
# ============================================================================

NOTEBOOK_NAME = "Mimic's Tavern"
SECTION_NAME = "House Rules"

EXPECTED_PAGE_COUNT = 16
EXPECTED_CONTAINER_COUNT = 1
EXPECTED_ASSOCIATION_COUNT = (
    EXPECTED_PAGE_COUNT
    + EXPECTED_CONTAINER_COUNT
)

PIPELINE_VERSION = (
    "lab7-live-orchestrator-onenote-section-new-v1"
)


# ============================================================================
# Bounded Live Connector
# ============================================================================

class HouseRulesOneNoteConnector(
    GraphConnector
):
    """
    Test-only Graph Connector constrained to exactly one
    known OneNote Section.

    The Connector:

        1. Locates Mimic's Tavern.
        2. Locates House Rules.
        3. Preserves the real Section object.
        4. Uses GraphConnector's production
           _enumerate_onenote_section_pages() implementation.
        5. Returns the Section plus its pages.

    No synchronization behavior is reimplemented here.
    """

    @staticmethod
    def _find_named_object(
        objects,
        expected_name,
        name_field,
        object_type,
    ):
        """
        Locate exactly one Graph object by case-insensitive name.
        """

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
        """
        Enumerate exactly the controlled House Rules Section.
        """

        if (
            source_name is None
            or str(source_name).lower()
            != "onenote"
        ):
            raise ValueError(
                "HouseRulesOneNoteConnector supports "
                "OneNote only."
            )

        # --------------------------------------------------------------------
        # Locate Notebook
        # --------------------------------------------------------------------

        notebooks = (
            self._get_collection(
                "/me/onenote/notebooks"
            )
        )

        notebook = (
            self._find_named_object(
                objects=notebooks,
                expected_name=NOTEBOOK_NAME,
                name_field="displayName",
                object_type="notebook",
            )
        )

        notebook_id = (
            notebook.get(
                "id"
            )
        )

        if not notebook_id:
            raise RuntimeError(
                "Target Notebook is missing "
                "its Microsoft Graph ID."
            )

        # --------------------------------------------------------------------
        # Locate Section
        # --------------------------------------------------------------------

        sections = (
            self._get_collection(
                "/me/onenote/notebooks/"
                f"{notebook_id}/sections"
            )
        )

        section = (
            self._find_named_object(
                objects=sections,
                expected_name=SECTION_NAME,
                name_field="displayName",
                object_type="section",
            )
        )

        section_id = (
            section.get(
                "id"
            )
        )

        if not section_id:
            raise RuntimeError(
                "Target Section is missing "
                "its Microsoft Graph ID."
            )

        # --------------------------------------------------------------------
        # Retrieve current Section state
        # --------------------------------------------------------------------

        live_section = (
            self._get_json(
                "/me/onenote/sections/"
                f"{section_id}"
            )
        )

        if not isinstance(
            live_section,
            dict,
        ):
            raise RuntimeError(
                "Unexpected OneNote Section response."
            )

        if (
            live_section.get("id")
            != section_id
        ):
            raise RuntimeError(
                "OneNote Section identity mismatch."
            )

        section_modified_at = (
            live_section.get(
                "lastModifiedDateTime"
            )
        )

        if not section_modified_at:
            raise RuntimeError(
                "Target OneNote Section is missing "
                "lastModifiedDateTime."
            )

        # --------------------------------------------------------------------
        # Build Connector output
        # --------------------------------------------------------------------

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

        # --------------------------------------------------------------------
        # Production OneNote page enumeration
        # --------------------------------------------------------------------

        self._enumerate_onenote_section_pages(
            section_context=section_context,
            raw_objects=raw_objects,
        )

        # --------------------------------------------------------------------
        # Verify exact bounded source scope
        # --------------------------------------------------------------------

        page_objects = [
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
            len(page_objects)
            != EXPECTED_PAGE_COUNT
        ):
            raise RuntimeError(
                "Controlled OneNote Section page count "
                "changed before synchronization.\n"
                f"Expected: {EXPECTED_PAGE_COUNT}\n"
                f"Actual:   {len(page_objects)}"
            )

        page_ids = [
            item[
                "raw_object"
            ].get(
                "id"
            )
            for item in page_objects
        ]

        if any(
            page_id is None
            for page_id in page_ids
        ):
            raise RuntimeError(
                "One or more controlled OneNote pages "
                "are missing their Graph ID."
            )

        if (
            len(set(page_ids))
            != EXPECTED_PAGE_COUNT
        ):
            raise RuntimeError(
                "Controlled OneNote Section does not "
                "contain 16 unique page identities."
            )

        if (
            len(raw_objects)
            != EXPECTED_ASSOCIATION_COUNT
        ):
            raise RuntimeError(
                "Controlled Connector object count "
                "did not reconcile.\n"
                f"Expected: {EXPECTED_ASSOCIATION_COUNT}\n"
                f"Actual:   {len(raw_objects)}"
            )

        # --------------------------------------------------------------------
        # ConnectorSection
        # --------------------------------------------------------------------

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

            "retrieval_strategy":
                "bounded_live_section_using_"
                "production_page_enumeration",

            "target_notebook":
                NOTEBOOK_NAME,

            "target_notebook_id":
                notebook_id,

            "target_section":
                SECTION_NAME,

            "target_section_id":
                section_id,

            "source_section_modified_at":
                section_modified_at,

            "pages_retrieved":
                len(page_objects),

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
            f"  Notebook         : {NOTEBOOK_NAME}"
        )

        print(
            f"  Section          : {SECTION_NAME}"
        )

        print(
            f"  Section ID       : {section_id}"
        )

        print(
            f"  Section modified : {section_modified_at}"
        )

        print(
            f"  Pages            : {len(page_objects)}"
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
# Independent Precondition Check
# ============================================================================

def get_controlled_page_inventory(
    connector,
):
    """
    Independently execute the bounded Connector before Synchronization
    so database preconditions can be verified before any writes occur.
    """

    connector_section = (
        connector.run(
            "OneNote"
        )
    )

    pages = [
        item
        for item
        in connector_section.raw_objects
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
            "Precondition inventory did not return "
            "exactly 16 pages."
        )

    return pages


def verify_no_existing_knowledge_objects(
    *,
    source_repository,
    knowledge_object_repository,
    pages,
):
    """
    Refuse to execute Synchronization if any controlled page already
    exists in AlphaOmega.
    """

    source_id = (
        source_repository.find_id_by_name(
            "OneNote"
        )
    )

    if source_id is None:
        raise RuntimeError(
            "OneNote Source is not registered."
        )

    existing = []

    for page in pages:

        raw_page = (
            page[
                "raw_object"
            ]
        )

        page_id = (
            raw_page.get(
                "id"
            )
        )

        page_title = (
            raw_page.get(
                "title"
            )
            or "Untitled"
        )

        knowledge_object = (
            knowledge_object_repository
            .find_by_source_identity(
                source_id=source_id,
                source_object_id=page_id,
            )
        )

        if knowledge_object is not None:

            existing.append(
                {
                    "title":
                        page_title,

                    "source_object_id":
                        page_id,

                    "knowledge_object_id":
                        knowledge_object.get(
                            "id"
                        ),
                }
            )

    if existing:

        print()

        print(
            "PRECONDITION FAILURE:"
        )

        print(
            "One or more House Rules pages already "
            "exist in AlphaOmega."
        )

        for record in existing:

            print(
                f"  {record['title']} : "
                f"{record['knowledge_object_id']}"
            )

        raise RuntimeError(
            "Synchronization aborted before writes "
            "because the NEW-only precondition failed."
        )

    print(
        "PASS: Database precondition verified."
    )

    print(
        "  Existing controlled Knowledge Objects : 0"
    )

    print(
        f"  Expected NEW records                  : "
        f"{EXPECTED_PAGE_COUNT}"
    )

    return source_id


# ============================================================================
# Association Helpers
# ============================================================================

def split_associations(
    associations,
):
    """
    Split Orchestrator associations by canonical object type.
    """

    if (
        len(associations)
        != EXPECTED_ASSOCIATION_COUNT
    ):
        raise RuntimeError(
            "Unexpected synchronization association count.\n"
            f"Expected: {EXPECTED_ASSOCIATION_COUNT}\n"
            f"Actual:   {len(associations)}"
        )

    content_associations = []
    container_associations = []

    for association in associations:

        if (
            association.translator_record
            is None
        ):
            raise RuntimeError(
                "Association is missing TranslatorRecord."
            )

        translator_record = (
            association.translator_record
        )

        if (
            translator_record.object_type
            == "CONTENT"
        ):
            content_associations.append(
                association
            )

        elif (
            translator_record.object_type
            == "CONTAINER"
        ):
            container_associations.append(
                association
            )

        else:
            raise RuntimeError(
                "Unexpected canonical object type: "
                f"{translator_record.object_type}"
            )

    if (
        len(content_associations)
        != EXPECTED_PAGE_COUNT
    ):
        raise RuntimeError(
            "Unexpected CONTENT association count.\n"
            f"Expected: {EXPECTED_PAGE_COUNT}\n"
            f"Actual:   {len(content_associations)}"
        )

    if (
        len(container_associations)
        != EXPECTED_CONTAINER_COUNT
    ):
        raise RuntimeError(
            "Unexpected CONTAINER association count.\n"
            f"Expected: {EXPECTED_CONTAINER_COUNT}\n"
            f"Actual:   {len(container_associations)}"
        )

    return (
        container_associations,
        content_associations,
    )


# ============================================================================
# Association Verification
# ============================================================================

def verify_associations(
    associations,
):
    """
    Verify:
        - 17 total associations
        - 1 CONTAINER
        - 16 CONTENT
        - CONTAINER does not reach Discovery or Extraction
        - all CONTENT records are NEW
        - all CONTENT records reach Extraction
    """

    (
        container_associations,
        content_associations,
    ) = split_associations(
        associations
    )

    # ------------------------------------------------------------------------
    # Verify CONTAINER termination
    # ------------------------------------------------------------------------

    container_association = (
        container_associations[0]
    )

    if (
        container_association.discovery_record
        is not None
    ):
        raise RuntimeError(
            "CONTAINER unexpectedly reached Discovery."
        )

    if (
        container_association.extraction_record
        is not None
    ):
        raise RuntimeError(
            "CONTAINER unexpectedly reached Extraction."
        )

    # ------------------------------------------------------------------------
    # Verify CONTENT associations
    # ------------------------------------------------------------------------

    source_object_ids = set()

    for association in content_associations:

        translator_record = (
            association.translator_record
        )

        source_object_id = (
            translator_record.source_object_id
        )

        if not source_object_id:
            raise RuntimeError(
                "TranslatorRecord is missing source identity."
            )

        if (
            source_object_id
            in source_object_ids
        ):
            raise RuntimeError(
                "Duplicate source identity found in "
                "CONTENT associations."
            )

        source_object_ids.add(
            source_object_id
        )

        if (
            association.discovery_record
            is None
        ):
            raise RuntimeError(
                "CONTENT association is missing DiscoveryRecord."
            )

        discovery_record = (
            association.discovery_record
        )

        if (
            discovery_record.sync_state
            != SyncState.NEW
        ):
            raise RuntimeError(
                "Expected every controlled page to be NEW, "
                f"but '{translator_record.name}' was "
                f"{discovery_record.sync_state}."
            )

        if (
            discovery_record.requires_extraction
            is not True
        ):
            raise RuntimeError(
                "NEW record does not require Extraction."
            )

        if (
            association.extraction_record
            is None
        ):
            raise RuntimeError(
                "NEW association is missing ExtractionRecord."
            )

        extraction_record = (
            association.extraction_record
        )

        if (
            extraction_record.correlation_id
            != association.correlation_id
        ):
            raise RuntimeError(
                "Extraction correlation mismatch."
            )

        if not (
            extraction_record.content_hash
        ):
            raise RuntimeError(
                "ExtractionRecord is missing content hash."
            )

    if (
        len(source_object_ids)
        != EXPECTED_PAGE_COUNT
    ):
        raise RuntimeError(
            "CONTENT source identity count "
            "did not reconcile."
        )

    print(
        "PASS: Synchronization associations verified."
    )

    print(
        f"  Total associations    : "
        f"{len(associations)}"
    )

    print(
        f"  CONTAINER associations: "
        f"{len(container_associations)}"
    )

    print(
        f"  CONTENT associations  : "
        f"{len(content_associations)}"
    )

    print(
        f"  Discovery NEW         : "
        f"{len(content_associations)}"
    )

    print(
        f"  Extraction records    : "
        f"{len(content_associations)}"
    )


# ============================================================================
# Orchestration Count Verification
# ============================================================================

def verify_counts(
    counts,
):

    expected_counts = {
        "associations":
            EXPECTED_ASSOCIATION_COUNT,

        "translated":
            EXPECTED_PAGE_COUNT,

        "discovered":
            EXPECTED_PAGE_COUNT,

        "extracted":
            EXPECTED_PAGE_COUNT,

        "new":
            EXPECTED_PAGE_COUNT,

        "modified":
            0,

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
        "PASS: Orchestration counts reconcile."
    )

    print(
        f"  Associations : {counts['associations']}"
    )

    print(
        f"  Translated   : {counts['translated']}"
    )

    print(
        f"  Discovered   : {counts['discovered']}"
    )

    print(
        f"  Extracted    : {counts['extracted']}"
    )

    print(
        f"  NEW          : {counts['new']}"
    )

    print(
        f"  MODIFIED     : {counts['modified']}"
    )

    print(
        f"  UNCHANGED    : {counts['unchanged']}"
    )


# ============================================================================
# Database Verification
# ============================================================================

def verify_persistence(
    *,
    client,
    source_id,
    associations,
    processing_job_id,
):
    """
    Verify persistence for the 16 CONTENT associations only.

    The CONTAINER association must not correspond to a persisted
    Knowledge Object.
    """

    (
        container_associations,
        content_associations,
    ) = split_associations(
        associations
    )

    knowledge_object_ids = set()

    # ------------------------------------------------------------------------
    # Verify CONTENT Knowledge Objects
    # ------------------------------------------------------------------------

    for association in content_associations:

        translator_record = (
            association.translator_record
        )

        extraction_record = (
            association.extraction_record
        )

        if extraction_record is None:
            raise RuntimeError(
                "CONTENT association is missing "
                "ExtractionRecord during persistence verification."
            )

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
                translator_record.source_object_id,
            )
            .execute()
        )

        records = (
            response.data
        )

        if (
            records is None
            or len(records) != 1
        ):
            raise RuntimeError(
                "Expected exactly one persisted Knowledge Object "
                f"for '{translator_record.name}'."
            )

        persisted = (
            records[0]
        )

        knowledge_object_id = (
            persisted[
                "id"
            ]
        )

        if (
            knowledge_object_id
            in knowledge_object_ids
        ):
            raise RuntimeError(
                "Duplicate Knowledge Object identity "
                "detected after synchronization."
            )

        knowledge_object_ids.add(
            knowledge_object_id
        )

        if (
            persisted[
                "content_hash"
            ]
            != extraction_record.content_hash
        ):
            raise RuntimeError(
                "Persisted content hash does not match "
                f"Extraction for '{translator_record.name}'."
            )

        if (
            persisted[
                "source_modified_at"
            ]
            != translator_record.source_modified_at
        ):
            raise RuntimeError(
                "Persisted source_modified_at does not match "
                f"Translator for '{translator_record.name}'."
            )

    if (
        len(knowledge_object_ids)
        != EXPECTED_PAGE_COUNT
    ):
        raise RuntimeError(
            "Persisted Knowledge Object count "
            "did not reconcile."
        )

    print(
        "PASS: 16 unique CONTENT Knowledge Objects persisted."
    )

    # ------------------------------------------------------------------------
    # Verify CONTAINER was not persisted
    # ------------------------------------------------------------------------

    container_association = (
        container_associations[0]
    )

    container_record = (
        container_association.translator_record
    )

    container_response = (
        client
        .table(
            "knowledge_objects"
        )
        .select(
            "id,"
            "source_object_id,"
            "title"
        )
        .eq(
            "source_id",
            source_id,
        )
        .eq(
            "source_object_id",
            container_record.source_object_id,
        )
        .execute()
    )

    container_records = (
        container_response.data
        or []
    )

    if container_records:
        raise RuntimeError(
            "CONTAINER was unexpectedly persisted "
            "as a Knowledge Object."
        )

    print(
        "PASS: CONTAINER was not persisted "
        "as a Knowledge Object."
    )

    # ------------------------------------------------------------------------
    # Verify Sync History
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
        .execute()
    )

    history_records = (
        history_response.data
        or []
    )

    if (
        len(history_records)
        != EXPECTED_PAGE_COUNT
    ):
        raise RuntimeError(
            "Unexpected Sync History count.\n"
            f"Expected: {EXPECTED_PAGE_COUNT}\n"
            f"Actual:   {len(history_records)}"
        )

    history_knowledge_object_ids = set()

    for history in history_records:

        if (
            history[
                "source_id"
            ]
            != source_id
        ):
            raise RuntimeError(
                "Sync History source identity mismatch."
            )

        if (
            str(
                history[
                    "sync_event"
                ]
            ).lower()
            != "new"
        ):
            raise RuntimeError(
                "Expected only NEW Sync History events."
            )

        history_knowledge_object_ids.add(
            history[
                "knowledge_object_id"
            ]
        )

    if (
        history_knowledge_object_ids
        != knowledge_object_ids
    ):
        raise RuntimeError(
            "Sync History Knowledge Object identities "
            "do not match persisted CONTENT Knowledge Objects."
        )

    print(
        "PASS: 16 NEW Sync History events verified."
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
    )

    if (
        records is None
        or len(records) != 1
    ):
        raise RuntimeError(
            "Processing Job could not be verified."
        )

    job = (
        records[0]
    )

    if (
        job[
            "status"
        ]
        != "completed"
    ):
        raise RuntimeError(
            "Processing Job was not completed."
        )

    if (
        job[
            "process_type"
        ]
        != "sync"
    ):
        raise RuntimeError(
            "Processing Job process type incorrect."
        )

    if (
        job[
            "pipeline_version"
        ]
        != PIPELINE_VERSION
    ):
        raise RuntimeError(
            "Processing Job pipeline version incorrect."
        )

    if (
        job[
            "completed_at"
        ]
        is None
    ):
        raise RuntimeError(
            "Processing Job has no completion timestamp."
        )

    if (
        job[
            "error_message"
        ]
        is not None
    ):
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
        "AlphaOmega Live Multi-Record OneNote NEW Test"
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

    # ========================================================================
    # PRECONDITION PHASE
    # ========================================================================

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

    precondition_connector = (
        HouseRulesOneNoteConnector()
    )

    pages = (
        get_controlled_page_inventory(
            precondition_connector
        )
    )

    source_id = (
        verify_no_existing_knowledge_objects(
            source_repository=(
                source_repository
            ),
            knowledge_object_repository=(
                knowledge_object_repository
            ),
            pages=pages,
        )
    )

    print()

    print(
        "ALL PRECONDITIONS PASSED."
    )

    print()

    print(
        "Synchronization is now permitted to write."
    )

    print()

    # ========================================================================
    # SYNCHRONIZATION
    # ========================================================================

    print(
        "------------------------------------------------------------"
    )

    print(
        "EXECUTING SYNCHRONIZATIONORCHESTRATOR"
    )

    print(
        "------------------------------------------------------------"
    )

    print()

    result = (
        orchestrator.run(
            source_name="OneNote",

            job_metadata={
                "test_type":
                    "controlled_live_multi_record",

                "target_notebook":
                    NOTEBOOK_NAME,

                "target_section":
                    SECTION_NAME,

                "expected_pages":
                    EXPECTED_PAGE_COUNT,

                "expected_state":
                    "NEW",
            },
        )
    )

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

    print(
        "PASS: SynchronizationOrchestrator returned."
    )

    print(
        f"  Processing Job ID : {processing_job_id}"
    )

    print()

    # ========================================================================
    # VERIFY PIPELINE RESULT
    # ========================================================================

    verify_associations(
        associations
    )

    print()

    verify_counts(
        counts
    )

    print()

    # ========================================================================
    # VERIFY DATABASE AFTERMATH
    # ========================================================================

    verify_persistence(
        client=client,
        source_id=source_id,
        associations=associations,
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

    # ========================================================================
    # FINAL RESULT
    # ========================================================================

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
        "Controlled scope:"
    )

    print(
        f"  OneNote / {NOTEBOOK_NAME} / {SECTION_NAME}"
    )

    print()

    print(
        f"Source pages                  : "
        f"{EXPECTED_PAGE_COUNT}"
    )

    print(
        f"Synchronization associations  : "
        f"{EXPECTED_ASSOCIATION_COUNT} : PASS"
    )

    print(
        f"  CONTAINER                    : "
        f"{EXPECTED_CONTAINER_COUNT} : PASS"
    )

    print(
        f"  CONTENT                      : "
        f"{EXPECTED_PAGE_COUNT} : PASS"
    )

    print(
        f"Discovery NEW                 : "
        f"{EXPECTED_PAGE_COUNT} : PASS"
    )

    print(
        "Discovery MODIFIED            : 0 : PASS"
    )

    print(
        "Discovery UNCHANGED           : 0 : PASS"
    )

    print(
        f"Extraction                    : "
        f"{EXPECTED_PAGE_COUNT} : PASS"
    )

    print(
        f"Knowledge Objects created     : "
        f"{EXPECTED_PAGE_COUNT} : PASS"
    )

    print(
        "CONTAINER Knowledge Objects   : 0 : PASS"
    )

    print(
        f"NEW Sync History events       : "
        f"{EXPECTED_PAGE_COUNT} : PASS"
    )

    print(
        "Processing Job completion     : PASS"
    )

    print()

    print(
        "LIVE MULTI-RECORD ONENOTE "
        "NEW TEST PASSED."
    )

    print()


if __name__ == "__main__":
    main()