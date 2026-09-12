"""
File:
    test_source_browsing.py

Purpose:
    Perform a controlled live database test of the Lab 8
    SourceBrowsingService.

This test verifies:
    - Enabled Sources can be listed.
    - Each enabled Source can be browsed.
    - Active Source Containers are returned.
    - Persisted hierarchy can be constructed.

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

from scripts.application.source_browsing_service import (
    SourceBrowsingService,
)


def main():

    print()
    print(
        "AlphaOmega Source Browsing Test"
    )
    print(
        "================================"
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

    service = (
        SourceBrowsingService(
            source_repository=(
                source_repository
            ),
            source_container_repository=(
                source_container_repository
            ),
        )
    )

    sources = (
        service.list_sources()
    )

    print(
        f"Enabled Sources: {len(sources)}"
    )

    print()

    if not sources:
        raise RuntimeError(
            "No enabled Sources were returned."
        )

    for source in sources:

        print(
            f"Source: {source['name']}"
        )

        print(
            f"  Source ID: "
            f"{source['source_id']}"
        )

        result = (
            service.browse_source(
                source[
                    "source_id"
                ]
            )
        )

        print(
            f"  Containers: "
            f"{result['container_count']}"
        )

        print(
            f"  Roots: "
            f"{len(result['roots'])}"
        )

        print()

    print(
        "SOURCE BROWSING TEST: PASS"
    )

    print()


if __name__ == "__main__":
    main()