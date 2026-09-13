"""
Discovery Lock Enforcement Test

Purpose:
    Validates synchronization section locking at the Discovery boundary.

Verifies:
    - Discovery accepts the required completed Translator input.
    - Completed synchronization sections cannot be modified after locking.
    - Attempts to violate the section-lock contract raise the expected
      synchronization exception.
    - Discovery preserves the synchronization framework's stage ownership
      boundary.

Does NOT:
    - Modify live source content.
    - Perform Extraction or Load.
    - Test Connector behavior.
    - Bypass synchronization section locking.
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

from scripts.sync.sync_exceptions import SectionLockedError


def main():
    print("Testing Discovery lock enforcement...")

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

    # ------------------------------------------------------------------
    # Controlled NEW record
    # ------------------------------------------------------------------

    record = TranslatorRecord()

    record.source_name = "OneNote"
    record.source_object_id = "alphaomega-discovery-lock-test"
    record.source_parent_object_id = "test-parent"
    record.name = "Discovery Lock Test"
    record.source_modified_at = datetime(
        2026,
        8,
        18,
        14,
        0,
        tzinfo=timezone.utc,
    )

    translator_section = TranslatorSection()

    translator_section.translated_records.append(
        record
    )

    translator_section.translation_succeeded = True
    translator_section.lock()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    discovery_section = discovery_service.run(
        translator_section
    )

    if not discovery_section.is_locked:
        raise RuntimeError(
            "DiscoverySection did not report itself as locked."
        )

    print("DiscoverySection reports locked PASSED.")

    # ------------------------------------------------------------------
    # Test attribute modification
    # ------------------------------------------------------------------

    try:
        discovery_section.discovery_succeeded = False

    except SectionLockedError:
        print(
            "Locked DiscoverySection rejected attribute "
            "modification PASSED."
        )

    else:
        raise RuntimeError(
            "Locked DiscoverySection allowed attribute modification."
        )

    # ------------------------------------------------------------------
    # Test collection modification
    # ------------------------------------------------------------------

    try:
        discovery_section.discovery_records.append(
            "should-not-be-added"
        )

    except AttributeError:
        print(
            "Frozen Discovery record collection rejected "
            "append PASSED."
        )

    else:
        raise RuntimeError(
            "Discovery record collection remained mutable "
            "after section locking."
        )

    print("Discovery lock enforcement test PASSED.")


if __name__ == "__main__":
    main()