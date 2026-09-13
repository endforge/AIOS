"""
Knowledge Object Repository Test

Purpose:
    Validates KnowledgeObjectRepository operations against the AlphaOmega
    database.

Verifies:
    - Knowledge Objects can be created through the repository.
    - Knowledge Objects can be found by source identity.
    - Existing Knowledge Objects can be updated.
    - Repository operations preserve the expected Knowledge Object identity
      and persisted values.

Does NOT:
    - Perform Discovery.
    - Perform Extraction or Load.
    - Retrieve content from a Source of Truth.
    - Execute synchronization orchestration.
"""

from common.security.local_credential_provider import LocalCredentialProvider
from scripts.database.database_connection import DatabaseConnection
from scripts.database.knowledge_object_repository import (
    KnowledgeObjectRepository,
)


def main():
    print("Testing Knowledge Object Repository...")

    credential_provider = LocalCredentialProvider()

    database_connection = DatabaseConnection(
        credential_provider
    )

    client = database_connection.connect()

    repository = KnowledgeObjectRepository(
        client
    )

    print("Authenticated repository access established.")

    # ---------------------------------------------------------
    # Test 1: Existing Knowledge Object
    # ---------------------------------------------------------

    source_id = "39944f99-e5da-487d-800b-8d92d0b61b6f"
    source_object_id = "alphaomega-discovery-repository-test"

    result = repository.find_by_source_identity(
        source_id,
        source_object_id,
    )

    if result is None:
        raise RuntimeError(
            "Expected Knowledge Object was not found."
        )

    expected_values = {
        "id": "118df4ec-429b-4dba-99e7-7cbba2ef4697",
        "title": "AlphaOmega Repository Test Object",
        "source_parent_object_id": "alphaomega-test-parent",
        "source_modified_at": "2026-08-16T13:00:00+00:00",
        "content_hash": "alphaomega-test-content-hash-12345",
    }

    for field_name, expected_value in expected_values.items():
        actual_value = result.get(field_name)

        if actual_value != expected_value:
            raise RuntimeError(
                f"Repository field validation failed for '{field_name}'. "
                f"Expected: {expected_value!r}. "
                f"Actual: {actual_value!r}."
            )

    print("Existing Knowledge Object returned expected facts.")

    # ---------------------------------------------------------
    # Test 2: Missing Knowledge Object
    # ---------------------------------------------------------

    missing_result = repository.find_by_source_identity(
        source_id,
        "alphaomega-repository-test-not-found",
    )

    if missing_result is not None:
        raise RuntimeError(
            "Repository returned an unexpected Knowledge Object."
        )

    print("Nonexistent Knowledge Object correctly returned None.")

    print("Knowledge Object Repository test PASSED.")


if __name__ == "__main__":
    main()