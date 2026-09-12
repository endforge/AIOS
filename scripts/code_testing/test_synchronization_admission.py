"""
File:
    test_synchronization_admission.py

Purpose:
    Perform a controlled live database test of persisted
    SynchronizationRequest admission.

This test is read-only.
"""


from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)

from scripts.database.source_repository import (
    SourceRepository,
)

from scripts.database.source_container_repository import (
    SourceContainerRepository,
)

from scripts.sync.sync_request import (
    SynchronizationRequest,
)

from scripts.application.synchronization_admission_service import (
    SynchronizationAdmissionService,
)


def main():

    print()
    print(
        "AlphaOmega Synchronization Admission Test"
    )
    print(
        "=========================================="
    )
    print()

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

    source_container_repository = (
        SourceContainerRepository(
            database_connection
        )
    )

    admission_service = (
        SynchronizationAdmissionService(
            source_repository=(
                source_repository
            ),
            source_container_repository=(
                source_container_repository
            ),
        )
    )

    sources = (
        source_repository.find_enabled()
    )

    if not sources:
        raise RuntimeError(
            "No enabled Sources were found."
        )

    for source in sources:

        source_id = (
            source[
                "id"
            ]
        )

        containers = (
            source_container_repository
            .find_active_by_source(
                source_id
            )
        )

        if not containers:
            raise RuntimeError(
                f"No active Containers found for "
                f"{source['name']}."
            )

        source_container = (
            containers[
                0
            ]
        )

        request = (
            SynchronizationRequest(
                source_id=(
                    source_id
                ),
                source_container_id=(
                    source_container[
                        "id"
                    ]
                ),
            )
        )

        admitted = (
            admission_service.validate(
                request
            )
        )

        print(
            f"Source: {admitted['source_name']}"
        )

        print(
            f"  Source ID: "
            f"{admitted['source_id']}"
        )

        print(
            f"  Container: "
            f"{admitted['container_name']}"
        )

        print(
            f"  Container ID: "
            f"{admitted['source_container_id']}"
        )

        print(
            "  Admission: PASS"
        )

        print()

    print(
        "SYNCHRONIZATION ADMISSION TEST: PASS"
    )

    print()


if __name__ == "__main__":
    main()