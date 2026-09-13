"""
Microsoft Graph Discovery Pipeline Sample Test

Purpose:
    Validates a small deterministic live AlphaOmega pipeline from Microsoft
    Graph through Connector, Translator, and Discovery.

Verifies:
    - Sample Microsoft Graph source retrieval completes successfully.
    - Connector output completes and locks correctly.
    - Translator accounts for Connector objects and locks its output.
    - Discovery operates against real Translator output.
    - Source identity resolves through SourceRepository.
    - Knowledge Object comparison executes through
      KnowledgeObjectRepository.
    - Successfully translated records receive a Discovery result or a
      record-level Discovery error.
    - Discovery produces only NEW, MODIFIED, or UNCHANGED states.
    - NEW and MODIFIED records require Extraction.
    - UNCHANGED records do not require Extraction.
    - Existing Knowledge Object identity and previous content hash are
      preserved.
    - Discovery output completes and locks correctly.

Does NOT:
    - Perform Extraction.
    - Perform Load.
    - Insert, update, or delete Knowledge Objects.
    - Modify Microsoft Graph source data.
"""

from collections import Counter
from pprint import pprint


# ============================================================================
# AlphaOmega Imports
# ============================================================================

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
# Sample Configuration
# ============================================================================

ONEDRIVE_TEST_FOLDER = "Writings"

GAMES_NOTEBOOK = "Games"
GAMES_SECTION = "Minecraft"

MIMICS_TAVERN_NOTEBOOK = "Mimic's Tavern"
MIMICS_TAVERN_SECTION = "Homebrew"


# ============================================================================
# Shared Helpers
# ============================================================================

def build_connector_section(
    source_name,
    connector_objects,
):
    """
    Build and lock a ConnectorSection using known sample objects.
    """

    section = ConnectorSection(
        source_name
    )

    section.connection_succeeded = True

    section.raw_objects = (
        connector_objects
    )

    section.raw_metadata = {
        "enumeration_complete":
            True,

        "test_mode":
            True,

        "objects_retrieved":
            len(connector_objects),
    }

    section.lock()

    return section


def expected_name(
    source_object_type,
    raw_object,
):
    """
    Determine expected canonical name.
    """

    if source_object_type == "page":

        title = raw_object.get(
            "title"
        )

        if (
            title is None
            or not str(title).strip()
        ):

            return "Untitled"

        return str(title).strip()

    name = (
        raw_object.get(
            "displayName"
        )
        or raw_object.get(
            "name"
        )
    )

    if name is None:
        return None

    return str(name).strip()


def find_exact_object(
    objects,
    field_name,
    field_value,
    description,
):
    """
    Find exactly one source object using a known field value.
    """

    matches = [
        item
        for item in objects
        if item.get(
            field_name
        ) == field_value
    ]

    if len(matches) != 1:

        raise RuntimeError(
            f"Expected exactly one {description} "
            f"named '{field_value}'. "
            f"Found {len(matches)}."
        )

    return matches[0]


# ============================================================================
# OneDrive Sample Retrieval
# ============================================================================

def get_onedrive_sample(
    connector,
):
    """
    Retrieve Writings and recursively retrieve every descendant.
    """

    root_children = (
        connector._get_collection(
            "/me/drive/root/children"
        )
    )

    writings_matches = [
        item
        for item in root_children
        if (
            item.get("name")
            == ONEDRIVE_TEST_FOLDER
            and "folder"
            in item
        )
    ]

    if len(writings_matches) != 1:

        raise RuntimeError(
            "Expected exactly one OneDrive "
            "Writings folder."
        )

    raw_objects = []

    def crawl(
        item,
    ):
        """
        Recursively retrieve every descendant beneath Writings.
        """

        raw_objects.append(
            connector._wrap_object(
                "driveItem",
                item,
            )
        )

        if "folder" not in item:
            return

        item_id = item.get(
            "id"
        )

        if not item_id:

            raise RuntimeError(
                "OneDrive folder is missing "
                "its object ID."
            )

        children = (
            connector._get_collection(
                "/me/drive/items/"
                f"{item_id}/children"
            )
        )

        for child in children:

            crawl(
                child
            )

    crawl(
        writings_matches[0]
    )

    return build_connector_section(
        "onedrive",
        raw_objects,
    )


