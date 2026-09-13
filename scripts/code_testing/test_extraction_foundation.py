"""
Extraction Foundation Test

Purpose:
    Validates the foundational Extraction record and section contracts.

Verifies:
    - ExtractionRecord stores canonical extracted content and metadata.
    - ExtractionRecord validates required Extraction data.
    - ExtractionSection stores Extraction records and record-level errors.
    - ExtractionSection follows the shared synchronization section contract.
    - Completed Extraction output can be locked against modification.

Does NOT:
    - Retrieve live source content.
    - Execute the complete ExtractionService.
    - Perform Load.
    - Persist Knowledge Objects.
"""

from scripts.extraction.content_hasher import ContentHasher
from scripts.extraction.extraction_record import ExtractionRecord
from scripts.extraction.extraction_section import ExtractionSection
from scripts.extraction.text_extractor import TextExtractor
from scripts.sync.sync_exceptions import SectionLockedError


def test_extraction_record():
    """
    Verify ExtractionRecord fields initialize correctly.
    """

    record = ExtractionRecord()

    assert record.canonical_content is None
    assert record.content_hash is None
    assert record.canonical_metadata == {}
    assert record.extractor_name is None
    assert record.extraction_timestamp is None

    print("PASS: ExtractionRecord initialized correctly.")


def test_extraction_section():
    """
    Verify ExtractionSection initializes and locks correctly.
    """

    section = ExtractionSection()

    assert section.extraction_records == []
    assert section.record_errors == []
    assert section.extraction_succeeded is False
    assert section.is_locked is False

    section.extraction_succeeded = True
    section.lock()

    assert section.is_locked is True
    assert section.extraction_records == ()
    assert section.record_errors == ()

    try:
        section.extraction_succeeded = False

        raise AssertionError(
            "Locked ExtractionSection allowed modification."
        )

    except SectionLockedError:
        pass

    print("PASS: ExtractionSection locking enforced.")


def test_content_hasher():
    """
    Verify SHA-256 hashing is deterministic.
    """

    content = "AlphaOmega canonical content"

    first_hash = ContentHasher.generate(content)
    second_hash = ContentHasher.generate(content)

    assert first_hash == second_hash

    assert len(first_hash) == 64

    assert first_hash != ContentHasher.generate(
        "Different canonical content"
    )

    print("PASS: ContentHasher is deterministic.")


def test_text_extractor_support():
    """
    Verify supported and unsupported extension detection.
    """

    assert TextExtractor.supports("notes.txt")
    assert TextExtractor.supports("notes.md")
    assert TextExtractor.supports("data.csv")
    assert TextExtractor.supports("data.json")
    assert TextExtractor.supports("data.xml")
    assert TextExtractor.supports("document.docx")
    assert TextExtractor.supports("document.pdf")
    assert TextExtractor.supports("workbook.xlsx")
    assert TextExtractor.supports("page.html")
    assert TextExtractor.supports("page.htm")

    assert not TextExtractor.supports("picture.jpg")
    assert not TextExtractor.supports("archive.zip")

    print("PASS: TextExtractor support routing correct.")


def test_plain_text_extraction():
    """
    Verify plain UTF-8 text extraction.
    """

    content = "AlphaOmega\nExtraction Test"

    result = TextExtractor.extract(
        "test.txt",
        content.encode("utf-8"),
    )

    assert result == content

    print("PASS: Plain text extraction correct.")


def test_unsupported_format():
    """
    Verify unsupported formats fail explicitly.
    """

    try:
        TextExtractor.extract(
            "picture.jpg",
            b"fake image bytes",
        )

        raise AssertionError(
            "Unsupported format did not raise ValueError."
        )

    except ValueError:
        pass

    print("PASS: Unsupported format rejected explicitly.")


def main():
    """
    Run Extraction foundation tests.
    """

    print("\nRunning Extraction foundation tests...\n")

    test_extraction_record()
    test_extraction_section()
    test_content_hasher()
    test_text_extractor_support()
    test_plain_text_extraction()
    test_unsupported_format()

    print("\nExtraction foundation tests PASSED.\n")


if __name__ == "__main__":
    main()