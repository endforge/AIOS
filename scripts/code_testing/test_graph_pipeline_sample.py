"""
Microsoft Graph Connector and Translator Sample Test

Purpose:
    Provides a deterministic Connector to synchronization correlation to
    Translator regression test using small, known Microsoft Graph datasets.

Verifies:
    - Selected OneDrive and OneNote test scopes are retrieved completely.
    - ConnectorSection remains locked.
    - Connector raw objects remain unchanged by synchronization preparation.
    - Every Connector object receives one valid and unique correlation UUID.
    - TranslatorRecord preserves its assigned correlation UUID.
    - Names and canonical object types are translated correctly.
    - Source object and immediate parent identities are preserved.
    - Source hierarchy paths are preserved.
    - Created and modified timestamps are preserved.
    - Blank OneNote page titles become Untitled.
    - Standard and non-contiguous OneNote child-page relationships are
      preserved.
    - Deep OneDrive traversal is preserved.

Does NOT:
    - Enumerate the complete OneDrive or complete OneNote Source of Truth.
    - Perform Discovery.
    - Perform Extraction or Load.
    - Persist Knowledge Objects.
"""

from collections import Counter
from pprint import pprint
from uuid import UUID

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)
from scripts.connectors.connector_section import (
    ConnectorSection,
)
from scripts.sync.sync_translation_input import (
    TranslationInput,
)
from scripts.translator.graph_translator import (
    GraphTranslator,
)


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
    Build a ConnectorSection for deterministic testing.
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

    return (
        raw_object.get(
            "displayName"
        )
        or raw_object.get(
            "name"
        )
    )


def expected_type(
    source_object_type,
    raw_object,
):
    """
    Determine expected canonical object type.
    """

    if source_object_type in (
        "notebook",
        "sectionGroup",
        "section",
        "driveRoot",
    ):

        return "CONTAINER"

    if source_object_type == "page":

        return "CONTENT"

    if source_object_type == "driveItem":

        if "folder" in raw_object:

            return "CONTAINER"

        return "CONTENT"

    return None


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
        Recursively crawl every descendant of Writings.
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
# OneNote Sample Retrieval Helpers
# ============================================================================

def get_onenote_notebook(
    connector,
    notebook_name,
):
    """
    Retrieve one exact OneNote notebook including its sections and
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
    Add a notebook and selected section hierarchy using the same
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
    Retrieve the two known OneNote regression datasets.
    """

    raw_objects = []

    sections = []

    section_ids = set()
    section_group_ids = set()

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
# Correlation Validation
# ============================================================================

