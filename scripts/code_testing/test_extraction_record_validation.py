"""
Extraction Record Validation Test

Purpose:
    Validates required-field and value validation performed by
    ExtractionRecord.

Verifies:
    - Valid ExtractionRecord data passes validation.
    - Missing or invalid required Extraction fields are rejected.
    - Canonical content and extraction metadata must satisfy the record
      contract before downstream processing.

Does NOT:
    - Retrieve source content.
    - Execute ExtractionService.
    - Perform Load.
    - Persist Knowledge Objects.
"""

from scripts.extraction.extraction_record import (
    ExtractionRecord,
)


VALID_HASH = (
    "0123456789abcdef"
    "0123456789abcdef"
    "0123456789abcdef"
    "0123456789abcdef"
)


def build_valid_record():
    """
    Build a minimally valid ExtractionRecord.
    """

    record = ExtractionRecord()

    record.canonical_content = (
        "AlphaOmega canonical content."
    )

    record.content_hash = VALID_HASH

    return record


def test_valid_record():
    """
    Verify a valid ExtractionRecord passes validation.
    """

    record = build_valid_record()

    assert record.validate() is True

    print(
        "PASS: Valid ExtractionRecord accepted."
    )


def test_missing_canonical_content():
    """
    Verify missing canonical content is rejected.
    """

    record = build_valid_record()

    record.canonical_content = None

    try:
        record.validate()

        raise AssertionError(
            "Missing canonical_content was accepted."
        )

    except ValueError as error:
        assert (
            "canonical_content"
            in str(error)
        )

    print(
        "PASS: Missing canonical_content rejected."
    )


def test_empty_canonical_content():
    """
    Verify empty canonical content is rejected.
    """

    record = build_valid_record()

    record.canonical_content = "   "

    try:
        record.validate()

        raise AssertionError(
            "Empty canonical_content was accepted."
        )

    except ValueError as error:
        assert (
            "cannot be empty"
            in str(error)
        )

    print(
        "PASS: Empty canonical_content rejected."
    )


def test_missing_content_hash():
    """
    Verify missing content hash is rejected.
    """

    record = build_valid_record()

    record.content_hash = None

    try:
        record.validate()

        raise AssertionError(
            "Missing content_hash was accepted."
        )

    except ValueError as error:
        assert (
            "content_hash"
            in str(error)
        )

    print(
        "PASS: Missing content_hash rejected."
    )


def test_wrong_hash_length():
    """
    Verify an invalid SHA-256 length is rejected.
    """

    record = build_valid_record()

    record.content_hash = "abc123"

    try:
        record.validate()

        raise AssertionError(
            "Incorrect hash length was accepted."
        )

    except ValueError as error:
        assert (
            "64-character"
            in str(error)
        )

    print(
        "PASS: Incorrect SHA-256 length rejected."
    )


def test_non_hexadecimal_hash():
    """
    Verify a 64-character non-hexadecimal hash is rejected.
    """

    record = build_valid_record()

    record.content_hash = "z" * 64

    try:
        record.validate()

        raise AssertionError(
            "Non-hexadecimal hash was accepted."
        )

    except ValueError as error:
        assert (
            "hexadecimal"
            in str(error)
        )

    print(
        "PASS: Non-hexadecimal SHA-256 rejected."
    )


def main():
    """
    Run ExtractionRecord validation tests.
    """

    print(
        "\nRunning ExtractionRecord validation tests...\n"
    )

    test_valid_record()
    test_missing_canonical_content()
    test_empty_canonical_content()
    test_missing_content_hash()
    test_wrong_hash_length()
    test_non_hexadecimal_hash()

    print(
        "\nExtractionRecord validation tests PASSED.\n"
    )


if __name__ == "__main__":
    main()