# ============================================================================
# OneNote Sample Retrieval
# ============================================================================

def get_onenote_notebook(
    connector,
    notebook_name,
):
    """
    Retrieve one exact OneNote notebook including sections and
    section groups.
    """

    notebooks = (
        connector._get_collection(
            "/me/onenote/notebooks"
            "?$expand=sections,"
            "sectionGroups($expand=sections)"
        )
    )

    return find_exact_object(
        notebooks,
        "displayName",
        notebook_name,
        "OneNote notebook",
    )


def add_notebook(
    connector,
    notebook,
    raw_objects,
    sections,
    section_ids,
    section_group_ids,
    only_section_name=None,
):
    """
    Add a notebook and selected section hierarchy using the
    production Connector hierarchy functions.
    """

    notebook_id = (
        notebook.get(
            "id"
        )
    )

    notebook_name = (
        notebook.get(
            "displayName"
        )
    )

    if not notebook_id:

        raise RuntimeError(
            f"Notebook '{notebook_name}' "
            "is missing its ID."
        )

    raw_objects.append(
        connector._wrap_object(
            "notebook",
            notebook,
            connector_metadata={
                "source_parent_object_id":
                    None,

                "source_path":
                    None,

                "object_path":
                    notebook_name,

                "hierarchy_verified":
                    True,
            },
        )
    )

    notebook_sections = (
        notebook.get(
            "sections",
            [],
        )
    )

    if only_section_name is not None:

        notebook_sections = [
            section
            for section
            in notebook_sections
            if section.get(
                "displayName"
            ) == only_section_name
        ]

        if len(notebook_sections) != 1:

            raise RuntimeError(
                f"Expected exactly one section "
                f"'{only_section_name}' in notebook "
                f"'{notebook_name}'. "
                f"Found {len(notebook_sections)}."
            )

    for section in notebook_sections:

        connector._add_onenote_section(
            section=section,
            raw_objects=raw_objects,
            sections=sections,
            section_ids=section_ids,
            parent_object_id=(
                notebook_id
            ),
            parent_path=(
                notebook_name
            ),
        )

    if only_section_name is None:

        for section_group in notebook.get(
            "sectionGroups",
            [],
        ):

            connector._add_onenote_section_group(
                section_group=(
                    section_group
                ),
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
                section_group_ids=(
                    section_group_ids
                ),
                parent_object_id=(
                    notebook_id
                ),
                parent_path=(
                    notebook_name
                ),
            )


def get_onenote_sample(
    connector,
):
    """
    Retrieve the known OneNote regression datasets.
    """

    raw_objects = []

    sections = []

    section_ids = set()
    section_group_ids = set()

    # ------------------------------------------------------------------------
    # Games -> Minecraft
    # ------------------------------------------------------------------------

    games_notebook = (
        get_onenote_notebook(
            connector,
            GAMES_NOTEBOOK,
        )
    )

    add_notebook(
        connector=connector,
        notebook=games_notebook,
        raw_objects=raw_objects,
        sections=sections,
        section_ids=section_ids,
        section_group_ids=(
            section_group_ids
        ),
        only_section_name=(
            GAMES_SECTION
        ),
    )

    # ------------------------------------------------------------------------
    # Mimic's Tavern -> Homebrew
    # ------------------------------------------------------------------------

    mimics_notebook = (
        get_onenote_notebook(
            connector,
            MIMICS_TAVERN_NOTEBOOK,
        )
    )

    add_notebook(
        connector=connector,
        notebook=mimics_notebook,
        raw_objects=raw_objects,
        sections=sections,
        section_ids=section_ids,
        section_group_ids=(
            section_group_ids
        ),
        only_section_name=(
            MIMICS_TAVERN_SECTION
        ),
    )

    # ------------------------------------------------------------------------
    # Retrieve pages through production hierarchy logic.
    # ------------------------------------------------------------------------

    for section_context in sections:

        connector._enumerate_onenote_section_pages(
            section_context=(
                section_context
            ),
            raw_objects=(
                raw_objects
            ),
        )

    return build_connector_section(
        "onenote",
        raw_objects,
    )


# ============================================================================
# Translator Validation
# ============================================================================

