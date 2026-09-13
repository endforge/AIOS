"""
Live Discovery UNCHANGED Test

Purpose:
    Validates the Discovery UNCHANGED path against live persisted AlphaOmega
    data.

Verifies:
    - A live translated source object can be compared with its existing
      Knowledge Object.
    - Discovery classifies matching source and persisted facts as UNCHANGED.
    - Existing Knowledge Object identity is preserved.
    - UNCHANGED records do not require Extraction.

Does NOT:
    - Perform Extraction.
    - Perform Load.
    - Modify Knowledge Objects.
    - Modify source data.
"""

from types import SimpleNamespace
from uuid import uuid4

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


# ============================================================================
# Live Test Targets
# ============================================================================


ONEDRIVE_FILE_NAME = (
    "Bogmire Introduction Draft v1.docx"
)

ONEDRIVE_OBJECT_ID = (
    "70EE5AA1D6A4DA1F!sac3f611bf898418d8a31206c7780357c"
)

ONEDRIVE_SOURCE_PATH = (
    "Mimics Tavern/D&D/Created Adventures/"
    "Bogmire Adventures/Drafts/"
    "Bogmire Introduction Draft v1.docx"
)


ONENOTE_PAGE_NAME = (
    "Blacksmith Lingo"
)

ONENOTE_PAGE_ID = (
    "0-c95a5657f28b44aca521bda1767279d9!"
    "1-70EE5AA1D6A4DA1F!80852"
)

ONENOTE_SOURCE_PATH = (
    "Mimic's Tavern/Lingo/Blacksmith Lingo"
)


# ============================================================================
# Database Infrastructure
# ============================================================================


def build_database_infrastructure():
    """
    Establish authenticated AlphaOmega database access and build
    the real Discovery service.
    """

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

    return (
        source_repository,
        knowledge_object_repository,
        discovery_service,
    )


# ============================================================================
# Existing Knowledge Object Validation
# ============================================================================


def get_existing_knowledge_object(
    *,
    source_repository,
    knowledge_object_repository,
    source_name,
    source_object_id,
    expected_title,
):
    """
    Retrieve and validate the existing controlled Knowledge Object.

    The UNCHANGED test requires the target to already exist.
    """

    source_id = (
        source_repository.find_id_by_name(
            source_name
        )
    )

    if source_id is None:
        raise RuntimeError(
            f"Source '{source_name}' is not registered "
            "in AlphaOmega."
        )

    knowledge_object = (
        knowledge_object_repository
        .find_by_source_identity(
            source_id=source_id,
            source_object_id=(
                source_object_id
            ),
        )
    )

    if knowledge_object is None:
        raise RuntimeError(
            f"Target '{expected_title}' does not exist "
            "in knowledge_objects. "
            "The targeted NEW Load test must succeed first."
        )

    if (
        knowledge_object["title"]
        != expected_title
    ):
        raise RuntimeError(
            f"Existing Knowledge Object title mismatch for "
            f"'{expected_title}'. "
            f"Stored title: "
            f"'{knowledge_object['title']}'."
        )

    if (
        knowledge_object["content_hash"]
        is None
    ):
        raise RuntimeError(
            f"Existing Knowledge Object for "
            f"'{expected_title}' has no content hash."
        )

    print(
        f"PASS: Existing Knowledge Object located for "
        f"'{expected_title}'."
    )

    print(
        f"  Knowledge Object ID : "
        f"{knowledge_object['id']}"
    )

    print(
        f"  Content hash        : "
        f"{knowledge_object['content_hash']}"
    )

    print(
        f"  Parent object ID    : "
        f"{knowledge_object['source_parent_object_id']}"
    )

    print(
        f"  Source modified at  : "
        f"{knowledge_object['source_modified_at']}"
    )

    return knowledge_object


# ============================================================================
# Controlled Translator Record
# ============================================================================


