"""
Discovery Stage Failure Test

Purpose:
    Verifies Discovery stage-level failure behavior.

Verifies:
    - An unregistered Source of Truth causes Discovery to fail.
    - The failure is raised as a DiscoveryError.
    - A stage-level failure terminates Discovery rather than continuing
      record processing.

Does NOT:
    - Test recoverable record-level failures.
    - Register or modify Sources.
    - Perform Extraction or Load.
    - Modify source data.
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

from scripts.sync.sync_exceptions import DiscoveryError


def main():
    print("Testing Discovery stage-level failure...")

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

    # ------------------------------------------------------------------
    # Controlled invalid Source
    # ------------------------------------------------------------------

    record = TranslatorRecord()

    record.source_name = "AlphaOmega-Source-That-Does-Not-Exist"
    record.source_object_id = "discovery-stage-failure-test"
    record.source_parent_object_id = "test-parent"
    record.name = "Discovery Stage Failure Test"
    record.source_modified_at = datetime(
        2026,
        8,
        18,
        12,
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

    try:
        discovery_service.run(
            translator_section
        )

    except DiscoveryError as error:
        print(
            "Discovery correctly raised stage-level "
            f"DiscoveryError: {error}"
        )

        print(
            "Discovery stage-level failure test PASSED."
        )

        return

    raise RuntimeError(
        "Discovery did not raise DiscoveryError for an "
        "unregistered Source of Truth."
    )


if __name__ == "__main__":
    main()