def validate_translator(
    connector_section,
    translator_section,
):
    """
    Verify record accounting across Connector -> Translator.
    """

    failures = []

    connector_count = len(
        connector_section.raw_objects
    )

    translated_count = len(
        translator_section.translated_records
    )

    translator_error_count = len(
        translator_section.record_errors
    )

    accounted_for = (
        translated_count
        + translator_error_count
    )

    if accounted_for != connector_count:

        failures.append(
            {
                "stage":
                    "Translator",

                "field":
                    "record_accounting",

                "expected":
                    connector_count,

                "actual":
                    accounted_for,
            }
        )

    if (
        translator_section.translation_succeeded
        is not True
    ):

        failures.append(
            {
                "stage":
                    "Translator",

                "field":
                    "translation_succeeded",

                "expected":
                    True,

                "actual":
                    translator_section.translation_succeeded,
            }
        )

    return failures


# ============================================================================
# Discovery Validation
# ============================================================================

def validate_discovery(
    translator_section,
    discovery_section,
):
    """
    Validate Discovery's output contract against Translator input.
    """

    failures = []

    translated_records = list(
        translator_section.translated_records
    )

    discovery_records = list(
        discovery_section.discovery_records
    )

    discovery_errors = list(
        discovery_section.record_errors
    )

    # ------------------------------------------------------------------------
    # Stage completion
    # ------------------------------------------------------------------------

    if (
        discovery_section.discovery_succeeded
        is not True
    ):

        failures.append(
            {
                "stage":
                    "Discovery",

                "field":
                    "discovery_succeeded",

                "expected":
                    True,

                "actual":
                    discovery_section.discovery_succeeded,
            }
        )

    # ------------------------------------------------------------------------
    # Record accounting
    # ------------------------------------------------------------------------

    accounted_for = (
        len(discovery_records)
        + len(discovery_errors)
    )

    if accounted_for != len(
        translated_records
    ):

        failures.append(
            {
                "stage":
                    "Discovery",

                "field":
                    "record_accounting",

                "expected":
                    len(
                        translated_records
                    ),

                "actual":
                    accounted_for,
            }
        )

    # ------------------------------------------------------------------------
    # Validate every successful Discovery record
    # ------------------------------------------------------------------------

    valid_states = {
        SyncState.NEW,
        SyncState.MODIFIED,
        SyncState.UNCHANGED,
    }

    for index, discovery_record in enumerate(
        discovery_records
    ):

        sync_state = (
            discovery_record.sync_state
        )

        # --------------------------------------------------------------------
        # Supported synchronization state
        # --------------------------------------------------------------------

        if sync_state not in valid_states:

            failures.append(
                {
                    "stage":
                        "Discovery",

                    "record_index":
                        index,

                    "field":
                        "sync_state",

                    "expected":
                        "NEW, MODIFIED, or UNCHANGED",

                    "actual":
                        sync_state,
                }
            )

            continue

        # --------------------------------------------------------------------
        # NEW
        # --------------------------------------------------------------------

        if sync_state == SyncState.NEW:

            if (
                discovery_record.requires_extraction
                is not True
            ):

                failures.append(
                    {
                        "stage":
                            "Discovery",

                        "record_index":
                            index,

                        "field":
                            "requires_extraction",

                        "sync_state":
                            "NEW",

                        "expected":
                            True,

                        "actual":
                            discovery_record.requires_extraction,
                    }
                )

            if (
                discovery_record.knowledge_object_id
                is not None
            ):

                failures.append(
                    {
                        "stage":
                            "Discovery",

                        "record_index":
                            index,

                        "field":
                            "knowledge_object_id",

                        "sync_state":
                            "NEW",

                        "expected":
                            None,

                        "actual":
                            discovery_record.knowledge_object_id,
                    }
                )

            if (
                discovery_record.previous_content_hash
                is not None
            ):

                failures.append(
                    {
                        "stage":
                            "Discovery",

                        "record_index":
                            index,

                        "field":
                            "previous_content_hash",

                        "sync_state":
                            "NEW",

                        "expected":
                            None,

                        "actual":
                            discovery_record.previous_content_hash,
                    }
                )

        # --------------------------------------------------------------------
        # MODIFIED
        # --------------------------------------------------------------------

        elif sync_state == SyncState.MODIFIED:

            if (
                discovery_record.requires_extraction
                is not True
            ):

                failures.append(
                    {
                        "stage":
                            "Discovery",

                        "record_index":
                            index,

                        "field":
                            "requires_extraction",

                        "sync_state":
                            "MODIFIED",

                        "expected":
                            True,

                        "actual":
                            discovery_record.requires_extraction,
                    }
                )

            if (
                discovery_record.knowledge_object_id
                is None
            ):

                failures.append(
                    {
                        "stage":
                            "Discovery",

                        "record_index":
                            index,

                        "field":
                            "knowledge_object_id",

                        "sync_state":
                            "MODIFIED",

                        "expected":
                            "existing Knowledge Object ID",

                        "actual":
                            None,
                    }
                )

            if not (
                discovery_record.comparison_reason
            ):

                failures.append(
                    {
                        "stage":
                            "Discovery",

                        "record_index":
                            index,

                        "field":
                            "comparison_reason",

                        "sync_state":
                            "MODIFIED",

                        "expected":
                            "at least one comparison reason",

                        "actual":
                            discovery_record.comparison_reason,
                    }
                )

        # --------------------------------------------------------------------
        # UNCHANGED
        # --------------------------------------------------------------------

        elif sync_state == SyncState.UNCHANGED:

            if (
                discovery_record.requires_extraction
                is not False
            ):

                failures.append(
                    {
                        "stage":
                            "Discovery",

                        "record_index":
                            index,

                        "field":
                            "requires_extraction",

                        "sync_state":
                            "UNCHANGED",

                        "expected":
                            False,

                        "actual":
                            discovery_record.requires_extraction,
                    }
                )

            if (
                discovery_record.knowledge_object_id
                is None
            ):

                failures.append(
                    {
                        "stage":
                            "Discovery",

                        "record_index":
                            index,

                        "field":
                            "knowledge_object_id",

                        "sync_state":
                            "UNCHANGED",

                        "expected":
                            "existing Knowledge Object ID",

                        "actual":
                            None,
                    }
                )

            if (
                discovery_record.comparison_reason
                is not None
            ):

                failures.append(
                    {
                        "stage":
                            "Discovery",

                        "record_index":
                            index,

                        "field":
                            "comparison_reason",

                        "sync_state":
                            "UNCHANGED",

                        "expected":
                            None,

                        "actual":
                            discovery_record.comparison_reason,
                    }
                )

    return failures


