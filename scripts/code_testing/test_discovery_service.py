"""
Discovery Service Integration Test

Purpose:
    Provides comprehensive integration validation of the AlphaOmega
    Discovery stage against the live AlphaOmega repository.

Verifies:
    - NEW objects are classified correctly.
    - Existing unchanged objects are classified UNCHANGED.
    - Changes to name, parent, or source modification timestamp are
      classified MODIFIED.
    - Combined comparison-field changes are classified MODIFIED.
    - Non-comparison fields do not incorrectly cause MODIFIED.
    - Nullable parent and timestamp comparisons behave correctly.
    - Existing Knowledge Object identity is preserved where required.
    - Extraction routing is set correctly from Discovery results.
    - DiscoverySection completes and locks correctly.
    - Correlation identity propagates through Discovery.

Does NOT:
    - Retrieve source content.
    - Perform Extraction or Load.
    - Modify source data.
    - Test Connector or Translator source retrieval behavior.
"""

from datetime import datetime, timezone
from uuid import uuid4

from common.security.local_credential_provider import LocalCredentialProvider

from scripts.database.database_connection import DatabaseConnection
from scripts.database.source_repository import SourceRepository
from scripts.database.knowledge_object_repository import (
    KnowledgeObjectRepository,
)

from scripts.discovery.discovery_service import DiscoveryService

from scripts.translator.translator_record import TranslatorRecord
from scripts.translator.translator_section import TranslatorSection

from scripts.sync.sync_state import SyncState


# ============================================================================
# Existing Synthetic Data baseline
# ============================================================================

EXISTING_SOURCE_OBJECT_ID = "alphaomega-discovery-repository-test"

EXISTING_KNOWLEDGE_OBJECT_ID = (
    "118df4ec-429b-4dba-99e7-7cbba2ef4697"
)

EXISTING_CONTENT_HASH = (
    "alphaomega-test-content-hash-12345"
)

EXISTING_NAME = "AlphaOmega Repository Test Object"

EXISTING_PARENT = "alphaomega-test-parent"

EXISTING_MODIFIED_AT = datetime(
    2026,
    8,
    16,
    13,
    0,
    tzinfo=timezone.utc,
)


# ============================================================================
# Nullable Synthetic Data baseline
# ============================================================================

NULLABLE_SOURCE_OBJECT_ID = (
    "alphaomega-discovery-nullable-test"
)

NULLABLE_KNOWLEDGE_OBJECT_ID = (
    "69b870eb-229c-4909-9eaf-3c8c6ecf12ea"
)

NULLABLE_CONTENT_HASH = (
    "alphaomega-nullable-test-content-hash-12345"
)

NULLABLE_NAME = (
    "AlphaOmega Discovery Nullable Test Object"
)


# ============================================================================
# Test Helpers
# ============================================================================


def build_translator_record(
    source_object_id,
    name,
    source_parent_object_id,
    source_modified_at,
):
    """
    Build a controlled OneNote TranslatorRecord for Discovery testing.

    Each record receives a unique orchestration correlation UUID so
    Discovery correlation propagation can be validated.
    """

    record = TranslatorRecord()

    record.correlation_id = str(
        uuid4()
    )

    record.source_name = "OneNote"
    record.source_object_id = source_object_id
    record.source_parent_object_id = source_parent_object_id
    record.name = name
    record.source_modified_at = source_modified_at

    return record


def validate_existing_object_identity(
    result,
    expected_knowledge_object_id,
    expected_content_hash,
    test_name,
):
    """
    Verify repository identity and previous content hash.
    """

    if (
        result.knowledge_object_id
        != expected_knowledge_object_id
    ):
        raise RuntimeError(
            f"{test_name} did not resolve the expected "
            "knowledge_object_id."
        )

    if (
        result.previous_content_hash
        != expected_content_hash
    ):
        raise RuntimeError(
            f"{test_name} did not preserve the expected "
            "previous content hash."
        )