def validate_correlation_input(
    connector_section,
    connector_snapshot,
    translation_input,
):
    """
    Validate the Synchronization correlation boundary.
    """

    failures = []

    # ------------------------------------------------------------------------
    # ConnectorSection must remain locked
    # ------------------------------------------------------------------------

    if connector_section.is_locked is not True:

        failures.append(
            {
                "object":
                    connector_section.source_name,

                "field":
                    "connector_section_locked",

                "expected":
                    True,

                "actual":
                    connector_section.is_locked,
            }
        )

    # ------------------------------------------------------------------------
    # Connector raw objects must remain unchanged
    # ------------------------------------------------------------------------

    if (
        list(
            connector_section.raw_objects
        )
        != connector_snapshot
    ):

        failures.append(
            {
                "object":
                    connector_section.source_name,

                "field":
                    "connector_raw_objects_unchanged",

                "expected":
                    "unchanged",

                "actual":
                    "modified",
            }
        )

    # ------------------------------------------------------------------------
    # Record count must remain one-for-one
    # ------------------------------------------------------------------------

    if (
        len(
            translation_input.raw_objects
        )
        != len(
            connector_section.raw_objects
        )
    ):

        failures.append(
            {
                "object":
                    connector_section.source_name,

                "field":
                    "correlation_record_count",

                "expected":
                    len(
                        connector_section.raw_objects
                    ),

                "actual":
                    len(
                        translation_input.raw_objects
                    ),
            }
        )

    correlation_ids = []

    # ------------------------------------------------------------------------
    # Validate every correlated object
    # ------------------------------------------------------------------------

    for index, correlated_object in enumerate(
        translation_input.raw_objects
    ):

        correlation_id = (
            correlated_object.get(
                "correlation_id"
            )
        )

        correlation_ids.append(
            correlation_id
        )

        # --------------------------------------------------------------------
        # UUID must exist and be valid
        # --------------------------------------------------------------------

        try:

            parsed_uuid = UUID(
                str(
                    correlation_id
                )
            )

            if str(
                parsed_uuid
            ) != str(
                correlation_id
            ):

                raise ValueError(
                    "UUID string is not canonical."
                )

        except Exception:

            failures.append(
                {
                    "object":
                        index,

                    "field":
                        "correlation_id",

                    "expected":
                        "valid canonical UUID",

                    "actual":
                        correlation_id,
                }
            )

        # --------------------------------------------------------------------
        # Connector source information must be preserved
        # --------------------------------------------------------------------

        if (
            index
            < len(
                connector_section.raw_objects
            )
        ):

            connector_object = (
                connector_section.raw_objects[
                    index
                ]
            )

            if (
                correlated_object.get(
                    "source_object_type"
                )
                != connector_object.get(
                    "source_object_type"
                )
            ):

                failures.append(
                    {
                        "object":
                            index,

                        "field":
                            "source_object_type_preserved",

                        "expected":
                            connector_object.get(
                                "source_object_type"
                            ),

                        "actual":
                            correlated_object.get(
                                "source_object_type"
                            ),
                    }
                )

            if (
                correlated_object.get(
                    "raw_object"
                )
                != connector_object.get(
                    "raw_object"
                )
            ):

                failures.append(
                    {
                        "object":
                            index,

                        "field":
                            "raw_object_preserved",

                        "expected":
                            "Connector raw_object",

                        "actual":
                            "different raw_object",
                    }
                )

            if (
                correlated_object.get(
                    "connector_metadata",
                    {},
                )
                != connector_object.get(
                    "connector_metadata",
                    {},
                )
            ):

                failures.append(
                    {
                        "object":
                            index,

                        "field":
                            "connector_metadata_preserved",

                        "expected":
                            connector_object.get(
                                "connector_metadata",
                                {},
                            ),

                        "actual":
                            correlated_object.get(
                                "connector_metadata",
                                {},
                            ),
                    }
                )

    # ------------------------------------------------------------------------
    # UUIDs must be unique within this synchronization batch
    # ------------------------------------------------------------------------

    if (
        len(
            correlation_ids
        )
        != len(
            set(
                correlation_ids
            )
        )
    ):

        failures.append(
            {
                "object":
                    connector_section.source_name,

                "field":
                    "correlation_id_uniqueness",

                "expected":
                    len(
                        correlation_ids
                    ),

                "actual":
                    len(
                        set(
                            correlation_ids
                        )
                    ),
            }
        )

    return failures


# ============================================================================
# General Pipeline Validation
# ============================================================================