# ============================================================================
# Reporting
# ============================================================================

def print_failures(
    label,
    failures,
):
    """
    Print validation failures.
    """

    if not failures:
        return

    print()
    print("=" * 80)
    print(
        f"{label} VALIDATION FAILURES"
    )
    print("=" * 80)

    for failure in failures:

        print("-" * 80)

        pprint(
            failure,
            sort_dicts=False,
        )


def print_discovery_summary(
    label,
    connector_section,
    translator_section,
    discovery_section,
):
    """
    Print concise end-to-end pipeline summary.
    """

    discovery_records = list(
        discovery_section.discovery_records
    )

    discovery_states = Counter(
        record.sync_state
        for record
        in discovery_records
    )

    requires_extraction = sum(
        1
        for record
        in discovery_records
        if record.requires_extraction
        is True
    )

    print()
    print("=" * 80)
    print(
        f"{label} PIPELINE SUMMARY"
    )
    print("=" * 80)

    print(
        f"Connector objects       : "
        f"{len(connector_section.raw_objects)}"
    )

    print(
        f"Translated records      : "
        f"{len(translator_section.translated_records)}"
    )

    print(
        f"Translator errors       : "
        f"{len(translator_section.record_errors)}"
    )

    print(
        f"Discovery records       : "
        f"{len(discovery_section.discovery_records)}"
    )

    print(
        f"Discovery errors        : "
        f"{len(discovery_section.record_errors)}"
    )

    print(
        f"Discovery states        : "
        f"{dict(discovery_states)}"
    )

    print(
        f"Requires Extraction     : "
        f"{requires_extraction}"
    )


# ============================================================================
# Pipeline Runner
# ============================================================================