def validate_correlation_identity(
    translator_records,
    discovery_records,
):
    """
    Verify one-for-one propagation of orchestration correlation identity.

    Discovery must preserve the exact correlation UUID assigned to each
    TranslatorRecord. Discovery must not generate or replace correlation
    identity.
    """

    if (
        len(translator_records)
        != len(discovery_records)
    ):
        raise RuntimeError(
            "Correlation validation cannot proceed because Translator "
            "and Discovery record counts differ. "
            f"Translator: {len(translator_records)}. "
            f"Discovery: {len(discovery_records)}."
        )

    seen_correlation_ids = set()

    for index, (
        translator_record,
        discovery_record,
    ) in enumerate(
        zip(
            translator_records,
            discovery_records,
        )
    ):
        expected_correlation_id = (
            translator_record.correlation_id
        )

        actual_correlation_id = (
            discovery_record.correlation_id
        )

        if actual_correlation_id is None:
            raise RuntimeError(
                "DiscoveryRecord is missing correlation identity. "
                f"Record index: {index}."
            )

        if (
            actual_correlation_id
            != expected_correlation_id
        ):
            raise RuntimeError(
                "Discovery changed correlation identity. "
                f"Record index: {index}. "
                f"Expected: {expected_correlation_id!r}. "
                f"Actual: {actual_correlation_id!r}."
            )

        if (
            actual_correlation_id
            in seen_correlation_ids
        ):
            raise RuntimeError(
                "Duplicate correlation identity detected in "
                "Discovery output. "
                f"Correlation ID: {actual_correlation_id!r}."
            )

        seen_correlation_ids.add(
            actual_correlation_id
        )

    print(
        "Discovery correlation identity propagation PASSED."
    )


# ============================================================================
# Test
# ============================================================================