def validate_pipeline(
    source_name,
    connector_section,
):
    """
    Apply synchronization correlation, translate every Connector object,
    and validate canonical values and correlation identity.
    """

    connector_snapshot = list(
        connector_section.raw_objects
    )

    translation_input = TranslationInput(
        connector_section
    )

    failures = validate_correlation_input(
        connector_section=(
            connector_section
        ),
        connector_snapshot=(
            connector_snapshot
        ),
        translation_input=(
            translation_input
        ),
    )

    translator = GraphTranslator()

    translator_section = (
        translator.run(
            translation_input
        )
    )

    # ------------------------------------------------------------------------
    # Build correlation lookup before source-object lookup.
    # ------------------------------------------------------------------------

    correlation_by_source_id = {}

    for correlated_object in (
        translation_input.raw_objects
    ):

        raw_object = (
            correlated_object[
                "raw_object"
            ]
        )

        object_id = raw_object.get(
            "id"
        )

        correlation_by_source_id[
            object_id
        ] = correlated_object[
            "correlation_id"
        ]

    translated_by_id = {
        record.source_object_id:
            record
        for record
        in translator_section.translated_records
    }

    # ------------------------------------------------------------------------
    # Record accounting
    # ------------------------------------------------------------------------

    if (
        len(
            translator_section.translated_records
        )
        + len(
            translator_section.record_errors
        )
        != len(
            connector_section.raw_objects
        )
    ):

        failures.append(
            {
                "object":
                    source_name,

                "field":
                    "record_accounting",

                "expected":
                    len(
                        connector_section.raw_objects
                    ),

                "actual":
                    (
                        len(
                            translator_section
                            .translated_records
                        )
                        + len(
                            translator_section
                            .record_errors
                        )
                    ),
            }
        )

    # ------------------------------------------------------------------------
    # Validate every object
    # ------------------------------------------------------------------------

    for connector_object in (
        connector_section.raw_objects
    ):

        source_object_type = (
            connector_object[
                "source_object_type"
            ]
        )

        raw_object = (
            connector_object[
                "raw_object"
            ]
        )

        connector_metadata = (
            connector_object.get(
                "connector_metadata",
                {},
            )
        )

        object_id = raw_object.get(
            "id"
        )

        name = expected_name(
            source_object_type,
            raw_object,
        )

        record = (
            translated_by_id.get(
                object_id
            )
        )

        if record is None:

            failures.append(
                {
                    "object":
                        name,

                    "field":
                        "translated_record",

                    "expected":
                        "present",

                    "actual":
                        "missing",
                }
            )

            continue

        expected_correlation_id = (
            correlation_by_source_id.get(
                object_id
            )
        )

        comparisons = {
            "correlation_id":
                (
                    expected_correlation_id,
                    record.correlation_id,
                ),

            "name":
                (
                    name,
                    record.name,
                ),

            "object_type":
                (
                    expected_type(
                        source_object_type,
                        raw_object,
                    ),
                    record.object_type,
                ),

            "source_object_id":
                (
                    object_id,
                    record.source_object_id,
                ),

            "source_created_at":
                (
                    raw_object.get(
                        "createdDateTime"
                    ),
                    record.source_created_at,
                ),

            "source_modified_at":
                (
                    raw_object.get(
                        "lastModifiedDateTime"
                    ),
                    record.source_modified_at,
                ),
        }

        if (
            "source_parent_object_id"
            in connector_metadata
        ):

            comparisons[
                "source_parent_object_id"
            ] = (
                connector_metadata.get(
                    "source_parent_object_id"
                ),
                record.source_parent_object_id,
            )

        elif source_name == "onedrive":

            parent_reference = (
                raw_object.get(
                    "parentReference"
                )
                or {}
            )

            comparisons[
                "source_parent_object_id"
            ] = (
                parent_reference.get(
                    "id"
                ),
                record.source_parent_object_id,
            )

        if (
            "source_path"
            in connector_metadata
        ):

            comparisons[
                "source_path"
            ] = (
                connector_metadata.get(
                    "source_path"
                ),
                record.source_path,
            )

        for (
            field_name,
            values,
        ) in comparisons.items():

            expected_value = (
                values[0]
            )

            actual_value = (
                values[1]
            )

            if (
                expected_value
                != actual_value
            ):

                failures.append(
                    {
                        "object":
                            name,

                        "object_id":
                            object_id,

                        "field":
                            field_name,

                        "expected":
                            expected_value,

                        "actual":
                            actual_value,
                    }
                )

    return (
        translator_section,
        failures,
    )


# ============================================================================
# Known OneNote Regression Validation
# ============================================================================

def get_unique_record(
    translator_section,
    name,
):
    """
    Return exactly one translated record having the requested name.
    """

    matches = [
        record
        for record
        in translator_section.translated_records
        if record.name == name
    ]

    if len(matches) != 1:

        return (
            None,
            {
                "object":
                    name,

                "field":
                    "baseline_lookup",

                "expected":
                    "exactly one translated record",

                "actual":
                    len(matches),
            },
        )

    return (
        matches[0],
        None,
    )


def validate_games_hierarchy(
    translator_section,
):
    """
    Validate the known Games -> Minecraft hierarchy.
    """

    failures = []

    parent_page, error = (
        get_unique_record(
            translator_section,
            "My World Realms - Hoesing and Park",
        )
    )

    if error:

        failures.append(
            error
        )

        return failures

    expected_children = (
        "Blueprints",
        "Storage Build",
        "Coordinates",
        "Super GreenHouse Tower",
    )

    expected_path = (
        "Games/Minecraft/"
        "My World Realms - Hoesing and Park"
    )

    for child_name in expected_children:

        child, error = (
            get_unique_record(
                translator_section,
                child_name,
            )
        )

        if error:

            failures.append(
                error
            )

            continue

        if (
            child.source_parent_object_id
            != parent_page.source_object_id
        ):

            failures.append(
                {
                    "object":
                        child_name,

                    "field":
                        "source_parent_object_id",

                    "expected":
                        parent_page.source_object_id,

                    "actual":
                        child.source_parent_object_id,
                }
            )

        if (
            child.source_path
            != expected_path
        ):

            failures.append(
                {
                    "object":
                        child_name,

                    "field":
                        "source_path",

                    "expected":
                        expected_path,

                    "actual":
                        child.source_path,
                }
            )

    return failures


