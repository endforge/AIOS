"""
Discovery Source Cache Test

Purpose:
    Verifies that Discovery resolves each Source of Truth only once during
    a Discovery run.

Verifies:
    - Multiple records from the same Source of Truth are processed normally.
    - Five OneNote TranslatorRecords produce five Discovery records.
    - SourceRepository lookup for OneNote occurs exactly once during the run.
    - Discovery reuses the resolved Source identity for subsequent records.

Does NOT:
    - Test caching across separate Discovery runs.
    - Modify Source records.
    - Perform Extraction or Load.
    - Test Connector source enumeration.
"""

from datetime import datetime, timezone

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


class CountingSourceRepository:
    """
    Test wrapper around the real SourceRepository.

    Counts how many times source-name resolution is requested.
    """

    def __init__(self, repository):
        self._repository = repository
        self.lookup_count = 0

    def find_id_by_name(self, source_name):
        self.lookup_count += 1

        return self._repository.find_id_by_name(
            source_name
        )


def build_record(object_number):
    """
    Build a controlled OneNote TranslatorRecord.
    """

    record = TranslatorRecord()

    record.source_name = "OneNote"
    record.source_object_id = (
        f"alphaomega-discovery-cache-test-{object_number}"
    )
    record.source_parent_object_id = "test-parent"
    record.name = (
        f"Discovery Source Cache Test {object_number}"
    )
    record.source_modified_at = datetime(
        2026,
        8,
        18,
        14,
        object_number,
        tzinfo=timezone.utc,
    )

    return record


def main():
    print("Testing Discovery source lookup caching...")

    # ------------------------------------------------------------------
    # Database infrastructure
    # ------------------------------------------------------------------

    credential_provider = LocalCredentialProvider()

    database_connection = DatabaseConnection(
        credential_provider
    )

    client = database_connection.connect()

    real_source_repository = SourceRepository(
        client
    )

    counting_source_repository = CountingSourceRepository(
        real_source_repository
    )

    knowledge_object_repository = KnowledgeObjectRepository(
        client
    )

    discovery_service = DiscoveryService(
        source_repository=counting_source_repository,
        knowledge_object_repository=knowledge_object_repository,
    )

    # ------------------------------------------------------------------
    # Multiple records from the same Source of Truth
    # ------------------------------------------------------------------

    translator_section = TranslatorSection()

    translator_section.translated_records.extend(
        [
            build_record(1),
            build_record(2),
            build_record(3),
            build_record(4),
            build_record(5),
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

    if len(discovery_section.discovery_records) != 5:
        raise RuntimeError(
            "Discovery did not process all five test records."
        )

    if counting_source_repository.lookup_count != 1:
        raise RuntimeError(
            "Discovery did not cache Source resolution correctly. "
            f"Expected 1 Source lookup. "
            f"Actual: {counting_source_repository.lookup_count}."
        )

    print(
        "Five OneNote records processed with one Source lookup."
    )

    print("Discovery source lookup caching test PASSED.")


if __name__ == "__main__":
    main()