def main():
    print("Testing Discovery Service...")

    # ------------------------------------------------------------------
    # Database infrastructure
    # ------------------------------------------------------------------

    credential_provider = LocalCredentialProvider()

    database_connection = DatabaseConnection(
        credential_provider
    )

    client = database_connection.connect()

    source_repository = SourceRepository(
        client
    )

    knowledge_object_repository = KnowledgeObjectRepository(
        client
    )

    discovery_service = DiscoveryService(
        source_repository=source_repository,
        knowledge_object_repository=knowledge_object_repository,
    )

    print("Authenticated Discovery repository access established.")

    # ==================================================================
    # Existing baseline test records
    # ==================================================================

    # ------------------------------------------------------------------
    # NEW
    # ------------------------------------------------------------------

    new_record = build_translator_record(
        source_object_id="alphaomega-discovery-new-test",
        name="AlphaOmega New Discovery Test",
        source_parent_object_id=EXISTING_PARENT,
        source_modified_at=EXISTING_MODIFIED_AT,
    )

    # ------------------------------------------------------------------
    # UNCHANGED
    # ------------------------------------------------------------------

    unchanged_record = build_translator_record(
        source_object_id=EXISTING_SOURCE_OBJECT_ID,
        name=EXISTING_NAME,
        source_parent_object_id=EXISTING_PARENT,
        source_modified_at=EXISTING_MODIFIED_AT,
    )

    # ------------------------------------------------------------------
    # MODIFIED - Name changed
    # ------------------------------------------------------------------

    name_modified_record = build_translator_record(
        source_object_id=EXISTING_SOURCE_OBJECT_ID,
        name="AlphaOmega Repository Test Object - Renamed",
        source_parent_object_id=EXISTING_PARENT,
        source_modified_at=EXISTING_MODIFIED_AT,
    )

    # ------------------------------------------------------------------
    # MODIFIED - Parent changed
    # ------------------------------------------------------------------

    parent_modified_record = build_translator_record(
        source_object_id=EXISTING_SOURCE_OBJECT_ID,
        name=EXISTING_NAME,
        source_parent_object_id="alphaomega-different-parent",
        source_modified_at=EXISTING_MODIFIED_AT,
    )

    # ------------------------------------------------------------------
    # MODIFIED - Timestamp changed
    # ------------------------------------------------------------------

    timestamp_modified_record = build_translator_record(
        source_object_id=EXISTING_SOURCE_OBJECT_ID,
        name=EXISTING_NAME,
        source_parent_object_id=EXISTING_PARENT,
        source_modified_at=datetime(
            2026,
            8,
            16,
            14,
            0,
            tzinfo=timezone.utc,
        ),
    )

    # ------------------------------------------------------------------
    # MODIFIED - All comparison fields changed
    # ------------------------------------------------------------------

    all_modified_record = build_translator_record(
        source_object_id=EXISTING_SOURCE_OBJECT_ID,
        name="AlphaOmega Repository Test Object - All Changed",
        source_parent_object_id="alphaomega-all-changed-parent",
        source_modified_at=datetime(
            2026,
            8,
            16,
            15,
            0,
            tzinfo=timezone.utc,
        ),
    )

    # ------------------------------------------------------------------
    # UNCHANGED - Non-comparison fields changed
    # ------------------------------------------------------------------

    ignored_fields_record = build_translator_record(
        source_object_id=EXISTING_SOURCE_OBJECT_ID,
        name=EXISTING_NAME,
        source_parent_object_id=EXISTING_PARENT,
        source_modified_at=EXISTING_MODIFIED_AT,
    )

    ignored_fields_record.source_path = (
        "/this/path/is/deliberately/different"
    )

    ignored_fields_record.source_url = (
        "https://alphaomega.invalid/discovery-test"
    )

    # ==================================================================
    # Nullable baseline test records
    # ==================================================================

    # ------------------------------------------------------------------
    # NULLABLE - NULL parent + NULL timestamp remain unchanged
    # ------------------------------------------------------------------

    nullable_unchanged_record = build_translator_record(
        source_object_id=NULLABLE_SOURCE_OBJECT_ID,
        name=NULLABLE_NAME,
        source_parent_object_id=None,
        source_modified_at=None,
    )

    # ------------------------------------------------------------------
    # NULLABLE - Parent NULL -> value
    # ------------------------------------------------------------------

    nullable_parent_changed_record = build_translator_record(
        source_object_id=NULLABLE_SOURCE_OBJECT_ID,
        name=NULLABLE_NAME,
        source_parent_object_id="alphaomega-nullable-new-parent",
        source_modified_at=None,
    )

    # ------------------------------------------------------------------
    # NULLABLE - Timestamp NULL -> value
    # ------------------------------------------------------------------

    nullable_timestamp_changed_record = build_translator_record(
        source_object_id=NULLABLE_SOURCE_OBJECT_ID,
        name=NULLABLE_NAME,
        source_parent_object_id=None,
        source_modified_at=datetime(
            2026,
            8,
            18,
            14,
            0,
            tzinfo=timezone.utc,
        ),
    )

    # ------------------------------------------------------------------
    # NULLABLE - Parent and timestamp both changed
    # ------------------------------------------------------------------

    nullable_both_changed_record = build_translator_record(
        source_object_id=NULLABLE_SOURCE_OBJECT_ID,
        name=NULLABLE_NAME,
        source_parent_object_id="alphaomega-nullable-new-parent",
        source_modified_at=datetime(
            2026,
            8,
            18,
            14,
            0,
            tzinfo=timezone.utc,
        ),
    )

    # ==================================================================
    # Translator Section
    # ==================================================================

    translator_section = TranslatorSection()

    translator_section.translated_records.extend(
        [
            new_record,
            unchanged_record,
            name_modified_record,
            parent_modified_record,
            timestamp_modified_record,
            all_modified_record,
            ignored_fields_record,
            nullable_unchanged_record,
            nullable_parent_changed_record,
            nullable_timestamp_changed_record,
            nullable_both_changed_record,
        ]
    )

    translator_section.translation_succeeded = True
    translator_section.lock()

    # ==================================================================
    # Discovery
    # ==================================================================

    discovery_section = discovery_service.run(
        translator_section
    )

    print("\nDiscovery results:")

    for index, result in enumerate(
        discovery_section.discovery_records
    ):
        print(
            f"Record {index}: "
            f"correlation_id={result.correlation_id}, "
            f"sync_state={result.sync_state}, "
            f"comparison_reason={result.comparison_reason!r}, "
            f"knowledge_object_id={result.knowledge_object_id}, "
            f"previous_content_hash={result.previous_content_hash!r}"
        )

    # ==================================================================
    # Section validation
    # ==================================================================

    if not discovery_section.discovery_succeeded:
        raise RuntimeError(
            "Discovery did not report successful completion."
        )

    if not discovery_section.is_locked:
        raise RuntimeError(
            "DiscoverySection was not locked after completion."
        )

    if len(discovery_section.record_errors) != 0:
        raise RuntimeError(
            "Discovery produced unexpected record errors: "
            f"{discovery_section.record_errors}"
        )

    if len(discovery_section.discovery_records) != 11:
        raise RuntimeError(
            "Discovery did not return the expected number "
            "of DiscoveryRecords."
        )

    # ==================================================================
    # Correlation validation
    # ==================================================================

    validate_correlation_identity(
        translator_records=(
            translator_section.translated_records
        ),
        discovery_records=(
            discovery_section.discovery_records
        ),
    )

    (
        new_result,
        unchanged_result,
        name_modified_result,
        parent_modified_result,
        timestamp_modified_result,
        all_modified_result,
        ignored_fields_result,
        nullable_unchanged_result,
        nullable_parent_changed_result,
        nullable_timestamp_changed_result,
        nullable_both_changed_result,
    ) = discovery_section.discovery_records

    # ==================================================================
    # Existing baseline validations
    # ==================================================================

    # ------------------------------------------------------------------
    # NEW
    # ------------------------------------------------------------------

    if new_result.sync_state != SyncState.NEW:
        raise RuntimeError(
            "NEW record was not classified as NEW."
        )

    if new_result.knowledge_object_id is not None:
        raise RuntimeError(
            "NEW record unexpectedly received a knowledge_object_id."
        )

    if new_result.previous_content_hash is not None:
        raise RuntimeError(
            "NEW record unexpectedly received a previous content hash."
        )

    if new_result.requires_extraction is not True:
        raise RuntimeError(
            "NEW record was not routed to Extraction."
        )

    if new_result.comparison_reason is not None:
        raise RuntimeError(
            "NEW record unexpectedly received a comparison reason."
        )

    print("NEW classification PASSED.")

    # ------------------------------------------------------------------
    # UNCHANGED
    # ------------------------------------------------------------------

    if unchanged_result.sync_state != SyncState.UNCHANGED:
        raise RuntimeError(
            "Existing matching record was not classified as UNCHANGED."
        )

    validate_existing_object_identity(
        unchanged_result,
        EXISTING_KNOWLEDGE_OBJECT_ID,
        EXISTING_CONTENT_HASH,
        "UNCHANGED record",
    )

    if unchanged_result.requires_extraction is not False:
        raise RuntimeError(
            "UNCHANGED record was incorrectly routed to Extraction."
        )

    if unchanged_result.comparison_reason is not None:
        raise RuntimeError(
            "UNCHANGED record unexpectedly received a comparison reason."
        )

    print("UNCHANGED classification PASSED.")

    # ------------------------------------------------------------------
    # MODIFIED - Name
    # ------------------------------------------------------------------

    if name_modified_result.sync_state != SyncState.MODIFIED:
        raise RuntimeError(
            "Name-changed record was not classified as MODIFIED."
        )

    validate_existing_object_identity(
        name_modified_result,
        EXISTING_KNOWLEDGE_OBJECT_ID,
        EXISTING_CONTENT_HASH,
        "Name-changed record",
    )

    if name_modified_result.comparison_reason != "name changed":
        raise RuntimeError(
            "Name-changed record returned an unexpected "
            "comparison reason."
        )

    if name_modified_result.requires_extraction is not True:
        raise RuntimeError(
            "Name-changed record was not routed to Extraction."
        )

    print("MODIFIED name-change classification PASSED.")

    # ------------------------------------------------------------------
    # MODIFIED - Parent
    # ------------------------------------------------------------------

    if parent_modified_result.sync_state != SyncState.MODIFIED:
        raise RuntimeError(
            "Parent-changed record was not classified as MODIFIED."
        )

    validate_existing_object_identity(
        parent_modified_result,
        EXISTING_KNOWLEDGE_OBJECT_ID,
        EXISTING_CONTENT_HASH,
        "Parent-changed record",
    )

    if (
        parent_modified_result.comparison_reason
        != "source parent changed"
    ):
        raise RuntimeError(
            "Parent-changed record returned an unexpected "
            "comparison reason."
        )

    if parent_modified_result.requires_extraction is not True:
        raise RuntimeError(
            "Parent-changed record was not routed to Extraction."
        )

    print("MODIFIED parent-change classification PASSED.")

    # ------------------------------------------------------------------
    # MODIFIED - Timestamp
    # ------------------------------------------------------------------

    if timestamp_modified_result.sync_state != SyncState.MODIFIED:
        raise RuntimeError(
            "Timestamp-changed record was not classified as MODIFIED."
        )

    validate_existing_object_identity(
        timestamp_modified_result,
        EXISTING_KNOWLEDGE_OBJECT_ID,
        EXISTING_CONTENT_HASH,
        "Timestamp-changed record",
    )

    if (
        timestamp_modified_result.comparison_reason
        != "source modified timestamp changed"
    ):
        raise RuntimeError(
            "Timestamp-changed record returned an unexpected "
            "comparison reason."
        )

    if timestamp_modified_result.requires_extraction is not True:
        raise RuntimeError(
            "Timestamp-changed record was not routed to Extraction."
        )

    print("MODIFIED timestamp-change classification PASSED.")

    # ------------------------------------------------------------------
    # MODIFIED - All three comparison fields
    # ------------------------------------------------------------------

    if all_modified_result.sync_state != SyncState.MODIFIED:
        raise RuntimeError(
            "All-fields-changed record was not classified as MODIFIED."
        )

    validate_existing_object_identity(
        all_modified_result,
        EXISTING_KNOWLEDGE_OBJECT_ID,
        EXISTING_CONTENT_HASH,
        "All-fields-changed record",
    )

    expected_reason = (
        "name changed; "
        "source parent changed; "
        "source modified timestamp changed"
    )

    if all_modified_result.comparison_reason != expected_reason:
        raise RuntimeError(
            "All-fields-changed record returned an unexpected "
            "comparison reason. "
            f"Expected: {expected_reason!r}. "
            f"Actual: {all_modified_result.comparison_reason!r}"
        )

    if all_modified_result.requires_extraction is not True:
        raise RuntimeError(
            "All-fields-changed record was not routed to Extraction."
        )

    print(
        "MODIFIED all-comparison-fields classification PASSED."
    )

    # ------------------------------------------------------------------
    # Non-comparison fields ignored
    # ------------------------------------------------------------------

    if ignored_fields_result.sync_state != SyncState.UNCHANGED:
        raise RuntimeError(
            "Changes to non-comparison fields incorrectly caused "
            "MODIFIED."
        )

    validate_existing_object_identity(
        ignored_fields_result,
        EXISTING_KNOWLEDGE_OBJECT_ID,
        EXISTING_CONTENT_HASH,
        "Non-comparison-fields record",
    )

    if ignored_fields_result.comparison_reason is not None:
        raise RuntimeError(
            "Changes to non-comparison fields unexpectedly produced "
            "a comparison reason."
        )

    if ignored_fields_result.requires_extraction is not False:
        raise RuntimeError(
            "Changes to non-comparison fields incorrectly routed "
            "the record to Extraction."
        )

    print("Non-comparison fields correctly ignored PASSED.")

    # ==================================================================
    # Nullable-field validations
    # ==================================================================

    # ------------------------------------------------------------------
    # NULL + NULL remains UNCHANGED
    # ------------------------------------------------------------------

    if nullable_unchanged_result.sync_state != SyncState.UNCHANGED:
        raise RuntimeError(
            "NULL parent and NULL timestamp were not classified "
            "as UNCHANGED."
        )

    validate_existing_object_identity(
        nullable_unchanged_result,
        NULLABLE_KNOWLEDGE_OBJECT_ID,
        NULLABLE_CONTENT_HASH,
        "Nullable UNCHANGED record",
    )

    if nullable_unchanged_result.comparison_reason is not None:
        raise RuntimeError(
            "Nullable UNCHANGED record unexpectedly received "
            "a comparison reason."
        )

    if nullable_unchanged_result.requires_extraction is not False:
        raise RuntimeError(
            "Nullable UNCHANGED record was incorrectly routed "
            "to Extraction."
        )

    print("Nullable NULL-to-NULL comparison PASSED.")

    # ------------------------------------------------------------------
    # Parent NULL -> value
    # ------------------------------------------------------------------

    if (
        nullable_parent_changed_result.sync_state
        != SyncState.MODIFIED
    ):
        raise RuntimeError(
            "Nullable parent change was not classified as MODIFIED."
        )

    validate_existing_object_identity(
        nullable_parent_changed_result,
        NULLABLE_KNOWLEDGE_OBJECT_ID,
        NULLABLE_CONTENT_HASH,
        "Nullable parent-changed record",
    )

    if (
        nullable_parent_changed_result.comparison_reason
        != "source parent changed"
    ):
        raise RuntimeError(
            "Nullable parent change returned an unexpected "
            "comparison reason. "
            f"Actual: "
            f"{nullable_parent_changed_result.comparison_reason!r}"
        )

    if nullable_parent_changed_result.requires_extraction is not True:
        raise RuntimeError(
            "Nullable parent change was not routed to Extraction."
        )

    print("Nullable parent NULL-to-value comparison PASSED.")

    # ------------------------------------------------------------------
    # Timestamp NULL -> value
    # ------------------------------------------------------------------

    if (
        nullable_timestamp_changed_result.sync_state
        != SyncState.MODIFIED
    ):
        raise RuntimeError(
            "Nullable timestamp change was not classified as MODIFIED."
        )

    validate_existing_object_identity(
        nullable_timestamp_changed_result,
        NULLABLE_KNOWLEDGE_OBJECT_ID,
        NULLABLE_CONTENT_HASH,
        "Nullable timestamp-changed record",
    )

    if (
        nullable_timestamp_changed_result.comparison_reason
        != "source modified timestamp changed"
    ):
        raise RuntimeError(
            "Nullable timestamp change returned an unexpected "
            "comparison reason. "
            f"Actual: "
            f"{nullable_timestamp_changed_result.comparison_reason!r}"
        )

    if (
        nullable_timestamp_changed_result.requires_extraction
        is not True
    ):
        raise RuntimeError(
            "Nullable timestamp change was not routed to Extraction."
        )

    print("Nullable timestamp NULL-to-value comparison PASSED.")

    # ------------------------------------------------------------------
    # Parent and timestamp both NULL -> values
    # ------------------------------------------------------------------

    if (
        nullable_both_changed_result.sync_state
        != SyncState.MODIFIED
    ):
        raise RuntimeError(
            "Combined nullable changes were not classified "
            "as MODIFIED."
        )

    validate_existing_object_identity(
        nullable_both_changed_result,
        NULLABLE_KNOWLEDGE_OBJECT_ID,
        NULLABLE_CONTENT_HASH,
        "Combined nullable-changed record",
    )

    expected_nullable_reason = (
        "source parent changed; "
        "source modified timestamp changed"
    )

    if (
        nullable_both_changed_result.comparison_reason
        != expected_nullable_reason
    ):
        raise RuntimeError(
            "Combined nullable changes returned an unexpected "
            "comparison reason. "
            f"Expected: {expected_nullable_reason!r}. "
            f"Actual: "
            f"{nullable_both_changed_result.comparison_reason!r}"
        )

    if nullable_both_changed_result.requires_extraction is not True:
        raise RuntimeError(
            "Combined nullable changes were not routed "
            "to Extraction."
        )

    print("Combined nullable-field comparison PASSED.")

    # ==================================================================
    # Final result
    # ==================================================================

    print("All nullable-field tests PASSED.")
    print("Discovery Section validation PASSED.")
    print("Discovery Service integration test PASSED.")


if __name__ == "__main__":
    main()