def build_translator_record(
    *,
    correlation_id,
    source_name,
    source_object_id,
    source_path,
    name,
    object_type,
    knowledge_object,
):
    """
    Build the trusted Translator record used as Discovery input.

    The comparison fields are taken directly from the existing
    Knowledge Object so this test isolates and validates Discovery's
    UNCHANGED decision path.

    Discovery comparison fields:
        name
        source_parent_object_id
        source_modified_at
    """

    return SimpleNamespace(
        correlation_id=(
            correlation_id
        ),

        source_name=(
            source_name
        ),

        source_object_id=(
            source_object_id
        ),

        source_parent_object_id=(
            knowledge_object[
                "source_parent_object_id"
            ]
        ),

        source_path=(
            source_path
        ),

        source_url=None,

        name=(
            name
        ),

        object_type=(
            object_type
        ),

        source_created_at=None,

        source_modified_at=(
            knowledge_object[
                "source_modified_at"
            ]
        ),

        metadata={
            "live_discovery_unchanged_test":
                True,
        },
    )


# ============================================================================
# Translator Section Test Input
# ============================================================================


def build_translator_section(
    translator_records,
):
    """
    Build the minimum trusted TranslatorSection interface required
    by DiscoveryService.

    DiscoveryService requires:
        translated_records

    The object is intentionally simple because Translator itself is
    not under test.
    """

    return SimpleNamespace(
        translated_records=(
            translator_records
        ),
    )


# ============================================================================
# Discovery Result Validation
# ============================================================================


def validate_unchanged_record(
    *,
    label,
    translator_record,
    discovery_record,
    knowledge_object,
):
    """
    Validate the complete Discovery UNCHANGED contract for one record.
    """

    if (
        discovery_record.correlation_id
        != translator_record.correlation_id
    ):
        raise RuntimeError(
            f"{label}: Correlation identity was not preserved."
        )

    print(
        f"PASS: {label} correlation identity preserved."
    )

    if (
        discovery_record.sync_state
        != SyncState.UNCHANGED
    ):
        raise RuntimeError(
            f"{label}: Expected UNCHANGED but received "
            f"{discovery_record.sync_state}."
        )

    print(
        f"PASS: {label} classified UNCHANGED."
    )

    if (
        discovery_record.requires_extraction
        is not False
    ):
        raise RuntimeError(
            f"{label}: UNCHANGED record incorrectly requires "
            "Extraction."
        )

    print(
        f"PASS: {label} requires_extraction = False."
    )

    if (
        discovery_record.knowledge_object_id
        != knowledge_object["id"]
    ):
        raise RuntimeError(
            f"{label}: Existing Knowledge Object identity "
            "was not preserved."
        )

    print(
        f"PASS: {label} existing Knowledge Object identity "
        "preserved."
    )

    if (
        discovery_record.previous_content_hash
        != knowledge_object["content_hash"]
    ):
        raise RuntimeError(
            f"{label}: Previous content hash was not preserved."
        )

    print(
        f"PASS: {label} previous content hash preserved."
    )

    if (
        discovery_record.comparison_reason
        is not None
    ):
        raise RuntimeError(
            f"{label}: UNCHANGED record unexpectedly contains "
            f"a comparison reason: "
            f"{discovery_record.comparison_reason}"
        )

    print(
        f"PASS: {label} comparison_reason = None."
    )


# ============================================================================
# Main
# ============================================================================