def run_pipeline(
    label,
    connector_section,
    discovery_service,
):
    """
    Execute Translator -> Discovery for a prepared Connector section.
    """

    print()
    print("=" * 80)
    print(
        f"RUNNING {label}"
    )
    print("=" * 80)

    # ------------------------------------------------------------------------
    # Translator
    # ------------------------------------------------------------------------

    print()
    print("Running Translator...")

    translator = GraphTranslator()

    translator_section = translator.run(
        connector_section
    )

    print(
        "Translator completed successfully."
    )

    # ------------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------------

    print()
    print("Running Discovery...")

    discovery_section = (
        discovery_service.run(
            translator_section
        )
    )

    print(
        "Discovery completed successfully."
    )

    # ------------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------------

    failures = []

    failures.extend(
        validate_translator(
            connector_section,
            translator_section,
        )
    )

    failures.extend(
        validate_discovery(
            translator_section,
            discovery_section,
        )
    )

    print_discovery_summary(
        label,
        connector_section,
        translator_section,
        discovery_section,
    )

    print_failures(
        label,
        failures,
    )

    if failures:

        print()
        print(
            f"{label}: FAIL"
        )

        return False

    print()
    print(
        f"{label}: PASS"
    )

    return True


# ============================================================================
# Main
# ============================================================================

def main():

    print()
    print("=" * 80)
    print(
        "ALPHAOMEGA CONNECTOR -> TRANSLATOR -> DISCOVERY "
        "SAMPLE END-TO-END TEST"
    )
    print("=" * 80)

    # ========================================================================
    # Database Authentication
    # ========================================================================

    print()
    print(
        "Establishing authenticated AlphaOmega database connection..."
    )

    credential_provider = (
        LocalCredentialProvider()
    )

    database_connection = (
        DatabaseConnection(
            credential_provider=(
                credential_provider
            )
        )
    )

    client = (
        database_connection.connect()
    )

    print(
        "Authenticated database connection established."
    )

    # ========================================================================
    # Repositories
    # ========================================================================

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

    # ========================================================================
    # Discovery Service
    # ========================================================================

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

    # ========================================================================
    # Microsoft Graph Connector
    # ========================================================================

    connector = (
        GraphConnector()
    )

    onedrive_pass = False
    onenote_pass = False

    # ========================================================================
    # OneDrive
    # ========================================================================

    try:

        print()
        print(
            "Retrieving OneDrive Writings sample..."
        )

        onedrive_section = (
            get_onedrive_sample(
                connector
            )
        )

        onedrive_pass = (
            run_pipeline(
                label=(
                    "ONEDRIVE WRITINGS"
                ),
                connector_section=(
                    onedrive_section
                ),
                discovery_service=(
                    discovery_service
                ),
            )
        )

    except Exception as error:

        print()
        print("=" * 80)
        print(
            "ONEDRIVE WRITINGS: FAIL"
        )
        print("=" * 80)

        print(
            f"{error.__class__.__name__}: "
            f"{error}"
        )

    # ========================================================================
    # OneNote
    # ========================================================================

    try:

        print()
        print(
            "Retrieving OneNote regression sample..."
        )

        onenote_section = (
            get_onenote_sample(
                connector
            )
        )

        onenote_pass = (
            run_pipeline(
                label=(
                    "ONENOTE REGRESSION SAMPLE"
                ),
                connector_section=(
                    onenote_section
                ),
                discovery_service=(
                    discovery_service
                ),
            )
        )

    except Exception as error:

        print()
        print("=" * 80)
        print(
            "ONENOTE REGRESSION SAMPLE: FAIL"
        )
        print("=" * 80)

        print(
            f"{error.__class__.__name__}: "
            f"{error}"
        )

    # ========================================================================
    # Final Result
    # ========================================================================

    print()
    print("=" * 80)
    print(
        "FINAL RESULT"
    )
    print("=" * 80)

    print(
        f"OneDrive Writings : "
        f"{'PASS' if onedrive_pass else 'FAIL'}"
    )

    print(
        f"OneNote Regression: "
        f"{'PASS' if onenote_pass else 'FAIL'}"
    )

    print()

    if (
        onedrive_pass
        and onenote_pass
    ):

        print(
            "CONNECTOR -> TRANSLATOR -> DISCOVERY "
            "END-TO-END SAMPLE TEST: PASS"
        )

    else:

        print(
            "CONNECTOR -> TRANSLATOR -> DISCOVERY "
            "END-TO-END SAMPLE TEST: FAIL"
        )

    print()


if __name__ == "__main__":

    main()