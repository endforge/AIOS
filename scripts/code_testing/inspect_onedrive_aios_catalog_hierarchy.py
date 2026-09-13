"""
OneDrive AIOS Source Container Catalog Hierarchy Inspection

Purpose:
    Inspect the freshly refreshed OneDrive Source Container Catalog around
    every active Container named AIOS.

Responsibilities:
    - Resolve the enabled OneDrive Source.
    - Load all active OneDrive Source Containers.
    - Identify every active Container named AIOS.
    - Show each AIOS Container's persisted identity and parent identity.
    - Resolve each persisted parent when possible.
    - Show immediate child Containers.
    - Recursively count all descendant Containers.
    - Show a small sample of the hierarchy beneath each AIOS Container.

This script is read-only.

It does NOT:
    - Call Microsoft Graph.
    - Refresh Source Containers.
    - Synchronize content.
    - Create Processing Jobs.
    - Modify database records.
"""

from collections import defaultdict, deque

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)

from scripts.sync.source_container_root_service import (
    SourceContainerRootService,
)


SOURCE_NAME = "OneDrive"
TARGET_NAME = "AIOS"

ROOT_SOURCE_OBJECT_ID = (
    SourceContainerRootService
    .ROOT_SOURCE_OBJECT_ID
)

SAMPLE_LIMIT = 30


def create_database():
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

    return client


def resolve_source(
    client,
):
    response = (
        client
        .table(
            "sources"
        )
        .select(
            "id,name,is_enabled"
        )
        .eq(
            "name",
            SOURCE_NAME,
        )
        .execute()
    )

    rows = response.data or []

    if len(rows) != 1:
        raise RuntimeError(
            "Expected exactly one OneDrive Source."
        )

    source = rows[0]

    if (
        source.get(
            "is_enabled"
        )
        is not True
    ):
        raise RuntimeError(
            "OneDrive Source is not enabled."
        )

    return source


def load_active_containers(
    client,
    *,
    source_id,
):
    """
    Load the complete active OneDrive Source Container Catalog.

    Pagination is explicit so the inspection does not accidentally examine
    only the database API's first result page.
    """

    page_size = 1000
    offset = 0
    containers = []

    while True:
        response = (
            client
            .table(
                "source_containers"
            )
            .select(
                "id,"
                "source_id,"
                "source_object_id,"
                "parent_source_object_id,"
                "name,"
                "is_active"
            )
            .eq(
                "source_id",
                source_id,
            )
            .eq(
                "is_active",
                True,
            )
            .range(
                offset,
                offset + page_size - 1,
            )
            .execute()
        )

        rows = response.data or []

        containers.extend(
            rows
        )

        if len(rows) < page_size:
            break

        offset += page_size

    return containers


def normalize_identity(
    value,
):
    if value is None:
        return None

    value = str(
        value
    ).strip()

    if not value:
        return None

    return value


def build_indexes(
    containers,
):
    """
    Build identity and parent-child indexes from persisted catalog data.
    """

    by_object_id = {}

    children_by_parent = defaultdict(
        list
    )

    for container in containers:
        object_id = normalize_identity(
            container.get(
                "source_object_id"
            )
        )

        parent_id = normalize_identity(
            container.get(
                "parent_source_object_id"
            )
        )

        if object_id:
            by_object_id[
                object_id
            ] = container

        if parent_id:
            children_by_parent[
                parent_id
            ].append(
                container
            )

    for children in children_by_parent.values():
        children.sort(
            key=lambda row: (
                str(
                    row.get(
                        "name"
                    )
                    or ""
                ).casefold(),
                str(
                    row.get(
                        "source_object_id"
                    )
                    or ""
                ),
            )
        )

    return (
        by_object_id,
        children_by_parent,
    )


def collect_descendants(
    root_object_id,
    *,
    children_by_parent,
):
    """
    Traverse persisted parent_source_object_id relationships.
    """

    descendants = []

    visited = {
        root_object_id
    }

    queue = deque(
        [
            (
                child,
                1,
            )
            for child
            in children_by_parent.get(
                root_object_id,
                [],
            )
        ]
    )

    while queue:
        (
            container,
            depth,
        ) = queue.popleft()

        object_id = normalize_identity(
            container.get(
                "source_object_id"
            )
        )

        if not object_id:
            continue

        if object_id in visited:
            continue

        visited.add(
            object_id
        )

        descendants.append(
            (
                container,
                depth,
            )
        )

        for child in children_by_parent.get(
            object_id,
            [],
        ):
            queue.append(
                (
                    child,
                    depth + 1,
                )
            )

    return descendants


def describe_parent(
    parent_object_id,
    *,
    by_object_id,
):
    if parent_object_id is None:
        return (
            "None"
        )

    if (
        parent_object_id
        == ROOT_SOURCE_OBJECT_ID
    ):
        return (
            "AlphaOmega synthetic Source Root"
        )

    parent = by_object_id.get(
        parent_object_id
    )

    if parent is None:
        return (
            "NOT FOUND AS ACTIVE SOURCE CONTAINER"
        )

    return (
        f"{parent.get('name')} "
        f"[{parent.get('id')}]"
    )