def main():
    """
    Run the targeted real-database Discovery UNCHANGED test.
    """

    print()
    print(
        "============================================================"
    )

    print(
        "AlphaOmega Targeted Discovery UNCHANGED Test"
    )

    print(
        "============================================================"
    )

    print()
    print(
        "READ-ONLY TEST"
    )

    print(
        "No Extraction will execute."
    )

    print(
        "No Load will execute."
    )

    print(
        "No database writes will occur."
    )

    print()

    (
        source_repository,
        knowledge_object_repository,
        discovery_service,
    ) = build_database_infrastructure()

    print(
        "PASS: Authenticated AlphaOmega database access established."
    )

    print()

    # ------------------------------------------------------------------------
    # Verify existing OneDrive Knowledge Object
    # ------------------------------------------------------------------------

    onedrive_knowledge_object = (
        get_existing_knowledge_object(
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
    )

    # ------------------------------------------------------------------------
    # Verify existing OneNote Knowledge Object
    # ------------------------------------------------------------------------

    onenote_knowledge_object = (
        get_existing_knowledge_object(
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
    )

    print()

    # ------------------------------------------------------------------------
    # Build controlled trusted Translator records
    # ------------------------------------------------------------------------

    onedrive_correlation_id = str(
        uuid4()
    )

    onenote_correlation_id = str(
        uuid4()
    )

    onedrive_translator_record = (
        build_translator_record(
            correlation_id=(
                onedrive_correlation_id
            ),
            source_name="OneDrive",
            source_object_id=(
                ONEDRIVE_OBJECT_ID
            ),
            source_path=(
                ONEDRIVE_SOURCE_PATH
            ),
            name=(
                ONEDRIVE_FILE_NAME
            ),
            object_type="CONTENT",
            knowledge_object=(
                onedrive_knowledge_object
            ),
        )
    )

    onenote_translator_record = (
        build_translator_record(
            correlation_id=(
                onenote_correlation_id
            ),
            source_name="OneNote",
            source_object_id=(
                ONENOTE_PAGE_ID
            ),
            source_path=(
                ONENOTE_SOURCE_PATH
            ),
            name=(
                ONENOTE_PAGE_NAME
            ),
            object_type="page",
            knowledge_object=(
                onenote_knowledge_object
            ),
        )
    )

    translator_section = (
        build_translator_section(
            [
                onedrive_translator_record,
                onenote_translator_record,
            ]
        )
    )

    # ------------------------------------------------------------------------
    # Execute real Discovery
    # ------------------------------------------------------------------------

    print(
        "Executing real Discovery..."
    )

    print()

    discovery_section = (
        discovery_service.run(
            translator_section
        )
    )

    # ------------------------------------------------------------------------
    # Validate section-level result
    # ------------------------------------------------------------------------

    if (
        discovery_section.discovery_succeeded
        is not True
    ):
        raise RuntimeError(
            "Discovery stage did not complete successfully."
        )

    print(
        "PASS: Discovery completed successfully."
    )

    if (
        len(
            discovery_section.record_errors
        )
        != 0
    ):
        print()
        print(
            "Discovery produced record-level errors:"
        )

        for error in (
            discovery_section.record_errors
        ):
            print(
                dict(error)
            )

        raise RuntimeError(
            "Discovery produced record-level errors."
        )

    print(
        "PASS: Discovery produced zero record-level errors."
    )

    if (
        len(
            discovery_section.discovery_records
        )
        != 2
    ):
        raise RuntimeError(
            "Discovery did not produce exactly two records."
        )

    print(
        "PASS: Discovery produced exactly two records."
    )

    if not discovery_section.is_locked:
        raise RuntimeError(
            "DiscoverySection was not locked."
        )

    print(
        "PASS: DiscoverySection is locked."
    )

    print()

    # ------------------------------------------------------------------------
    # Results are produced in Translator input order.
    # ------------------------------------------------------------------------

    onedrive_discovery_record = (
        discovery_section
        .discovery_records[0]
    )

    onenote_discovery_record = (
        discovery_section
        .discovery_records[1]
    )

    # ------------------------------------------------------------------------
    # Validate OneDrive
    # ------------------------------------------------------------------------

    print(
        "Validating OneDrive..."
    )

    validate_unchanged_record(
        label="OneDrive",
        translator_record=(
            onedrive_translator_record
        ),
        discovery_record=(
            onedrive_discovery_record
        ),
        knowledge_object=(
            onedrive_knowledge_object
        ),
    )

    print()

    # ------------------------------------------------------------------------
    # Validate OneNote
    # ------------------------------------------------------------------------

    print(
        "Validating OneNote..."
    )

    validate_unchanged_record(
        label="OneNote",
        translator_record=(
            onenote_translator_record
        ),
        discovery_record=(
            onenote_discovery_record
        ),
        knowledge_object=(
            onenote_knowledge_object
        ),
    )

    # ------------------------------------------------------------------------
    # Final Result
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

    print(
        f"OneDrive: {ONEDRIVE_FILE_NAME} : UNCHANGED : PASS"
    )

    print(
        f"OneNote : {ONENOTE_PAGE_NAME} : UNCHANGED : PASS"
    )

    print()

    print(
        "Extraction invoked : NO"
    )

    print(
        "Load invoked       : NO"
    )

    print(
        "Database writes    : NO"
    )

    print()

    print(
        "Targeted Discovery UNCHANGED test PASSED."
    )

    print()


if __name__ == "__main__":
    main()