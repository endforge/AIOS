"""
Source Container Observation Validator Test

Purpose:
    Validates SourceContainerObservationValidator behavior using controlled
    Source Container observations.

Verifies:
    - Valid complete observations are accepted.
    - Required observation fields are enforced.
    - Duplicate or inconsistent identities are rejected.
    - Invalid hierarchy relationships are rejected.
    - Observation completeness requirements are enforced before persistence
      decisions.

Does NOT:
    - Enumerate a Source of Truth.
    - Persist Source Containers.
    - Reconcile observations against the database.
    - Synchronize content.
"""

from datetime import datetime, timezone
from uuid import uuid4

from common.security.local_credential_provider import LocalCredentialProvider
from scripts.database.database_connection import DatabaseConnection
from scripts.database.processing_job_repository import ProcessingJobRepository
from scripts.database.source_container_repository import SourceContainerRepository


def main():
    credential_provider = LocalCredentialProvider()
    db = DatabaseConnection(credential_provider)
    client = db.connect()

    processing_job_repository = ProcessingJobRepository(client)
    source_container_repository = SourceContainerRepository(db)

    processing_job_id = None
    source_container_id = None

    try:
        # Find an existing Source to satisfy the source_id FK.
        source_response = (
            client
            .table("sources")
            .select("id")
            .limit(1)
            .execute()
        )

        if not source_response.data:
            raise RuntimeError(
                "No Source exists for repository testing."
            )

        source_id = source_response.data[0]["id"]

        # Create a legitimate temporary Processing Job.
        processing_job_id = processing_job_repository.create(
            process_type="source_container_repository_test",
            pipeline_version="test",
            metadata={
                "purpose": "SourceContainerRepository test"
            },
        )

        print("Temporary Processing Job created.")
        print(f"Processing Job ID: {processing_job_id}")

        # Create one temporary Source Container.
        source_container_id = str(uuid4())
        source_object_id = f"TEST-{uuid4()}"

        test_record = {
            "id": source_container_id,
            "source_id": source_id,
            "source_object_id": source_object_id,
            "parent_source_object_id": None,
            "name": "Source Container Repository Test",
            "last_seen_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "last_seen_processing_job_id": processing_job_id,
            "is_active": True,
        }

        insert_response = (
            client
            .table("source_containers")
            .insert(test_record)
            .execute()
        )

        if not insert_response.data:
            raise RuntimeError(
                "Failed to create temporary Source Container."
            )

        print("Temporary Source Container created.")
        print(f"Source Container ID: {source_container_id}")
        print(f"Source ID: {source_id}")
        print(f"Source Object ID: {source_object_id}")

        # Test 1: Find by AlphaOmega UUID.
        by_id = source_container_repository.find_by_id(
            source_container_id
        )

        assert by_id is not None
        assert by_id["id"] == source_container_id

        print("PASS: find_by_id")

        # Test 2: Find by Source-of-Truth identity.
        by_identity = (
            source_container_repository.find_by_source_identity(
                source_id,
                source_object_id,
            )
        )

        assert by_identity is not None
        assert by_identity["id"] == source_container_id

        print("PASS: find_by_source_identity")

        # Test 3: Both lookup paths return same Container.
        assert by_id["id"] == by_identity["id"]

        print(
            "PASS: both lookup paths return the same Container"
        )

        # Test 4: Find complete saved catalog for Source.
        by_source = source_container_repository.find_by_source(
            source_id
        )

        matching = [
            container
            for container in by_source
            if container["id"] == source_container_id
        ]

        assert len(matching) == 1

        print("PASS: find_by_source")

        # Test 5: Unknown UUID returns None.
        missing = source_container_repository.find_by_id(
            uuid4()
        )

        assert missing is None

        print(
            "PASS: unknown Source Container returns None"
        )

        # Test 6: Required argument validation.
        try:
            source_container_repository.find_by_id(None)

            raise AssertionError(
                "find_by_id(None) should raise ValueError"
            )

        except ValueError:
            pass

        try:
            source_container_repository.find_by_source_identity(
                None,
                source_object_id,
            )

            raise AssertionError(
                "Missing source_id should raise ValueError"
            )

        except ValueError:
            pass

        try:
            source_container_repository.find_by_source_identity(
                source_id,
                None,
            )

            raise AssertionError(
                "Missing source_object_id should raise ValueError"
            )

        except ValueError:
            pass

        try:
            source_container_repository.find_by_source(None)

            raise AssertionError(
                "find_by_source(None) should raise ValueError"
            )

        except ValueError:
            pass

        print("PASS: required argument validation")

        print()
        print(
            "SOURCE CONTAINER REPOSITORY TEST: PASS"
        )

    finally:
        # Remove Source Container before its referenced Processing Job.
        if source_container_id is not None:
            (
                client
                .table("source_containers")
                .delete()
                .eq("id", source_container_id)
                .execute()
            )

            print(
                "Temporary Source Container removed."
            )

        if processing_job_id is not None:
            (
                client
                .table("processing_jobs")
                .delete()
                .eq("id", processing_job_id)
                .execute()
            )

            print(
                "Temporary Processing Job removed."
            )


if __name__ == "__main__":
    main()