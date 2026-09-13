"""
Live UNCHANGED Integration Test

Purpose:
    Validates the targeted live AlphaOmega UNCHANGED path for known OneDrive
    and OneNote content whose persisted source facts match the current Sources
    of Truth.

Verifies:
    - Live OneDrive and OneNote targets can be retrieved and translated.
    - Discovery classifies matching persisted source facts as UNCHANGED.
    - Correlation identity is preserved.
    - Existing Knowledge Object identities are preserved.
    - Previous content hashes are preserved.
    - UNCHANGED records do not require Extraction.
    - No comparison reasons are produced for unchanged records.

Does NOT:
    - Perform Extraction.
    - Perform Load.
    - Create a Processing Job.
    - Write to the AlphaOmega database.
"""

from scripts.sync.sync_state import (
    SyncState,
)

from scripts.code_testing.test_live_modified import (
    ONEDRIVE_FILE_NAME,
    ONEDRIVE_OBJECT_ID,
    ONENOTE_PAGE_NAME,
    ONENOTE_PAGE_ID,
    build_database_infrastructure,
    get_existing_knowledge_object,
    get_onedrive_target,
    get_onenote_target,
    translate_target,
)

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)


def validate_unchanged(
    *,
    discovery_service,
    translator_section,
    translator_record,
    existing_knowledge_object,
    expected_name,
):
    """
    Execute Discovery and verify the complete UNCHANGED contract
    for one live source object.
    """

    discovery_section = (
        discovery_service.run(
            translator_section
        )
    )

    if (
        discovery_section.discovery_succeeded
        is not True
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
            f"Discovery produced record-level errors for "
            f"'{expected_name}': "
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

    if not discovery_section.is_locked:
        raise RuntimeError(
            f"DiscoverySection was not locked for "
            f"'{expected_name}'."
        )

    discovery_record = (
        discovery_section
        .discovery_records[0]
    )

    # ------------------------------------------------------------------
    # Correlation identity
    # ------------------------------------------------------------------

    if (
        discovery_record.correlation_id
        != translator_record.correlation_id
    ):
        raise RuntimeError(
            f"Correlation identity was not preserved for "
            f"'{expected_name}'."
        )

    # ------------------------------------------------------------------
    # UNCHANGED classification
    # ------------------------------------------------------------------

    if (
        discovery_record.sync_state
        != SyncState.UNCHANGED
    ):
        raise RuntimeError(
            f"Expected UNCHANGED for '{expected_name}' "
            f"but received "
            f"{discovery_record.sync_state}."
        )

    # ------------------------------------------------------------------
    # Extraction short-circuit
    # ------------------------------------------------------------------

    if (
        discovery_record.requires_extraction
        is not False
    ):
        raise RuntimeError(
            f"UNCHANGED record '{expected_name}' incorrectly "
            "requires Extraction."
        )

    # ------------------------------------------------------------------
    # Existing Knowledge Object identity
    # ------------------------------------------------------------------

    if (
        discovery_record.knowledge_object_id
        != existing_knowledge_object["id"]
    ):
        raise RuntimeError(
            f"Existing Knowledge Object identity was not "
            f"preserved for '{expected_name}'."
        )

    # ------------------------------------------------------------------
    # Previous content hash
    # ------------------------------------------------------------------

    if (
        discovery_record.previous_content_hash
        != existing_knowledge_object["content_hash"]
    ):
        raise RuntimeError(
            f"Previous content hash was not preserved for "
            f"'{expected_name}'."
        )

    # ------------------------------------------------------------------
    # Comparison reason
    # ------------------------------------------------------------------

    if (
        discovery_record.comparison_reason
        is not None
    ):
        raise RuntimeError(
            f"UNCHANGED record '{expected_name}' unexpectedly "
            f"contains comparison reason: "
            f"{discovery_record.comparison_reason}"
        )

    print(
        f"PASS: Discovery classified "
        f"'{expected_name}' as UNCHANGED."
    )

    print(
        "  requires_extraction : False"
    )

    print(
        f"  Knowledge Object ID : "
        f"{discovery_record.knowledge_object_id}"
    )

    print(
        f"  Previous hash       : "
        f"{discovery_record.previous_content_hash}"
    )

    print(
        "  Comparison reason   : None"
    )

    return discovery_record


def main():
    """
    Execute the targeted live UNCHANGED integration test.
    """

    print()
    print(
        "============================================================"
    )

    print(
        "AlphaOmega Targeted Live UNCHANGED Integration Test"
    )

    print(
        "============================================================"
    )

    print()
    print(
        "READ-ONLY TEST"
    )

    print(
        "Live Microsoft Graph retrieval : YES"
    )

    print(
        "Real TranslationInput           : YES"
    )

    print(
        "Real GraphTranslator            : YES"
    )

    print(
        "Real Discovery                  : YES"
    )

    print(
        "Extraction                      : NO"
    )

    print(
        "Load                            : NO"
    )

    print(
        "Processing Job                  : NO"
    )

    print(
        "Database writes                 : NO"
    )

    print()

    (
        _client,
        source_repository,
        knowledge_object_repository,
        discovery_service,
        _load_service,
    ) = build_database_infrastructure()

    print(
        "PASS: Authenticated AlphaOmega "
        "database access established."
    )

    # ------------------------------------------------------------------
    # Existing persisted state
    # ------------------------------------------------------------------

    (
        _onedrive_source_id,
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
        _onenote_source_id,
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

    # ------------------------------------------------------------------
    # Exact current Sources of Truth
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Real TranslationInput -> GraphTranslator
    # ------------------------------------------------------------------

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

    print()

    # ------------------------------------------------------------------
    # Real Discovery -> UNCHANGED
    # ------------------------------------------------------------------

    onedrive_discovery_record = (
        validate_unchanged(
            discovery_service=(
                discovery_service
            ),
            translator_section=(
                onedrive_translator_section
            ),
            translator_record=(
                onedrive_translator_record
            ),
            existing_knowledge_object=(
                onedrive_existing
            ),
            expected_name=(
                ONEDRIVE_FILE_NAME
            ),
        )
    )

    print()

    onenote_discovery_record = (
        validate_unchanged(
            discovery_service=(
                discovery_service
            ),
            translator_section=(
                onenote_translator_section
            ),
            translator_record=(
                onenote_translator_record
            ),
            existing_knowledge_object=(
                onenote_existing
            ),
            expected_name=(
                ONENOTE_PAGE_NAME
            ),
        )
    )

    # ------------------------------------------------------------------
    # Final cross-object assertions
    # ------------------------------------------------------------------

    if (
        onedrive_discovery_record.requires_extraction
        or onenote_discovery_record.requires_extraction
    ):
        raise RuntimeError(
            "At least one UNCHANGED object incorrectly "
            "requires Extraction."
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
        f"OneDrive: {ONEDRIVE_FILE_NAME}"
    )

    print(
        "  Live Discovery : UNCHANGED : PASS"
    )

    print()

    print(
        f"OneNote : {ONENOTE_PAGE_NAME}"
    )

    print(
        "  Live Discovery : UNCHANGED : PASS"
    )

    print()

    print(
        "Correlation preserved    : PASS"
    )

    print(
        "Existing KO IDs preserved: PASS"
    )

    print(
        "Previous hashes preserved: PASS"
    )

    print(
        "requires_extraction=False: PASS"
    )

    print(
        "Comparison reasons absent : PASS"
    )

    print()

    print(
        "Extraction invoked        : NO"
    )

    print(
        "Load invoked              : NO"
    )

    print(
        "Processing Job created    : NO"
    )

    print(
        "Database writes           : NO"
    )

    print()

    print(
        "Targeted live UNCHANGED integration "
        "test PASSED."
    )

    print()


if __name__ == "__main__":
    main()