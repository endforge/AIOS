"""
Live Source Container Validation Test

Purpose:
    Verifies that persisted AlphaOmega Source Container identities can be
    validated against their live Sources of Truth.

Verifies:
    - An active persisted OneDrive Source Container can be resolved from
      AlphaOmega identity to Microsoft Graph identity.
    - The persisted OneDrive Microsoft Graph object still exists as a folder.
    - An active persisted OneNote Source Container can be resolved from
      AlphaOmega identity to Microsoft Graph identity.
    - The persisted OneNote Microsoft Graph object still exists in a complete
      current OneNote container observation.
    - Generic Source Container validation routes both Sources correctly.

Does NOT:
    - Modify the AlphaOmega database.
    - Refresh the Source Container Catalog.
    - Create Processing Jobs.
    - Create Synchronization Runs.
    - Reserve synchronization.
    - Retrieve synchronization content.
    - Execute synchronization.
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

from scripts.connectors.source_container_validator import (
    SourceContainerValidator,
)

from scripts.connectors.ms_graph.onedrive_container_validator import (
    OneDriveContainerValidator,
)

from scripts.connectors.ms_graph.onenote_container_validator import (
    OneNoteContainerValidator,
)


def require(
    condition,
    message,
):
    """
    Require one live validation condition.
    """

    if not condition:
        raise RuntimeError(
            message
        )


def get_source_by_name(
    source_repository,
    source_name,
):
    """
    Find one enabled Source by its registered name.
    """

    sources = (
        source_repository.find_enabled()
    )

    for source in sources:

        if (
            str(
                source.get(
                    "name",
                    "",
                )
            ).strip().lower()
            == source_name
        ):
            return source

    raise RuntimeError(
        "Enabled Source was not found: "
        f"{source_name}"
    )


def select_active_container(
    source_container_repository,
    source_id,
):
    """
    Select one active persisted Source Container for live validation.
    """

    containers = (
        source_container_repository
        .find_active_by_source(
            source_id
        )
    )

    require(
        bool(
            containers
        ),
        "No active Source Containers were found "
        f"for Source {source_id}.",
    )

    for container in containers:

        source_object_id = (
            container.get(
                "source_object_id"
            )
        )

        if (
            source_object_id is not None
            and str(
                source_object_id
            ).strip()
        ):
            return container

    raise RuntimeError(
        "No active Source Container with a Source-native "
        f"object ID was found for Source {source_id}."
    )


def validate_source(
    *,
    source_name,
    source,
    container,
    validator,
):
    """
    Validate one persisted Source Container against its live Source.
    """

    source_id = str(
        source[
            "id"
        ]
    )

    source_container_id = str(
        container[
            "id"
        ]
    )

    source_object_id = str(
        container[
            "source_object_id"
        ]
    ).strip()

    container_name = (
        container.get(
            "name"
        )
    )

    print(
        f"Source: {source_name}"
    )

    print(
        f"  AlphaOmega Source ID: {source_id}"
    )

    print(
        "  AlphaOmega Source Container ID: "
        f"{source_container_id}"
    )

    print(
        "  Source Object ID: "
        f"{source_object_id}"
    )

    print(
        "  Container Name: "
        f"{container_name}"
    )

    result = (
        validator.validate(
            source_name=source_name,
            source_object_id=source_object_id,
        )
    )

    require(
        result.get(
            "exists"
        )
        is True,
        f"Live {source_name} Source Container "
        "validation reported that the persisted "
        "container no longer exists.",
    )

    require(
        result.get(
            "source_name"
        )
        == source_name,
        f"Live {source_name} validation returned "
        "the wrong Source name.",
    )

    require(
        result.get(
            "source_object_id"
        )
        == source_object_id,
        f"Live {source_name} validation returned "
        "the wrong Source object ID.",
    )

    print(
        "  PASS: Persisted identity exists "
        "at Source of Truth"
    )

    print()


def main():

    print()
    print(
        "AlphaOmega Live Source Container Validation Test"
    )
    print(
        "================================================"
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

    validator = (
        SourceContainerValidator(
            {
                "onedrive":
                    OneDriveContainerValidator(),

                "onenote":
                    OneNoteContainerValidator(),
            }
        )
    )

    for source_name in (
        "onedrive",
        "onenote",
    ):

        source = (
            get_source_by_name(
                source_repository,
                source_name,
            )
        )

        container = (
            select_active_container(
                source_container_repository,
                source[
                    "id"
                ],
            )
        )

        validate_source(
            source_name=source_name,
            source=source,
            container=container,
            validator=validator,
        )

    print(
        "LIVE SOURCE CONTAINER VALIDATION TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()