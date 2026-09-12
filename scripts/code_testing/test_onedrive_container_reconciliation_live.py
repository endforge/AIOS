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
from scripts.connectors.ms_graph.onedrive_container_enumerator import (
    OneDriveContainerEnumerator,
)
from scripts.sync.source_container_observation_validator import (
    SourceContainerObservationValidator,
)
from scripts.sync.source_container_reconciler import (
    SourceContainerReconciler,
)


def main():

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega Live OneDrive Container Reconciliation Test"
    )
    print(
        "============================================================"
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
        SourceRepository(client)
    )

    source_id = (
        source_repository.find_id_by_name(
            "OneDrive"
        )
    )

    if source_id is None:
        raise RuntimeError(
            "Registered OneDrive Source was not found."
        )

    print(
        "PASS: Registered OneDrive Source resolved."
    )
    print(
        f"  Source ID : {source_id}"
    )
    print()

    print(
        "Enumerating live OneDrive Containers..."
    )
    print()

    enumerator = (
        OneDriveContainerEnumerator()
    )

    observation = (
        enumerator.enumerate()
    )

    print(
        "PASS: OneDrive enumeration completed."
    )
    print(
        f"  Containers : "
        f"{len(observation['containers'])}"
    )
    print(
        f"  Complete   : "
        f"{observation['enumeration_complete']}"
    )
    print(
        f"  Delta link : "
        f"{bool(observation.get('delta_link'))}"
    )
    print()

    print(
        "Validating complete observation..."
    )
    print()

    validator = (
        SourceContainerObservationValidator()
    )

    validated_containers = (
        validator.validate(
            observation
        )
    )

    print(
        "PASS: Live OneDrive observation validated."
    )
    print(
        f"  Validated Containers : "
        f"{len(validated_containers)}"
    )
    print()

    source_container_repository = (
        SourceContainerRepository(
            database_connection
        )
    )

    existing_containers = (
        source_container_repository.find_by_source(
            source_id
        )
    )

    print(
        "PASS: Existing Source Container Catalog read."
    )
    print(
        f"  Existing Containers : "
        f"{len(existing_containers)}"
    )
    print()

    reconciler = (
        SourceContainerReconciler()
    )

    result = (
        reconciler.reconcile(
            observed_containers=(
                validated_containers
            ),
            existing_containers=(
                existing_containers
            ),
        )
    )

    print(
        "PASS: Live reconciliation completed."
    )
    print()

    print(
        "RECONCILIATION RESULT"
    )
    print(
        f"  NEW         : {len(result['new'])}"
    )
    print(
        f"  EXISTING    : {len(result['existing'])}"
    )
    print(
        f"  REAPPEARING : {len(result['reappearing'])}"
    )
    print(
        f"  ABSENT      : {len(result['absent'])}"
    )

    print()
    print(
        "No Source Container Catalog changes were written."
    )
    print()
    print(
        "LIVE ONEDRIVE CONTAINER RECONCILIATION TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()