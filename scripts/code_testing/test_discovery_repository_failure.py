"""
Discovery Repository Failure Test

Purpose:
    Verifies Discovery behavior when repository infrastructure fails.

Verifies:
    - An unexpected Knowledge Object repository failure terminates Discovery.
    - The repository failure is converted to a stage-level DiscoveryError.
    - DiscoveryError preserves the original repository exception as its cause.
    - The preserved cause remains the controlled underlying failure.

Does NOT:
    - Test record-level Discovery failure recovery.
    - Modify the live Knowledge Object repository.
    - Perform Extraction or Load.
    - Test Connector or Translator behavior.
"""

from datetime import datetime, timezone

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.database.database_connection import DatabaseConnection
from scripts.database.source_repository import SourceRepository

from scripts.discovery.discovery_service import DiscoveryService

from scripts.translator.translator_record import TranslatorRecord
from scripts.translator.translator_section import TranslatorSection

from scripts.sync.sync_exceptions import DiscoveryError


class FailingKnowledgeObjectRepository:
    """
    Controlled repository substitute that simulates a repository-wide
    infrastructure failure.
    """

    def find_by_source_identity(
        self,
        source_id,
        source_object_id,
    ):
        raise RuntimeError(
            "Simulated Knowledge Object repository failure."
        )


def main():
    print("Testing Discovery repository failure...")

    # ------------------------------------------------------------------
    # Real Source repository
    # ------------------------------------------------------------------

    credential_provider = LocalCredentialProvider()

    database_connection = DatabaseConnection(
        credential_provider
    )

    client = database_connection.connect()

    source_repository = SourceRepository(
        client
    )

    # ------------------------------------------------------------------
    # Controlled failing Knowledge Object repository
    # ------------------------------------------------------------------

    failing_repository = FailingKnowledgeObjectRepository()

    discovery_service = DiscoveryService(
        source_repository=source_repository,
        knowledge_object_repository=failing_repository,
    )

    print("Discovery test infrastructure established.")

    # ------------------------------------------------------------------
    # Valid OneNote record
    # ------------------------------------------------------------------

    record = TranslatorRecord()

    record.source_name = "OneNote"
    record.source_object_id = "discovery-repository-failure-test"
    record.source_parent_object_id = "test-parent"
    record.name = "Discovery Repository Failure Test"
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
            "Repository failure correctly produced "
            f"stage-level DiscoveryError: {error}"
        )

        if not isinstance(error.__cause__, RuntimeError):
            raise RuntimeError(
                "DiscoveryError did not preserve the original "
                "repository failure as its cause."
            )

        if (
            str(error.__cause__)
            != "Simulated Knowledge Object repository failure."
        ):
            raise RuntimeError(
                "DiscoveryError preserved an unexpected "
                "underlying exception."
            )

        print(
            "Original repository failure correctly preserved."
        )

        print(
            "Discovery repository failure test PASSED."
        )

        return

    raise RuntimeError(
        "Repository failure did not terminate Discovery "
        "with DiscoveryError."
    )


if __name__ == "__main__":
    main()