def print_container_report(
    container,
    *,
    by_object_id,
    children_by_parent,
):
    object_id = normalize_identity(
        container.get(
            "source_object_id"
        )
    )

    parent_object_id = normalize_identity(
        container.get(
            "parent_source_object_id"
        )
    )

    immediate_children = (
        children_by_parent.get(
            object_id,
            [],
        )
    )

    descendants = (
        collect_descendants(
            object_id,
            children_by_parent=(
                children_by_parent
            ),
        )
    )

    print()
    print(
        "-" * 72
    )

    print(
        f"AIOS Container: {container.get('id')}"
    )

    print(
        "-" * 72
    )

    print(
        f"  Name                : "
        f"{container.get('name')}"
    )

    print(
        f"  Source Object ID    : "
        f"{object_id}"
    )

    print(
        f"  Parent Object ID    : "
        f"{parent_object_id}"
    )

    print(
        f"  Parent Resolution   : "
        f"{describe_parent(parent_object_id, by_object_id=by_object_id)}"
    )

    print(
        f"  Immediate Children  : "
        f"{len(immediate_children)}"
    )

    print(
        f"  Total Descendants   : "
        f"{len(descendants)}"
    )

    if immediate_children:
        print()
        print(
            "Immediate child Containers:"
        )

        for child in immediate_children[
            :SAMPLE_LIMIT
        ]:
            print(
                "  - "
                f"{child.get('name')} "
                f"[{child.get('source_object_id')}]"
            )

        if (
            len(immediate_children)
            > SAMPLE_LIMIT
        ):
            print(
                "  ... "
                f"{len(immediate_children) - SAMPLE_LIMIT} "
                "additional immediate children"
            )

    if descendants:
        print()
        print(
            f"Hierarchy sample "
            f"(first {min(len(descendants), SAMPLE_LIMIT)} descendants):"
        )

        for (
            descendant,
            depth,
        ) in descendants[
            :SAMPLE_LIMIT
        ]:
            indent = (
                "  " * depth
            )

            print(
                f"{indent}- "
                f"{descendant.get('name')} "
                f"[{descendant.get('source_object_id')}]"
            )

        if (
            len(descendants)
            > SAMPLE_LIMIT
        ):
            print(
                "  ... "
                f"{len(descendants) - SAMPLE_LIMIT} "
                "additional descendants"
            )


def main():
    print()
    print(
        "=" * 72
    )

    print(
        "OneDrive AIOS Source Container Catalog Hierarchy Inspection"
    )

    print(
        "=" * 72
    )

    print()

    client = create_database()

    print(
        "PASS: Authenticated AlphaOmega database connection established."
    )

    source = resolve_source(
        client
    )

    source_id = str(
        source[
            "id"
        ]
    )

    print(
        "PASS: Enabled OneDrive Source resolved."
    )

    print(
        f"  Source ID : {source_id}"
    )

    containers = (
        load_active_containers(
            client,
            source_id=source_id,
        )
    )

    print()
    print(
        "PASS: Active OneDrive Source Container Catalog loaded."
    )

    print(
        f"  Active Containers : {len(containers)}"
    )

    (
        by_object_id,
        children_by_parent,
    ) = build_indexes(
        containers
    )

    roots = [
        container
        for container in containers
        if normalize_identity(
            container.get(
                "source_object_id"
            )
        )
        == ROOT_SOURCE_OBJECT_ID
    ]

    print(
        f"  Synthetic Roots   : {len(roots)}"
    )

    if roots:
        root_children = (
            children_by_parent.get(
                ROOT_SOURCE_OBJECT_ID,
                [],
            )
        )

        print(
            f"  Root Children     : {len(root_children)}"
        )

        print()
        print(
            "Top-level catalog Containers:"
        )

        for child in root_children[
            :SAMPLE_LIMIT
        ]:
            print(
                "  - "
                f"{child.get('name')} "
                f"[{child.get('source_object_id')}]"
            )

        if (
            len(root_children)
            > SAMPLE_LIMIT
        ):
            print(
                "  ... "
                f"{len(root_children) - SAMPLE_LIMIT} "
                "additional top-level Containers"
            )

    aios_containers = [
        container
        for container in containers
        if str(
            container.get(
                "name"
            )
            or ""
        ).strip().casefold()
        == TARGET_NAME.casefold()
    ]

    print()
    print(
        f"Active Containers named AIOS: "
        f"{len(aios_containers)}"
    )

    if not aios_containers:
        raise RuntimeError(
            "No active OneDrive Source Container named AIOS "
            "exists in the freshly refreshed catalog."
        )

    for container in aios_containers:
        print_container_report(
            container,
            by_object_id=by_object_id,
            children_by_parent=children_by_parent,
        )

    print()
    print(
        "=" * 72
    )

    print(
        "READ-ONLY AIOS CATALOG INSPECTION COMPLETE"
    )

    print(
        "=" * 72
    )

    print()


if __name__ == "__main__":
    main()