def validate_non_contiguous_hierarchy(
    translator_section,
):
    """
    Validate the known Mimic's Tavern hierarchy:

        Homebrew
            Selune Armor       level 0
                Armor          level 2
    """

    failures = []

    parent_page, error = (
        get_unique_record(
            translator_section,
            "Selune Armor",
        )
    )

    if error:

        failures.append(
            error
        )

        return failures

    child_page, error = (
        get_unique_record(
            translator_section,
            "Armor",
        )
    )

    if error:

        failures.append(
            error
        )

        return failures

    if (
        child_page.source_parent_object_id
        != parent_page.source_object_id
    ):

        failures.append(
            {
                "object":
                    "Armor",

                "field":
                    "source_parent_object_id",

                "expected":
                    parent_page.source_object_id,

                "actual":
                    child_page.source_parent_object_id,
            }
        )

    expected_path = (
        "Mimic's Tavern/"
        "Homebrew/"
        "Selune Armor"
    )

    if (
        child_page.source_path
        != expected_path
    ):

        failures.append(
            {
                "object":
                    "Armor",

                "field":
                    "source_path",

                "expected":
                    expected_path,

                "actual":
                    child_page.source_path,
            }
        )

    parent_hierarchy = (
        parent_page.metadata.get(
            "connector_hierarchy",
            {},
        )
    )

    child_hierarchy = (
        child_page.metadata.get(
            "connector_hierarchy",
            {},
        )
    )

    parent_level = (
        parent_hierarchy.get(
            "page_level"
        )
    )

    child_level = (
        child_hierarchy.get(
            "page_level"
        )
    )

    if parent_level != 0:

        failures.append(
            {
                "object":
                    "Selune Armor",

                "field":
                    "page_level",

                "expected":
                    0,

                "actual":
                    parent_level,
            }
        )

    if child_level != 2:

        failures.append(
            {
                "object":
                    "Armor",

                "field":
                    "page_level",

                "expected":
                    2,

                "actual":
                    child_level,
            }
        )

    parent_order = (
        parent_hierarchy.get(
            "page_order"
        )
    )

    child_order = (
        child_hierarchy.get(
            "page_order"
        )
    )

    if (
        isinstance(
            parent_order,
            int,
        )
        and isinstance(
            child_order,
            int,
        )
    ):

        if child_order <= parent_order:

            failures.append(
                {
                    "object":
                        "Armor",

                    "field":
                        "page_order",

                    "expected":
                        (
                            "greater than Selune "
                            "Armor page order"
                        ),

                    "actual":
                        child_order,
                }
            )

    else:

        failures.append(
            {
                "object":
                    "Armor",

                "field":
                    "page_order",

                "expected":
                    "integer ordering values",

                "actual":
                    {
                        "Selune Armor":
                            parent_order,

                        "Armor":
                            child_order,
                    },
            }
        )

    return failures


def validate_untitled_pages(
    translator_section,
):
    """
    Verify blank OneNote page title normalization.
    """

    failures = []

    untitled_records = [
        record
        for record
        in translator_section.translated_records
        if record.name == "Untitled"
    ]

    if len(untitled_records) < 1:

        failures.append(
            {
                "object":
                    "Untitled",

                "field":
                    "blank_title_normalization",

                "expected":
                    "at least one Untitled page",

                "actual":
                    len(untitled_records),
            }
        )

    return failures


# ============================================================================
# Reporting
# ============================================================================

def print_inventory(
    label,
    connector_section,
):
    """
    Print concise Connector inventory.
    """

    print()
    print("=" * 78)
    print(
        f"{label} CONNECTOR INVENTORY"
    )
    print("=" * 78)

    counts = Counter()

    for connector_object in (
        connector_section.raw_objects
    ):

        source_object_type = (
            connector_object[
                "source_object_type"
            ]
        )

        raw_object = (
            connector_object[
                "raw_object"
            ]
        )

        counts[
            source_object_type
        ] += 1

        print(
            f"{source_object_type:<12} | "
            f"{str(expected_name(source_object_type, raw_object))}"
        )

    print()

    print(
        f"Total objects: "
        f"{len(connector_section.raw_objects)}"
    )

    print(
        f"Types: {dict(counts)}"
    )


