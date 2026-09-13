"""
Full OneNote Connector and Translator Integration Test

Purpose:
    Validates the complete Microsoft Graph OneNote Connector to Translator
    integration against the entire OneNote Source of Truth.

Verifies:
    - Connector processing completes successfully.
    - Connector enumeration is complete.
    - Translator processing completes successfully.
    - Every Connector object is accounted for.
    - Notebooks become CONTAINER.
    - Section groups become CONTAINER.
    - Sections become CONTAINER.
    - Pages become CONTENT.
    - Names match Microsoft Graph.
    - Blank OneNote page titles become Untitled.
    - Source object IDs match Microsoft Graph.
    - Connector-proven parent relationships survive Translation.
    - Connector-proven source paths survive Translation.
    - Created and modified timestamps match Microsoft Graph.
    - Connector hierarchy remains marked as verified.
    - Translator record errors are reported.

Does NOT:
    - Perform Discovery.
    - Perform Extraction or Load.
    - Persist Knowledge Objects.
    - Modify OneNote source data.
"""

from collections import Counter

from scripts.connectors.ms_graph.graph_connector import GraphConnector
from scripts.translator.graph_translator import GraphTranslator
from collections.abc import Mapping


SOURCE = "onenote"

MAX_FAILURES_TO_PRINT = 100


# ============================================================================
# Validation Helpers
# ============================================================================

def expected_name(
    source_object_type,
    raw_object,
):
    """
    Determine the expected AlphaOmega canonical name.
    """

    if source_object_type == "page":

        title = raw_object.get("title")

        if (
            title is None
            or not str(title).strip()
        ):

            return "Untitled"

        return str(title).strip()

    name = (
        raw_object.get("displayName")
        or raw_object.get("name")
    )

    if name is None:
        return None

    return str(name).strip()


def expected_object_type(
    source_object_type,
):
    """
    Determine expected AlphaOmega canonical type.
    """

    if source_object_type in (
        "notebook",
        "sectionGroup",
        "section",
    ):

        return "CONTAINER"

    if source_object_type == "page":

        return "CONTENT"

    return None


def add_failure(
    failures,
    object_name,
    object_id,
    field,
    expected,
    actual,
):
    """
    Record one validation failure.
    """

    failures.append(
        {
            "object_name": object_name,
            "object_id": object_id,
            "field": field,
            "expected": expected,
            "actual": actual,
        }
    )


# ============================================================================
# Full Validation
# ============================================================================

