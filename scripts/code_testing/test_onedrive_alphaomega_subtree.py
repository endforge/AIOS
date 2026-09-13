"""
OneDrive AlphaOmega Subtree Test

Purpose:
    Validates selection of the AlphaOmega subtree from a complete live
    OneDrive container observation.

Verifies:
    - OneDrive container enumeration completes successfully.
    - The complete observation passes Source Container validation.
    - The AlphaOmega subtree can be identified from the complete observation.
    - Selected subtree membership follows the observed OneDrive hierarchy.

Does NOT:
    - Persist the selected subtree.
    - Modify OneDrive.
    - Synchronize file content.
    - Create Knowledge Objects.
"""


from scripts.connectors.ms_graph.onedrive_container_enumerator import (
    OneDriveContainerEnumerator,
)
from scripts.sync.source_container_observation_validator import (
    SourceContainerObservationValidator,
)


TARGET_NAME = "AlphaOmega"


def main():

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega OneDrive Subtree Diagnostic"
    )
    print(
        "============================================================"
    )
    print()

    # ---------------------------------------------------------
    # Enumerate live OneDrive Containers
    # ---------------------------------------------------------

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
    print()

    # ---------------------------------------------------------
    # Validate complete observation
    # ---------------------------------------------------------

    validator = (
        SourceContainerObservationValidator()
    )

    containers = (
        validator.validate(
            observation
        )
    )

    print(
        "PASS: Complete observation validated."
    )
    print(
        f"  Validated Containers : "
        f"{len(containers)}"
    )
    print()

    # ---------------------------------------------------------
    # Find AlphaOmega
    # ---------------------------------------------------------

    matches = [
        container
        for container in containers
        if container["name"] == TARGET_NAME
    ]

    if not matches:
        raise RuntimeError(
            f'No Container named "{TARGET_NAME}" was found.'
        )

    print(
        f'Containers named "{TARGET_NAME}" found: '
        f"{len(matches)}"
    )
    print()

    for index, match in enumerate(
        matches,
        start=1,
    ):
        print(
            f"Match {index}:"
        )
        print(
            f"  Source Object ID : "
            f"{match['source_object_id']}"
        )
        print(
            f"  Parent ID        : "
            f"{match['parent_source_object_id']}"
        )
        print()

    if len(matches) != 1:
        print(
            "STOP: AlphaOmega name is not unique."
        )
        print(
            "No subtree will be selected automatically."
        )
        print()
        return

    root = matches[0]

    # ---------------------------------------------------------
    # Build parent -> children lookup
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Walk AlphaOmega subtree
    # ---------------------------------------------------------

    subtree = []
    pending = [root]

    while pending:

        current = pending.pop()

        subtree.append(
            current
        )

        children = (
            children_by_parent.get(
                current["source_object_id"],
                [],
            )
        )

        pending.extend(
            children
        )

    # ---------------------------------------------------------
    # Report
    # ---------------------------------------------------------

    descendant_count = (
        len(subtree) - 1
    )

    direct_children = (
        children_by_parent.get(
            root["source_object_id"],
            [],
        )
    )

    print(
        "PASS: AlphaOmega subtree identified."
    )
    print()
    print(
        "SUBTREE RESULT"
    )
    print(
        f"  Root                : "
        f"{root['name']}"
    )
    print(
        f"  Root Source ID      : "
        f"{root['source_object_id']}"
    )
    print(
        f"  Direct Children     : "
        f"{len(direct_children)}"
    )
    print(
        f"  Descendants         : "
        f"{descendant_count}"
    )
    print(
        f"  Total Containers    : "
        f"{len(subtree)}"
    )
    print()

    print(
        "DIRECT CHILDREN"
    )

    for child in sorted(
        direct_children,
        key=lambda item: item["name"].lower(),
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
        "ONEDRIVE ALPHAOMEGA SUBTREE DIAGNOSTIC: PASS"
    )
    print()


if __name__ == "__main__":
    main()