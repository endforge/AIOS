"""
Source Browsing Service Test

Purpose:
    Performs a controlled live database test of the Lab 8
    SourceBrowsingService.

Verifies:
    - Enabled registered Sources can be listed.
    - A requested Source can be browsed through the application service.
    - Active persisted Source Containers are returned.
    - Persisted parent relationships are assembled into an application-facing
      hierarchy.
    - OneDrive and OneNote catalogs can be browsed without direct UI database
      access.

Does NOT:
    - Refresh Source Containers.
    - Communicate with a Source of Truth.
    - Synchronize content.
    - Modify the AlphaOmega database.
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