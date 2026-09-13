"""
Live Microsoft Graph Extraction Test

Purpose:
    Validates Extraction against live content retrieved from Microsoft Graph.

Verifies:
    - Live source content can be retrieved for controlled test objects.
    - ExtractionService can process the retrieved source content.
    - Canonical extracted content is produced from the live source object.
    - Extraction produces the metadata required for downstream Load.

Does NOT:
    - Perform Load.
    - Persist Knowledge Objects.
    - Modify Microsoft Graph source data.
    - Execute the complete synchronization pipeline.
"""

from types import SimpleNamespace

from scripts.extraction.extraction_service import (
    ExtractionService,
)


# ============================================================================
# Live Test Targets
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
# Test Input
# ============================================================================

def build_extraction_input(
    source_name,
    source_object_id,
    object_type,
    name,
):
    """
    Build the minimal orchestration-supplied input required
    by ExtractionService.
    """

    return SimpleNamespace(
        source_name=source_name,
        source_object_id=source_object_id,
        object_type=object_type,
        name=name,
    )


# ============================================================================
# Validation
# ============================================================================

def validate_extraction_section(
    section,
    expected_name,
):
    """
    Validate successful live Extraction output without
    printing canonical source content.
    """

    assert (
        section.extraction_succeeded
        is True
    )

    assert (
        section.is_locked
        is True
    )

    assert (
        len(section.record_errors)
        == 0
    ), (
        f"Extraction produced record errors for "
        f"'{expected_name}': "
        f"{section.record_errors}"
    )

    assert (
        len(section.extraction_records)
        == 1
    )

    record = (
        section.extraction_records[0]
    )

    assert (
        isinstance(
            record.canonical_content,
            str,
        )
    )

    assert (
        len(record.canonical_content)
        > 0
    )

    assert (
        isinstance(
            record.content_hash,
            str,
        )
    )

    assert (
        len(record.content_hash)
        == 64
    )

    assert (
        record.extractor_name
        == "text_extractor"
    )

    assert (
        record.extraction_timestamp
        is not None
    )

    return record


# ============================================================================
# OneDrive
# ============================================================================

def test_live_onedrive_extraction():
    """
    Retrieve and extract the known OneDrive DOCX object.
    """

    print(
        "Testing live OneDrive Extraction..."
    )

    service = ExtractionService()

    extraction_input = (
        build_extraction_input(
            source_name="OneDrive",
            source_object_id=(
                ONEDRIVE_OBJECT_ID
            ),
            object_type="CONTENT",
            name=ONEDRIVE_FILE_NAME,
        )
    )

    section = service.run(
        [extraction_input]
    )

    record = (
        validate_extraction_section(
            section=section,
            expected_name=(
                ONEDRIVE_FILE_NAME
            ),
        )
    )

    print(
        f"  Target: {ONEDRIVE_FILE_NAME}"
    )

    print(
        "  Canonical content length: "
        f"{len(record.canonical_content)}"
    )

    print(
        "  SHA-256 length: "
        f"{len(record.content_hash)}"
    )

    print(
        "PASS: Live OneDrive DOCX "
        "retrieval and Extraction succeeded."
    )


# ============================================================================
# OneNote
# ============================================================================

def test_live_onenote_extraction():
    """
    Retrieve and extract the known OneNote page.
    """

    print(
        "\nTesting live OneNote Extraction..."
    )

    service = ExtractionService()

    extraction_input = (
        build_extraction_input(
            source_name="OneNote",
            source_object_id=(
                ONENOTE_PAGE_ID
            ),
            object_type="page",
            name=ONENOTE_PAGE_NAME,
        )
    )

    section = service.run(
        [extraction_input]
    )

    record = (
        validate_extraction_section(
            section=section,
            expected_name=(
                ONENOTE_PAGE_NAME
            ),
        )
    )

    print(
        f"  Target: {ONENOTE_PAGE_NAME}"
    )

    print(
        "  Canonical content length: "
        f"{len(record.canonical_content)}"
    )

    print(
        "  SHA-256 length: "
        f"{len(record.content_hash)}"
    )

    print(
        "PASS: Live OneNote page "
        "retrieval and Extraction succeeded."
    )


# ============================================================================
# Main
# ============================================================================

def main():
    """
    Run live Microsoft Graph Extraction tests.
    """

    print(
        "\nRunning live Microsoft Graph "
        "Extraction integration tests...\n"
    )

    test_live_onedrive_extraction()

    test_live_onenote_extraction()

    print(
        "\nLive Microsoft Graph Extraction "
        "integration tests PASSED.\n"
    )


if __name__ == "__main__":
    main()