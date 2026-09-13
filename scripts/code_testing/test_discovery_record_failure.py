"""
Discovery Record Failure Test

Purpose:
    Verifies Discovery record-level exception handling and orchestration
    correlation preservation.

Verifies:
    - One controlled DiscoveryRecordError fails only the affected record.
    - The failure is recorded in DiscoverySection.record_errors.
    - The failed record's correlation UUID is preserved.
    - Subsequent records continue processing after the record-level failure.
    - Successful records preserve their own correlation UUIDs.
    - Discovery can complete successfully despite the isolated record failure.

Does NOT:
    - Simulate a stage-level Discovery failure.
    - Modify source data.
    - Perform Extraction or Load.
    - Persist Knowledge Objects.
"""

from datetime import datetime, timezone
from uuid import uuid4

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.database.database_connection import DatabaseConnection
from scripts.database.source_repository import SourceRepository
from scripts.database.knowledge_object_repository import (
    KnowledgeObjectRepository,
)

from scripts.discovery.discovery_service import DiscoveryService

from scripts.translator.translator_record import TranslatorRecord
from scripts.translator.translator_section import TranslatorSection

from scripts.sync.sync_exceptions import DiscoveryRecordError
from scripts.sync.sync_state import SyncState


FAILURE_OBJECT_ID = "alphaomega-discovery-record-failure"


class RecordFailureDiscoveryService(DiscoveryService):
    """
    Test-only DiscoveryService that injects one controlled
    DiscoveryRecordError.

    All other records execute through the real Discovery logic.
    """

    def _discover_record(
        self,
        translator_record,
        source_ids,
    ):
        if (
            translator_record.source_object_id
            == FAILURE_OBJECT_ID
        ):
            raise DiscoveryRecordError(
                "Simulated Discovery record-level failure."
            )

        return super()._discover_record(
            translator_record=translator_record,
            source_ids=source_ids,
        )


def build_record(
    source_object_id,
    name,
):
    """
    Build a controlled OneNote TranslatorRecord.

    Each record receives a unique orchestration correlation UUID.
    """

    record = TranslatorRecord()

    record.correlation_id = str(
        uuid4()
    )

    record.source_name = "OneNote"
    record.source_object_id = source_object_id
    record.source_parent_object_id = "test-parent"
    record.name = name
    record.source_modified_at = datetime(
        2026,
        8,
        18,
        14,
        0,
        tzinfo=timezone.utc,
    )

    return record


def main():
    print("Testing Discovery record-level failure handling...")

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

    discovery_service = RecordFailureDiscoveryService(
        source_repository=source_repository,
        knowledge_object_repository=knowledge_object_repository,
    )

    # ------------------------------------------------------------------
    # Controlled records
    # ------------------------------------------------------------------
    #
    # Record 1 should succeed.
    # Record 2 should raise DiscoveryRecordError.
    # Record 3 should still execute successfully.
    #

    first_record = build_record(
        source_object_id="alphaomega-discovery-record-before",
        name="Discovery Record Before Failure",
    )

    failing_record = build_record(
        source_object_id=FAILURE_OBJECT_ID,
        name="Discovery Record Failure",
    )

    third_record = build_record(
        source_object_id="alphaomega-discovery-record-after",
        name="Discovery Record After Failure",
    )

    translator_section = TranslatorSection()

    translator_section.translated_records.extend(
        [
            first_record,
            failing_record,
            third_record,
        ]
    )

    translator_section.translation_succeeded = True
    translator_section.lock()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    discovery_section = discovery_service.run(
        translator_section
    )

    # ------------------------------------------------------------------
    # Stage completion validation
    # ------------------------------------------------------------------

    if discovery_section.discovery_succeeded is not True:
        raise RuntimeError(
            "Discovery did not complete after a record-level failure."
        )

    if not discovery_section.is_locked:
        raise RuntimeError(
            "DiscoverySection was not locked after completion."
        )

    # ------------------------------------------------------------------
    # Successful record validation
    # ------------------------------------------------------------------

    if len(discovery_section.discovery_records) != 2:
        raise RuntimeError(
            "Discovery did not return exactly two successful records. "
            f"Actual: {len(discovery_section.discovery_records)}."
        )

    first_result = discovery_section.discovery_records[0]
    third_result = discovery_section.discovery_records[1]

    if first_result.sync_state != SyncState.NEW:
        raise RuntimeError(
            "Record before failure did not complete successfully."
        )

    if third_result.sync_state != SyncState.NEW:
        raise RuntimeError(
            "Record after failure did not continue successfully."
        )

    # ------------------------------------------------------------------
    # Successful correlation validation
    # ------------------------------------------------------------------

    if (
        first_result.correlation_id
        != first_record.correlation_id
    ):
        raise RuntimeError(
            "Record before failure did not preserve its "
            "correlation identity."
        )

    if (
        third_result.correlation_id
        != third_record.correlation_id
    ):
        raise RuntimeError(
            "Record after failure did not preserve its "
            "correlation identity."
        )

    if (
        first_result.correlation_id
        == third_result.correlation_id
    ):
        raise RuntimeError(
            "Successful Discovery records unexpectedly share "
            "the same correlation identity."
        )

    print(
        "Records before and after failure processed successfully."
    )

    print(
        "Successful records preserved correlation identity."
    )

    # ------------------------------------------------------------------
    # Record error validation
    # ------------------------------------------------------------------

    if len(discovery_section.record_errors) != 1:
        raise RuntimeError(
            "Discovery did not record exactly one record-level error. "
            f"Actual: {len(discovery_section.record_errors)}."
        )

    error = discovery_section.record_errors[0]

    if error["stage"] != "Discovery":
        raise RuntimeError(
            "Record error contains an unexpected stage."
        )

    if error["object_id"] != FAILURE_OBJECT_ID:
        raise RuntimeError(
            "Record error identifies the wrong source object."
        )

    if (
        error["exception_type"]
        != "DiscoveryRecordError"
    ):
        raise RuntimeError(
            "Record error contains an unexpected exception type."
        )

    if (
        error["failure_reason"]
        != "Simulated Discovery record-level failure."
    ):
        raise RuntimeError(
            "Record error contains an unexpected failure reason."
        )

    # ------------------------------------------------------------------
    # Failed correlation validation
    # ------------------------------------------------------------------

    if "correlation_id" not in error:
        raise RuntimeError(
            "Discovery record-level error is missing "
            "correlation identity."
        )

    if (
        error["correlation_id"]
        != failing_record.correlation_id
    ):
        raise RuntimeError(
            "Discovery record-level error did not preserve "
            "the failed record's correlation identity. "
            f"Expected: {failing_record.correlation_id!r}. "
            f"Actual: {error['correlation_id']!r}."
        )

    if error["correlation_id"] in {
        first_record.correlation_id,
        third_record.correlation_id,
    }:
        raise RuntimeError(
            "Failed record correlation identity was incorrectly "
            "associated with a successful record."
        )

    print(
        "Discovery record-level error captured correctly."
    )

    print(
        "Failed record preserved correlation identity."
    )

    print(
        "Discovery continued processing after the failed record."
    )

    print(
        "Discovery record-level failure test PASSED."
    )


if __name__ == "__main__":
    main()