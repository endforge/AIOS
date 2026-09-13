"""
Live OneNote Synchronization Orchestrator Same-Hash Test

Purpose:
    Validates the live orchestration path where OneNote metadata causes
    Discovery to report MODIFIED but Extraction produces the same canonical
    content hash already stored for the Knowledge Object.

Verifies:
    - A changed parent Section timestamp can cause the controlled OneNote
      page to enter the MODIFIED path.
    - Translator uses the parent Section modification timestamp as the
      page's source_modified_at.
    - Discovery classifies the controlled page as MODIFIED.
    - Extraction executes for the MODIFIED record.
    - Extraction produces the same canonical content hash already stored.
    - SynchronizationOrchestrator stops the record before Load when the
      canonical content hash is unchanged.
    - The existing Knowledge Object remains unchanged.
    - No new synchronization history event is created for the controlled
      Knowledge Object.
    - The Processing Job still completes successfully.

Does NOT:
    - Update the controlled Knowledge Object when canonical content is
      unchanged.
    - Create a synchronization history event for the unchanged Knowledge
      Object.
    - Synchronize the complete OneNote Source of Truth.
    - Modify the OneNote source page.
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


ONENOTE_PAGE_NAME = (
    "Blacksmith Lingo"
)

ONENOTE_PAGE_ID = (
    "0-c95a5657f28b44aca521bda1767279d9!"
    "1-70EE5AA1D6A4DA1F!80852"
)


# ============================================================================
# Targeted OneNote Connector
# ============================================================================


class TargetedOneNoteConnector(
    GraphConnector
):
    """
    Live Graph Connector constrained to exactly one known OneNote page.

    The targeted test reproduces the production OneNote Connector
    contract by retrieving both:

        - the target OneNote Page
        - its parent Section metadata

    The parent Section lastModifiedDateTime is supplied to the
    Translator as source_section_modified_at because Microsoft Graph
    does not reliably update the Page lastModifiedDateTime when page
    content changes.

    Graph-side object type:
        page

    Canonical AlphaOmega object type after Translator:
        CONTENT
    """

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
                "TargetedOneNoteConnector supports "
                "OneNote only."
            )

        # --------------------------------------------------------------------
        # Retrieve target OneNote Page.
        # --------------------------------------------------------------------

        raw_object = (
            self._get_json(
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

        if (
            raw_object.get("title")
            != ONENOTE_PAGE_NAME
        ):
            raise RuntimeError(
                "OneNote page title mismatch."
            )

        # --------------------------------------------------------------------
        # Obtain parent Section identity.
        # --------------------------------------------------------------------

        parent_section = (
            raw_object.get(
                "parentSection"
            )
        )

        if not isinstance(
            parent_section,
            dict,
        ):
            raise RuntimeError(
                "OneNote Page did not contain "
                "parentSection metadata."
            )

        section_id = (
            parent_section.get(
                "id"
            )
        )

        if not section_id:
            raise RuntimeError(
                "OneNote Page parent Section "
                "identity is unavailable."
            )

        # --------------------------------------------------------------------
        # Retrieve live parent Section metadata.
        # --------------------------------------------------------------------

        raw_section = (
            self._get_json(
                "/me/onenote/sections/"
                f"{section_id}"
            )
        )

        if not isinstance(
            raw_section,
            dict,
        ):
            raise RuntimeError(
                "Unexpected OneNote Section Graph response."
            )

        if (
            raw_section.get("id")
            != section_id
        ):
            raise RuntimeError(
                "OneNote parent Section identity mismatch."
            )

        section_modified_at = (
            raw_section.get(
                "lastModifiedDateTime"
            )
        )

        if not section_modified_at:
            raise RuntimeError(
                "OneNote parent Section does not contain "
                "lastModifiedDateTime."
            )

        # --------------------------------------------------------------------
        # Wrap Page.
        # --------------------------------------------------------------------

        wrapped_object = (
            self._wrap_object(
                "page",
                raw_object,
            )
        )

        # --------------------------------------------------------------------
        # Reproduce production OneNote Connector contract.
        # --------------------------------------------------------------------

        connector_metadata = (
            wrapped_object.setdefault(
                "connector_metadata",
                {},
            )
        )

        connector_metadata[
            "source_section_modified_at"
        ] = section_modified_at

        # --------------------------------------------------------------------
        # Construct ConnectorSection.
        # --------------------------------------------------------------------

        section = (
            ConnectorSection(
                "onenote"
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

            "retrieval_strategy":
                "targeted_live_same_hash_test",

            "objects_retrieved":
                1,

            "target_object_id":
                ONENOTE_PAGE_ID,

            "target_section_id":
                section_id,

            "source_section_modified_at":
                section_modified_at,
        }

        section.lock()

        print(
            "PASS: Targeted Connector retrieved exactly "
            "one OneNote page."
        )

        print(
            f"  Name             : "
            f"{raw_object.get('title')}"
        )

        print(
            f"  Object ID        : "
            f"{raw_object.get('id')}"
        )

        print(
            f"  Page modified    : "
            f"{raw_object.get('lastModifiedDateTime')}"
        )

        print(
            f"  Parent Section   : "
            f"{raw_section.get('displayName')}"
        )

        print(
            f"  Section ID       : "
            f"{section_id}"
        )

        print(
            f"  Section modified : "
            f"{section_modified_at}"
        )

        return section


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
        TargetedOneNoteConnector()
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
                "lab7-live-orchestrator-onenote-same-hash-v1"
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

    source_id = (
        source_repository.find_id_by_name(
            "OneNote"
        )
    )

    if source_id is None:
        raise RuntimeError(
            "OneNote Source is not registered."
        )

    knowledge_object = (
        knowledge_object_repository
        .find_by_source_identity(
            source_id=source_id,
            source_object_id=(
                ONENOTE_PAGE_ID
            ),
        )
    )

    if knowledge_object is None:
        raise RuntimeError(
            "Controlled OneNote Knowledge Object "
            "does not exist."
        )

    if (
        knowledge_object["title"]
        != ONENOTE_PAGE_NAME
    ):
        raise RuntimeError(
            "Controlled OneNote Knowledge Object "
            "title mismatch."
        )

    print(
        "PASS: Existing controlled OneNote "
        "Knowledge Object located."
    )

    print(
        f"  Knowledge Object ID : "
        f"{knowledge_object['id']}"
    )

    print(
        f"  Stored hash         : "
        f"{knowledge_object['content_hash']}"
    )

    print(
        f"  Stored modified     : "
        f"{knowledge_object['source_modified_at']}"
    )

    return (
        source_id,
        knowledge_object,
    )


# ============================================================================
# Database Verification
# ============================================================================


def verify_database_unchanged(
    *,
    client,
    source_id,
    previous_knowledge_object,
    processing_job_id,
):
    """
    Verify Load was skipped.

    Requirements:
        - Exactly one Knowledge Object still exists.
        - Knowledge Object ID is unchanged.
        - Content hash is unchanged.
        - source_modified_at is unchanged.
        - No Sync History event exists for this KO and Processing Job.
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
            ONENOTE_PAGE_ID,
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
            "Expected exactly one OneNote Knowledge Object "
            "after same-hash Orchestration."
        )

    persisted = (
        records[0]
    )

    if (
        persisted["id"]
        != previous_knowledge_object["id"]
    ):
        raise RuntimeError(
            "OneNote Knowledge Object identity changed."
        )

    if (
        persisted["content_hash"]
        != previous_knowledge_object[
            "content_hash"
        ]
    ):
        raise RuntimeError(
            "OneNote Knowledge Object content hash changed "
            "even though Load should have been skipped."
        )

    if (
        persisted["source_modified_at"]
        != previous_knowledge_object[
            "source_modified_at"
        ]
    ):
        raise RuntimeError(
            "OneNote Knowledge Object source_modified_at changed "
            "even though Load should have been skipped."
        )

    print(
        "PASS: Existing OneNote Knowledge Object remained unchanged."
    )

    print(
        f"  Knowledge Object ID : "
        f"{persisted['id']}"
    )

    print(
        f"  Content hash        : "
        f"{persisted['content_hash']}"
    )

    print(
        f"  Stored modified     : "
        f"{persisted['source_modified_at']}"
    )

    # ------------------------------------------------------------------------
    # No Sync History should exist for this KO for this Processing Job.
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

    if history_records is None:
        history_records = []

    if (
        len(
            history_records
        )
        != 0
    ):
        raise RuntimeError(
            "Same-hash MODIFIED record created a Sync History "
            "event even though Load should have been skipped."
        )

    print(
        "PASS: No Sync History event created for same-hash record."
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
        !=
        "lab7-live-orchestrator-onenote-same-hash-v1"
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
        "PASS: Same-hash Processing Job completed correctly."
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
        "AlphaOmega Live OneNote Same-Hash Orchestrator Test"
    )

    print(
        "============================================================"
    )

    print()

    print(
        "TARGET SCOPE: EXACTLY ONE ONENOTE PAGE"
    )

    print(
        f"Target: {ONENOTE_PAGE_NAME}"
    )

    print()

    print(
        "EXPECTED SCENARIO:"
    )

    print(
        "  Parent Section timestamp changed."
    )

    print(
        "  Blacksmith Lingo content did NOT change."
    )

    print(
        "  Discovery should report MODIFIED."
    )

    print(
        "  Extraction should run."
    )

    print(
        "  Extracted hash should match stored hash."
    )

    print(
        "  Load should be skipped."
    )

    print()

    (
        client,
        source_repository,
        knowledge_object_repository,
        orchestrator,
    ) = build_live_orchestrator()

    print(
        "PASS: Live OneNote Orchestrator "
        "infrastructure constructed."
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

    print()

    print(
        "Executing SynchronizationOrchestrator..."
    )

    print()

    result = (
        orchestrator.run(
            source_name="OneNote",

            job_metadata={
                "test_type":
                    "targeted_live_same_hash",

                "target":
                    ONENOTE_PAGE_NAME,

                "target_object_id":
                    ONENOTE_PAGE_ID,
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
        associations[
            0
        ]
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

    translator_record = (
        association.translator_record
    )

    if (
        translator_record.source_object_id
        != ONENOTE_PAGE_ID
    ):
        raise RuntimeError(
            "TranslatorRecord OneNote identity mismatch."
        )

    if (
        translator_record.object_type
        != "CONTENT"
    ):
        raise RuntimeError(
            "OneNote page was not translated to canonical CONTENT."
        )

    print(
        "PASS: OneNote TranslatorRecord attached."
    )

    print(
        f"  Correlation ID     : "
        f"{translator_record.correlation_id}"
    )

    print(
        f"  Canonical type     : "
        f"{translator_record.object_type}"
    )

    print(
        f"  Source modified at : "
        f"{translator_record.source_modified_at}"
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
            "Expected OneNote MODIFIED but received "
            f"{discovery_record.sync_state}. "
            "The parent Section timestamp may not have changed "
            "since Blacksmith Lingo was last synchronized."
        )

    if (
        discovery_record.requires_extraction
        is not True
    ):
        raise RuntimeError(
            "MODIFIED OneNote record does not "
            "require Extraction."
        )

    if (
        discovery_record.knowledge_object_id
        != existing_knowledge_object[
            "id"
        ]
    ):
        raise RuntimeError(
            "Discovery did not preserve existing "
            "OneNote Knowledge Object identity."
        )

    if (
        discovery_record.previous_content_hash
        != existing_knowledge_object[
            "content_hash"
        ]
    ):
        raise RuntimeError(
            "Discovery did not preserve previous "
            "OneNote content hash."
        )

    print(
        "PASS: Discovery classified Blacksmith Lingo MODIFIED."
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
            "MODIFIED OneNote association has no "
            "ExtractionRecord."
        )

    extraction_record = (
        association.extraction_record
    )

    if (
        extraction_record.correlation_id
        != association.correlation_id
    ):
        raise RuntimeError(
            "OneNote Extraction correlation mismatch."
        )

    if (
        extraction_record.content_hash
        != existing_knowledge_object[
            "content_hash"
        ]
    ):
        raise RuntimeError(
            "Blacksmith Lingo canonical content actually changed.\n"
            f"Stored hash:    "
            f"{existing_knowledge_object['content_hash']}\n"
            f"Extracted hash: "
            f"{extraction_record.content_hash}\n"
            "This is not a valid same-hash test state."
        )

    print(
        "PASS: Extraction executed for Blacksmith Lingo."
    )

    print(
        "PASS: Extracted canonical content hash matches stored hash."
    )

    print(
        f"  Stored hash    : "
        f"{existing_knowledge_object['content_hash']}"
    )

    print(
        f"  Extracted hash : "
        f"{extraction_record.content_hash}"
    )

    # ------------------------------------------------------------------------
    # Load Gate
    # ------------------------------------------------------------------------

    if (
        result[
            "load_section"
        ]
        is not None
    ):
        raise RuntimeError(
            "LoadSection was produced for a same-hash "
            "MODIFIED record."
        )

    print(
        "PASS: Same-hash MODIFIED record stopped before Load."
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
            "Unexpected OneNote same-hash "
            "Orchestration counts.\n"
            f"Expected: {expected_counts}\n"
            f"Actual:   {counts}"
        )

    print(
        "PASS: Same-hash Orchestration counts correct."
    )

    # ------------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------------

    verify_database_unchanged(
        client=client,
        source_id=source_id,
        previous_knowledge_object=(
            existing_knowledge_object
        ),
        processing_job_id=(
            processing_job_id
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
        f"OneNote: {ONENOTE_PAGE_NAME} : "
        "MODIFIED / SAME HASH : PASS"
    )

    print()

    print(
        "Targeted Connector           : PASS"
    )

    print(
        "Processing Job creation      : PASS"
    )

    print(
        "TranslationInput             : PASS"
    )

    print(
        "GraphTranslator              : PASS"
    )

    print(
        "Canonical CONTENT type       : PASS"
    )

    print(
        "Discovery MODIFIED           : PASS"
    )

    print(
        "Extraction                   : PASS"
    )

    print(
        "Canonical hash unchanged     : PASS"
    )

    print(
        "Load skipped                 : PASS"
    )

    print(
        "Knowledge Object unchanged   : PASS"
    )

    print(
        "No Sync History created      : PASS"
    )

    print(
        "Processing Job completion    : PASS"
    )

    print()

    print(
        "LIVE ONENOTE SAME-HASH "
        "ORCHESTRATOR TEST PASSED."
    )

    print()


if __name__ == "__main__":
    main()