def validate(
    connector_section,
    translator_section,
):
    """
    Validate the complete OneNote Connector -> Translator result.
    """

    failures = []

    connector_objects = list(
        connector_section.raw_objects
    )

    translated_records = list(
        translator_section.translated_records
    )

    record_errors = list(
        translator_section.record_errors
    )

    # ------------------------------------------------------------------------
    # Stage validation
    # ------------------------------------------------------------------------

    if connector_section.connection_succeeded is not True:

        add_failure(
            failures,
            "Connector",
            None,
            "connection_succeeded",
            True,
            connector_section.connection_succeeded,
        )

    if (
        connector_section.raw_metadata.get(
            "enumeration_complete"
        )
        is not True
    ):

        add_failure(
            failures,
            "Connector",
            None,
            "enumeration_complete",
            True,
            connector_section.raw_metadata.get(
                "enumeration_complete"
            ),
        )

    if translator_section.translation_succeeded is not True:

        add_failure(
            failures,
            "Translator",
            None,
            "translation_succeeded",
            True,
            translator_section.translation_succeeded,
        )

    # ------------------------------------------------------------------------
    # Record accounting
    # ------------------------------------------------------------------------

    accounted_for = (
        len(translated_records)
        + len(record_errors)
    )

    if accounted_for != len(connector_objects):

        add_failure(
            failures,
            "Pipeline",
            None,
            "record_accounting",
            len(connector_objects),
            accounted_for,
        )

    # ------------------------------------------------------------------------
    # Build translated lookup
    # ------------------------------------------------------------------------

    translated_by_id = {}

    for record in translated_records:

        if record.source_object_id in translated_by_id:

            add_failure(
                failures,
                record.name,
                record.source_object_id,
                "duplicate_source_object_id",
                "unique",
                "duplicate",
            )

        translated_by_id[
            record.source_object_id
        ] = record

    # ------------------------------------------------------------------------
    # Validate every Connector object
    # ------------------------------------------------------------------------

    supported_types = {
        "notebook",
        "sectionGroup",
        "section",
        "page",
    }

    for connector_object in connector_objects:

        source_object_type = (
            connector_object.get(
                "source_object_type"
            )
        )

        raw_object = (
            connector_object.get(
                "raw_object"
            )
        )

        connector_metadata = (
            connector_object.get(
                "connector_metadata",
                {}
            )
        )

        if source_object_type not in supported_types:

            add_failure(
                failures,
                str(raw_object),
                None,
                "source_object_type",
                sorted(supported_types),
                source_object_type,
            )

            continue

        if not isinstance(raw_object, Mapping):

            add_failure(
                failures,
                "Unknown",
                None,
                "raw_object",
                "Mapping",
                type(raw_object).__name__,
            )

            continue

        object_id = raw_object.get("id")

        object_name = expected_name(
            source_object_type,
            raw_object,
        )

        record = translated_by_id.get(
            object_id
        )

        if record is None:

            add_failure(
                failures,
                object_name,
                object_id,
                "translated_record",
                "present",
                "missing",
            )

            continue

        # --------------------------------------------------------------------
        # Canonical field comparisons
        # --------------------------------------------------------------------

        comparisons = {
            "source_name": (
                SOURCE,
                record.source_name,
            ),

            "source_object_id": (
                object_id,
                record.source_object_id,
            ),

            "name": (
                object_name,
                record.name,
            ),

            "object_type": (
                expected_object_type(
                    source_object_type
                ),
                record.object_type,
            ),

            "source_created_at": (
                raw_object.get(
                    "createdDateTime"
                ),
                record.source_created_at,
            ),

            "source_modified_at": (
                raw_object.get(
                    "lastModifiedDateTime"
                ),
                record.source_modified_at,
            ),
        }

        # --------------------------------------------------------------------
        # Connector-proven hierarchy
        # --------------------------------------------------------------------

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

        # --------------------------------------------------------------------
        # Compare values
        # --------------------------------------------------------------------

        for field, values in comparisons.items():

            expected = values[0]
            actual = values[1]

            if expected != actual:

                add_failure(
                    failures,
                    object_name,
                    object_id,
                    field,
                    expected,
                    actual,
                )

        # --------------------------------------------------------------------
        # Hierarchy verification
        # --------------------------------------------------------------------

        if (
            "hierarchy_verified"
            in connector_metadata
            and connector_metadata.get(
                "hierarchy_verified"
            )
            is not True
        ):

            add_failure(
                failures,
                object_name,
                object_id,
                "hierarchy_verified",
                True,
                connector_metadata.get(
                    "hierarchy_verified"
                ),
            )

        # --------------------------------------------------------------------
        # Page-specific validation
        # --------------------------------------------------------------------

        if source_object_type == "page":

            raw_title = raw_object.get(
                "title"
            )

            if (
                raw_title is None
                or not str(raw_title).strip()
            ):

                if record.name != "Untitled":

                    add_failure(
                        failures,
                        object_name,
                        object_id,
                        "untitled_page_normalization",
                        "Untitled",
                        record.name,
                    )

            page_level = (
                connector_metadata.get(
                    "page_level"
                )
            )

            if page_level is None:

                add_failure(
                    failures,
                    object_name,
                    object_id,
                    "page_level",
                    "Microsoft Graph level value",
                    None,
                )

            # A nested page must have a proven parent page.
            #
            # The Connector already performs the actual hierarchy
            # reconstruction. Here we verify that Translator preserved it.
            if (
                isinstance(page_level, int)
                and page_level > 0
                and not record.source_parent_object_id
            ):

                add_failure(
                    failures,
                    object_name,
                    object_id,
                    "nested_page_parent",
                    "parent page object ID",
                    record.source_parent_object_id,
                )

    return failures


# ============================================================================
# Reporting
# ============================================================================

