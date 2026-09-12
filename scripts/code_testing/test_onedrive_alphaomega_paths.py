from scripts.connectors.ms_graph.onedrive_container_enumerator import (
    OneDriveContainerEnumerator,
)
from scripts.sync.source_container_observation_validator import (
    SourceContainerObservationValidator,
)


TARGET_NAME = "AlphaOmega"


def build_parent_chain(
    container,
    containers_by_id,
):
    """
    Walk from a Container upward through its represented parents.
    """

    chain = []
    current = container
    visited = set()

    while current is not None:

        source_object_id = (
            current["source_object_id"]
        )

        if source_object_id in visited:
            raise RuntimeError(
                "Cycle encountered while building parent chain."
            )

        visited.add(
            source_object_id
        )

        chain.append(
            current
        )

        parent_id = (
            current[
                "parent_source_object_id"
            ]
        )

        if parent_id is None:
            break

        current = (
            containers_by_id.get(
                parent_id
            )
        )

        if current is None:
            raise RuntimeError(
                "Parent Container was not found in "
                f"validated observation: {parent_id}"
            )

    chain.reverse()

    return chain


def count_subtree(
    root,
    children_by_parent,
):
    """
    Count the root Container and every descendant beneath it.
    """

    count = 0
    pending = [root]

    while pending:

        current = pending.pop()

        count += 1

        pending.extend(
            children_by_parent.get(
                current["source_object_id"],
                [],
            )
        )

    return count


def main():

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega OneDrive Path Diagnostic"
    )
    print(
        "============================================================"
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

    validator = (
        SourceContainerObservationValidator()
    )

    containers = (
        validator.validate(
            observation
        )
    )

    print(
        "PASS: Complete OneDrive observation validated."
    )
    print(
        f"  Containers : {len(containers)}"
    )
    print()

    containers_by_id = {
        container["source_object_id"]:
            container
        for container in containers
    }

    children_by_parent = {}

    for container in containers:

        parent_id = (
            container[
                "parent_source_object_id"
            ]
        )

        children_by_parent.setdefault(
            parent_id,
            [],
        ).append(
            container
        )

    matches = [
        container
        for container in containers
        if container["name"] == TARGET_NAME
    ]

    if not matches:
        raise RuntimeError(
            'No Container named "AlphaOmega" was found.'
        )

    print(
        f'Containers named "AlphaOmega": {len(matches)}'
    )
    print()

    for index, match in enumerate(
        matches,
        start=1,
    ):

        chain = (
            build_parent_chain(
                match,
                containers_by_id,
            )
        )

        subtree_count = (
            count_subtree(
                match,
                children_by_parent,
            )
        )

        print(
            "------------------------------------------------------------"
        )
        print(
            f"MATCH {index}"
        )
        print(
            "------------------------------------------------------------"
        )
        print()

        print(
            f"Source Object ID:"
        )
        print(
            f"  {match['source_object_id']}"
        )
        print()

        print(
            "PARENT CHAIN"
        )

        for depth, container in enumerate(
            chain
        ):

            indent = (
                "  " * depth
            )

            print(
                f"{indent}- {container['name']}"
            )

        print()

        print(
            f"Subtree Containers : {subtree_count}"
        )

        direct_children = (
            children_by_parent.get(
                match["source_object_id"],
                [],
            )
        )

        print(
            f"Direct Children     : {len(direct_children)}"
        )

        if direct_children:

            print()
            print(
                "DIRECT CHILDREN"
            )

            for child in sorted(
                direct_children,
                key=lambda item: (
                    item["name"].lower()
                ),
            ):
                print(
                    f"  - {child['name']}"
                )

        print()

    print(
        "No Source Container Catalog changes were written."
    )
    print()
    print(
        "ONEDRIVE ALPHAOMEGA PATH DIAGNOSTIC: PASS"
    )
    print()


if __name__ == "__main__":
    main()