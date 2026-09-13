"""
OneNote Section Timestamp Translation Test

Purpose:
    Validates that GraphTranslator uses the parent OneNote Section
    modification timestamp as the canonical source_modified_at value for a
    OneNote page.

Verifies:
    - A controlled ConnectorSection can be translated.
    - TranslationInput provides correlation identity.
    - GraphTranslator produces a page TranslatorRecord.
    - The page source_modified_at matches the parent Section modification
      timestamp.

Does NOT:
    - Make live synchronization decisions.
    - Perform Discovery.
    - Perform Extraction or Load.
    - Write to AlphaOmega.
"""

from scripts.connectors.connector_section import (
    ConnectorSection,
)

from scripts.sync.sync_translation_input import (
    TranslationInput,
)

from scripts.translator.graph_translator import (
    GraphTranslator,
)


# ============================================================================
# Controlled Test Values
# ============================================================================

PAGE_ID = (
    "alphaomega-onenote-section-timestamp-test"
)

SECTION_ID = (
    "alphaomega-onenote-section-test"
)

PAGE_TITLE = (
    "Blacksmith Lingo"
)

PAGE_MODIFIED_AT = (
    "2018-09-29T16:00:20.845Z"
)

SECTION_MODIFIED_AT = (
    "2026-08-23T20:47:38Z"
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
        "OneNote Section Timestamp Translation Test"
    )

    print(
        "============================================================"
    )

    print()

    # ------------------------------------------------------------------------
    # Build ConnectorSection exactly at the real Connector boundary.
    # ------------------------------------------------------------------------

    connector_section = (
        ConnectorSection(
            "onenote"
        )
    )

    connector_section.raw_objects = [
        {
            "source_object_type":
                "page",

            "raw_object": {
                "id":
                    PAGE_ID,

                "title":
                    PAGE_TITLE,

                "createdDateTime":
                    PAGE_MODIFIED_AT,

                "lastModifiedDateTime":
                    PAGE_MODIFIED_AT,

                "parentSection": {
                    "id":
                        SECTION_ID,
                },
            },

            "connector_metadata": {
                "source_parent_object_id":
                    SECTION_ID,

                "source_path":
                    "Mimic's Tavern/Lingo",

                "object_path":
                    "Mimic's Tavern/Lingo/Blacksmith Lingo",

                "hierarchy_verified":
                    True,

                "page_level":
                    0,

                "page_order":
                    1,

                "source_section_modified_at":
                    SECTION_MODIFIED_AT,
            },
        }
    ]

    connector_section.raw_metadata = {
        "enumeration_complete":
            True,

        "retrieval_strategy":
            "isolated-test",

        "objects_retrieved":
            1,
    }

    connector_section.connection_succeeded = (
        True
    )

    connector_section.lock()

    print(
        "PASS: Synthetic ConnectorSection created."
    )

    # ------------------------------------------------------------------------
    # Use the REAL orchestration correlation boundary.
    # ------------------------------------------------------------------------

    translation_input = (
        TranslationInput(
            connector_section
        )
    )

    print(
        "PASS: TranslationInput created."
    )

    if (
        len(
            translation_input.raw_objects
        )
        != 1
    ):
        raise RuntimeError(
            "TranslationInput did not contain exactly one object."
        )

    correlated_object = (
        translation_input.raw_objects[0]
    )

    correlation_id = (
        correlated_object.get(
            "correlation_id"
        )
    )

    if not correlation_id:
        raise RuntimeError(
            "TranslationInput did not assign correlation identity."
        )

    print(
        "PASS: Correlation identity assigned."
    )

    # ------------------------------------------------------------------------
    # Run REAL GraphTranslator.
    # ------------------------------------------------------------------------

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
            "GraphTranslator did not report successful translation."
        )

    if (
        len(
            translator_section.record_errors
        )
        != 0
    ):
        raise RuntimeError(
            "GraphTranslator produced unexpected record errors: "
            f"{translator_section.record_errors}"
        )

    if (
        len(
            translator_section.translated_records
        )
        != 1
    ):
        raise RuntimeError(
            "Expected exactly one TranslatorRecord."
        )

    record = (
        translator_section
        .translated_records[0]
    )

    print(
        "PASS: GraphTranslator produced exactly one record."
    )

    # ------------------------------------------------------------------------
    # Identity validation.
    # ------------------------------------------------------------------------

    if (
        record.correlation_id
        != correlation_id
    ):
        raise RuntimeError(
            "Correlation identity was not preserved."
        )

    print(
        "PASS: Correlation identity preserved."
    )

    if (
        record.source_name
        != "OneNote"
    ):
        raise RuntimeError(
            "Incorrect canonical Source name."
        )

    if (
        record.source_object_id
        != PAGE_ID
    ):
        raise RuntimeError(
            "Incorrect OneNote Page identity."
        )

    if (
        record.source_parent_object_id
        != SECTION_ID
    ):
        raise RuntimeError(
            "Incorrect OneNote parent Section identity."
        )

    print(
        "PASS: OneNote Page and Section identity preserved."
    )

    # ------------------------------------------------------------------------
    # Critical timestamp test.
    # ------------------------------------------------------------------------

    print()

    print(
        f"Page lastModifiedDateTime    : "
        f"{PAGE_MODIFIED_AT}"
    )

    print(
        f"Section lastModifiedDateTime : "
        f"{SECTION_MODIFIED_AT}"
    )

    print(
        f"Translated source_modified_at: "
        f"{record.source_modified_at}"
    )

    if (
        record.source_modified_at
        != SECTION_MODIFIED_AT
    ):
        raise RuntimeError(
            "OneNote TranslatorRecord.source_modified_at "
            "did not use the parent Section timestamp.\n"
            f"Expected: {SECTION_MODIFIED_AT!r}\n"
            f"Actual:   {record.source_modified_at!r}"
        )

    print()

    print(
        "PASS: OneNote source_modified_at uses "
        "parent Section lastModifiedDateTime."
    )

    if (
        record.source_modified_at
        == PAGE_MODIFIED_AT
    ):
        raise RuntimeError(
            "OneNote Page timestamp was incorrectly used "
            "as the canonical modification signal."
        )

    print(
        "PASS: Stale Page timestamp was not used."
    )

    # ------------------------------------------------------------------------
    # Connector metadata preservation.
    # ------------------------------------------------------------------------

    hierarchy_metadata = (
        record.metadata.get(
            "connector_hierarchy"
        )
    )

    if (
        hierarchy_metadata is None
    ):
        raise RuntimeError(
            "Connector hierarchy metadata was not preserved."
        )

    if (
        hierarchy_metadata.get(
            "source_section_modified_at"
        )
        != SECTION_MODIFIED_AT
    ):
        raise RuntimeError(
            "Section modification timestamp was not "
            "preserved in Translator metadata."
        )

    print(
        "PASS: Section timestamp preserved in metadata."
    )

    # ------------------------------------------------------------------------
    # Section locking.
    # ------------------------------------------------------------------------

    if (
        translator_section.is_locked
        is not True
    ):
        raise RuntimeError(
            "TranslatorSection was not locked."
        )

    print(
        "PASS: TranslatorSection locked."
    )

    # ------------------------------------------------------------------------
    # Final.
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
        "Connector page metadata           : PASS"
    )

    print(
        "TranslationInput correlation       : PASS"
    )

    print(
        "Real GraphTranslator               : PASS"
    )

    print(
        "Parent Section identity            : PASS"
    )

    print(
        "Section timestamp -> source_modified_at : PASS"
    )

    print(
        "Stale Page timestamp ignored       : PASS"
    )

    print()

    print(
        "ONENOTE SECTION TIMESTAMP "
        "TRANSLATION TEST PASSED."
    )

    print()


if __name__ == "__main__":
    main()