def print_failure(
    failure,
):
    """
    Print one validation failure.
    """

    print("-" * 80)

    print(
        f"Object Name : "
        f"{failure.get('object_name')}"
    )

    print(
        f"Object ID   : "
        f"{failure.get('object_id')}"
    )

    print(
        f"Field       : "
        f"{failure.get('field')}"
    )

    print(
        f"Expected    : "
        f"{failure.get('expected')}"
    )

    print(
        f"Actual      : "
        f"{failure.get('actual')}"
    )


# ============================================================================
# Main
# ============================================================================

def main():

    print()
    print("=" * 80)
    print(
        "FULL ONENOTE CONNECTOR -> TRANSLATOR TEST"
    )
    print("=" * 80)

    # ------------------------------------------------------------------------
    # Connector
    # ------------------------------------------------------------------------

    print()
    print("Running full OneNote Connector...")

    connector = GraphConnector()

    connector_section = connector.run(
        SOURCE
    )

    print(
        "Connector completed successfully."
    )

    connector_objects = list(
        connector_section.raw_objects
    )

    connector_types = Counter(
        connector_object.get(
            "source_object_type"
        )
        for connector_object
        in connector_objects
    )

    print()
    print(
        f"Connector objects      : "
        f"{len(connector_objects)}"
    )

    print(
        f"Connector object types : "
        f"{dict(connector_types)}"
    )

    print(
        f"Enumeration complete   : "
        f"{connector_section.raw_metadata.get('enumeration_complete')}"
    )

    print(
        f"Retrieval strategy     : "
        f"{connector_section.raw_metadata.get('retrieval_strategy')}"
    )

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

    translated_records = list(
        translator_section.translated_records
    )

    record_errors = list(
        translator_section.record_errors
    )

    canonical_types = Counter(
        record.object_type
        for record
        in translated_records
    )

    untitled_pages = sum(
        1
        for record
        in translated_records
        if (
            record.object_type == "CONTENT"
            and record.name == "Untitled"
        )
    )

    # ------------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------------

    print()
    print("Validating full pipeline...")

    failures = validate(
        connector_section,
        translator_section,
    )

    # ------------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------------

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(
        f"Connector objects      : "
        f"{len(connector_objects)}"
    )

    print(
        f"Translated records     : "
        f"{len(translated_records)}"
    )

    print(
        f"Record errors          : "
        f"{len(record_errors)}"
    )

    print(
        f"Canonical object types : "
        f"{dict(canonical_types)}"
    )

    print(
        f"Untitled pages         : "
        f"{untitled_pages}"
    )

    print(
        f"Validation failures    : "
        f"{len(failures)}"
    )

    # ------------------------------------------------------------------------
    # Record errors
    # ------------------------------------------------------------------------

    if record_errors:

        print()
        print("=" * 80)
        print("TRANSLATOR RECORD ERRORS")
        print("=" * 80)

        for error in record_errors[
            :MAX_FAILURES_TO_PRINT
        ]:

            print("-" * 80)
            print(error)

        if (
            len(record_errors)
            > MAX_FAILURES_TO_PRINT
        ):

            print()
            print(
                f"... {len(record_errors) - MAX_FAILURES_TO_PRINT} "
                "additional record errors not displayed."
            )

    # ------------------------------------------------------------------------
    # Validation failures
    # ------------------------------------------------------------------------

    if failures:

        print()
        print("=" * 80)
        print("VALIDATION FAILURES")
        print("=" * 80)

        for failure in failures[
            :MAX_FAILURES_TO_PRINT
        ]:

            print_failure(
                failure
            )

        if (
            len(failures)
            > MAX_FAILURES_TO_PRINT
        ):

            print()
            print(
                f"... {len(failures) - MAX_FAILURES_TO_PRINT} "
                "additional failures not displayed."
            )

    # ------------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------------

    print()
    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)

    if failures:

        print(
            "FULL ONENOTE CONNECTOR -> TRANSLATOR: FAIL"
        )

    else:

        print(
            "FULL ONENOTE CONNECTOR -> TRANSLATOR: PASS"
        )

    print()


if __name__ == "__main__":
    main()