def print_translator_output(
    label,
    translator_section,
):
    """
    Print canonical Translator fields and correlation identity.
    """

    print()
    print("=" * 78)
    print(
        f"{label} TRANSLATOR OUTPUT"
    )
    print("=" * 78)

    for record in (
        translator_section.translated_records
    ):

        pprint(
            {
                "correlation_id":
                    record.correlation_id,

                "name":
                    record.name,

                "object_type":
                    record.object_type,

                "source_name":
                    record.source_name,

                "source_object_id":
                    record.source_object_id,

                "source_parent_object_id":
                    record.source_parent_object_id,

                "source_created_at":
                    record.source_created_at,

                "source_modified_at":
                    record.source_modified_at,

                "source_path":
                    record.source_path,

                "source_url":
                    record.source_url,
            },
            sort_dicts=False,
        )

        print(
            "-" * 78
        )


def print_result(
    label,
    failures,
):
    """
    Print exact validation outcome.
    """

    print()
    print("=" * 78)
    print(
        f"{label} VALIDATION"
    )
    print("=" * 78)

    if not failures:

        print(
            f"{label}: PASS"
        )

        return True

    print(
        f"{label}: FAIL"
    )

    print(
        f"Failures: {len(failures)}"
    )

    for failure in failures:

        print(
            "-" * 78
        )

        pprint(
            failure,
            sort_dicts=False,
        )

    return False


# ============================================================================
# Main
# ============================================================================

def main():

    connector = GraphConnector()

    print()
    print("=" * 78)
    print(
        "Microsoft Graph Connector -> Correlation -> Translator "
        "Deterministic Regression Validation"
    )
    print("=" * 78)

    onedrive_pass = False
    onenote_pass = False

    # ========================================================================
    # OneDrive
    # ========================================================================

    try:

        onedrive_section = (
            get_onedrive_sample(
                connector
            )
        )

        print_inventory(
            "ONEDRIVE WRITINGS",
            onedrive_section,
        )

        (
            onedrive_translator,
            onedrive_failures,
        ) = validate_pipeline(
            "onedrive",
            onedrive_section,
        )

        print_translator_output(
            "ONEDRIVE WRITINGS",
            onedrive_translator,
        )

        onedrive_pass = print_result(
            "ONEDRIVE WRITINGS",
            onedrive_failures,
        )

    except Exception as error:

        print()
        print(
            "ONEDRIVE WRITINGS: FAIL"
        )

        print(
            f"{error.__class__.__name__}: "
            f"{error}"
        )

    # ========================================================================
    # OneNote
    # ========================================================================

    try:

        onenote_section = (
            get_onenote_sample(
                connector
            )
        )

        print_inventory(
            "ONENOTE REGRESSION SAMPLE",
            onenote_section,
        )

        (
            onenote_translator,
            onenote_failures,
        ) = validate_pipeline(
            "onenote",
            onenote_section,
        )

        onenote_failures.extend(
            validate_games_hierarchy(
                onenote_translator
            )
        )

        onenote_failures.extend(
            validate_non_contiguous_hierarchy(
                onenote_translator
            )
        )

        onenote_failures.extend(
            validate_untitled_pages(
                onenote_translator
            )
        )

        print_translator_output(
            "ONENOTE REGRESSION SAMPLE",
            onenote_translator,
        )

        onenote_pass = print_result(
            "ONENOTE REGRESSION SAMPLE",
            onenote_failures,
        )

    except Exception as error:

        print()
        print(
            "ONENOTE REGRESSION SAMPLE: FAIL"
        )

        print(
            f"{error.__class__.__name__}: "
            f"{error}"
        )

    # ========================================================================
    # Final Result
    # ========================================================================

    print()
    print("=" * 78)
    print("FINAL RESULT")
    print("=" * 78)

    print(
        f"OneDrive Writings : "
        f"{'PASS' if onedrive_pass else 'FAIL'}"
    )

    print(
        f"OneNote Regression: "
        f"{'PASS' if onenote_pass else 'FAIL'}"
    )

    if (
        onedrive_pass
        and onenote_pass
    ):

        print()
        print(
            "Connector -> Correlation -> Translator "
            "deterministic regression validation: PASS"
        )

    else:

        print()
        print(
            "Connector -> Correlation -> Translator "
            "deterministic regression validation: FAIL"
        )


if __name__ == "__main__":

    main()