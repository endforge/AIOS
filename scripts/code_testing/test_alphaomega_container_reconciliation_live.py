"""
Read-only live reconciliation test for the persisted
OneDrive AlphaOmega Source Container subtree.

No database writes are performed.
"""

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)
from scripts.connectors.ms_graph.onedrive_container_enumerator import (
    OneDriveContainerEnumerator,
)
from scripts.database.database_connection import (
    DatabaseConnection,
)
from scripts.database.source_container_repository import (
    SourceContainerRepository,
)
from scripts.database.source_repository import (
    SourceRepository,
)
from scripts.sync.source_container_observation_validator import (
    SourceContainerObservationValidator,
)
from scripts.sync.source_container_reconciler import (
    SourceContainerReconciler,
)


SOURCE_NAME = "OneDrive"

ALPHAOMEGA_ROOT_ID = (
    "70EE5AA1D6A4DA1F!s9c76b7e6703145539f4f257f446477f7"
)


def select_subtree(
    containers,
    root_source_object_id,
):
    """
    Return the selected root Container and all descendants.
    """

    containers_by_id = {
        container["source_object_id"]: container
        for container in containers
    }

    if root_source_object_id not in containers_by_id:
        raise RuntimeError(
            "Approved AlphaOmega root is not present "
            "in the validated OneDrive observation."
        )

    containers_by_parent = {}

    for container in containers:

        parent_id = container.get(
            "parent_source_object_id"
        )

        containers_by_parent.setdefault(
            parent_id,
            [],
        ).append(
            container
        )

    subtree = []
    pending = [
        root_source_object_id
    ]
    visited = set()

    while pending:

        source_object_id = pending.pop()

        if source_object_id in visited:
            continue

        visited.add(
            source_object_id
        )

        container = containers_by_id.get(
            source_object_id
        )

        if container is None:
            raise RuntimeError(
                "Subtree references a Container "
                "missing from the validated observation."
            )

        subtree.append(
            container
        )

        for child in containers_by_parent.get(
            source_object_id,
            [],
        ):
            pending.append(
                child["source_object_id"]
            )

    return subtree


def main():

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega Live Source Container Reconciliation Test"
    )
    print(
        "============================================================"
    )
    print()

    # ---------------------------------------------------------
    # Database connection
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Resolve registered OneDrive Source
    # ---------------------------------------------------------

    source_repository = (
        SourceRepository(client)
    )

    source_id = (
        source_repository.find_id_by_name(
            SOURCE_NAME
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

    # ---------------------------------------------------------
    # Fresh complete OneDrive observation
    # ---------------------------------------------------------

    enumerator = (
        OneDriveContainerEnumerator()
    )

    observation = (
        enumerator.enumerate()
    )

    if (
        observation.get(
            "enumeration_complete"
        )
        is not True
    ):
        raise RuntimeError(
            "OneDrive enumeration is not complete."
        )

    print(
        "PASS: Complete OneDrive observation received."
    )
    print(
        f"  Observed Containers : "
        f"{len(observation['containers'])}"
    )
    print()

    # ---------------------------------------------------------
    # Validate complete observation
    # ---------------------------------------------------------

    validator = (
        SourceContainerObservationValidator()
    )

    validated_containers = (
        validator.validate(
            observation
        )
    )

    print(
        "PASS: OneDrive observation validated."
    )
    print(
        f"  Validated Containers : "
        f"{len(validated_containers)}"
    )
    print()

    # ---------------------------------------------------------
    # Select current AlphaOmega subtree
    # ---------------------------------------------------------

    alphaomega_observed = (
        select_subtree(
            validated_containers,
            ALPHAOMEGA_ROOT_ID,
        )
    )

    print(
        "PASS: Current AlphaOmega subtree selected."
    )
    print(
        f"  Observed AlphaOmega Containers : "
        f"{len(alphaomega_observed)}"
    )
    print()

    # ---------------------------------------------------------
    # Read persisted Source Container Catalog
    # ---------------------------------------------------------

    source_container_repository = (
        SourceContainerRepository(
            database_connection
        )
    )

    persisted_all = (
        source_container_repository.find_by_source(
            source_id
        )
    )

    # Only compare persisted records that belong to the
    # AlphaOmega subtree population.
    #
    # The initial population occurred from the previous
    # AlphaOmega observation. Its identities should therefore
    # overlap the current subtree. A previously persisted
    # AlphaOmega Container that has since disappeared must also
    # remain in the reconciliation input so it can become ABSENT.
    #
    # Start from the approved root and reconstruct the persisted
    # subtree using persisted parent relationships.

    persisted_by_id = {
        container["source_object_id"]: container
        for container in persisted_all
    }

    persisted_children = {}

    for container in persisted_all:

        parent_id = container.get(
            "parent_source_object_id"
        )

        persisted_children.setdefault(
            parent_id,
            [],
        ).append(
            container
        )

    alphaomega_existing = []

    if ALPHAOMEGA_ROOT_ID in persisted_by_id:

        pending = [
            ALPHAOMEGA_ROOT_ID
        ]

        visited = set()

        while pending:

            source_object_id = pending.pop()

            if source_object_id in visited:
                continue

            visited.add(
                source_object_id
            )

            container = persisted_by_id.get(
                source_object_id
            )

            if container is None:
                continue

            alphaomega_existing.append(
                container
            )

            for child in persisted_children.get(
                source_object_id,
                [],
            ):
                pending.append(
                    child["source_object_id"]
                )

    else:
        raise RuntimeError(
            "Persisted AlphaOmega root was not found."
        )

    print(
        "PASS: Persisted AlphaOmega catalog read."
    )
    print(
        f"  Persisted AlphaOmega Containers : "
        f"{len(alphaomega_existing)}"
    )
    print()

    # ---------------------------------------------------------
    # Reconcile
    # ---------------------------------------------------------

    reconciler = (
        SourceContainerReconciler()
    )

    result = (
        reconciler.reconcile(
            observed_containers=alphaomega_observed,
            existing_containers=alphaomega_existing,
        )
    )

    print(
        "Reconciliation result:"
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

    # ---------------------------------------------------------
    # Identity proof
    # ---------------------------------------------------------

    existing_count = (
        len(result["existing"])
    )

    if existing_count == 0:
        raise RuntimeError(
            "No persisted AlphaOmega identities were "
            "recognized by reconciliation."
        )

    for pair in result["existing"]:

        existing = pair["existing"]

        if not existing.get("id"):
            raise RuntimeError(
                "An EXISTING Container does not have "
                "a persistent AlphaOmega UUID."
            )

    print(
        "PASS: Persisted Source identities were recognized."
    )
    print(
        "PASS: EXISTING Containers retain AlphaOmega UUIDs."
    )
    print()
    print(
        "ALPHAOMEGA LIVE RECONCILIATION TEST: PASS"
    )
    print()
    print(
        "READ ONLY: No database records were changed."
    )
    print()


if __name__ == "__main__":
    main()