"""
OneDrive Live Folder Inventory

Purpose:
    Performs a live read-only inventory of a selected OneDrive folder using
    the production Microsoft Graph Connector.

Verifies:
    - The production GraphConnector can retrieve OneDrive inventory data.
    - Objects within the selected folder can be identified from live
      Microsoft Graph results.
    - Source inventory can be inspected without database persistence.

Does NOT:
    - Modify OneDrive.
    - Write to the AlphaOmega database.
    - Perform Extraction or Load.
    - Create Knowledge Objects.
"""

from collections import Counter

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)


# ============================================================================
# Controlled Test Scope
# ============================================================================

TARGET_PATH = (
    "David",
    "Book Ideas",
)


# ============================================================================
# Helpers
# ============================================================================

def find_folder(
    connector,
    parent_id,
    folder_name,
):
    """
    Find exactly one named folder beneath the requested parent.

    parent_id=None means the OneDrive root.
    """

    if parent_id is None:

        endpoint = (
            "/me/drive/root/children"
        )

    else:

        endpoint = (
            "/me/drive/items/"
            f"{parent_id}/children"
        )

    children = (
        connector._get_collection(
            endpoint
        )
    )

    matches = [
        item
        for item in children
        if (
            item.get("name")
            == folder_name
            and "folder" in item
        )
    ]

    if len(matches) != 1:

        raise RuntimeError(
            f"Expected exactly one folder "
            f"named '{folder_name}'. "
            f"Found {len(matches)}."
        )

    return matches[0]


def locate_target_folder(
    connector,
):
    """
    Walk the known folder path and return Adventures.
    """

    parent_id = None
    current_folder = None

    print()
    print("Locating controlled OneDrive scope...")

    for folder_name in TARGET_PATH:

        current_folder = (
            find_folder(
                connector=connector,
                parent_id=parent_id,
                folder_name=folder_name,
            )
        )

        parent_id = (
            current_folder.get(
                "id"
            )
        )

        if not parent_id:

            raise RuntimeError(
                f"Folder '{folder_name}' "
                "is missing its Microsoft Graph ID."
            )

        print(
            f"  FOUND: {folder_name}"
        )

    return current_folder


def crawl_folder(
    connector,
    folder,
    relative_path="",
):
    """
    Recursively inventory one folder and every descendant.

    Returns one inventory entry for the target folder itself
    plus every folder and file beneath it.
    """

    inventory = []

    folder_name = (
        folder.get(
            "name"
        )
    )

    folder_id = (
        folder.get(
            "id"
        )
    )

    if not folder_name:

        raise RuntimeError(
            "OneDrive folder is missing its name."
        )

    if not folder_id:

        raise RuntimeError(
            f"Folder '{folder_name}' "
            "is missing its Microsoft Graph ID."
        )

    object_path = (
        folder_name
        if not relative_path
        else f"{relative_path}/{folder_name}"
    )

    inventory.append(
        {
            "type":
                "CONTAINER",

            "name":
                folder_name,

            "id":
                folder_id,

            "path":
                object_path,
        }
    )

    children = (
        connector._get_collection(
            "/me/drive/items/"
            f"{folder_id}/children"
        )
    )

    for child in children:

        child_name = (
            child.get(
                "name"
            )
        )

        child_id = (
            child.get(
                "id"
            )
        )

        if not child_name:

            raise RuntimeError(
                "OneDrive child object "
                "is missing its name."
            )

        if not child_id:

            raise RuntimeError(
                f"OneDrive object '{child_name}' "
                "is missing its Microsoft Graph ID."
            )

        if "folder" in child:

            inventory.extend(
                crawl_folder(
                    connector=connector,
                    folder=child,
                    relative_path=object_path,
                )
            )

        else:

            inventory.append(
                {
                    "type":
                        "CONTENT",

                    "name":
                        child_name,

                    "id":
                        child_id,

                    "path":
                        f"{object_path}/{child_name}",
                }
            )

    return inventory


# ============================================================================
# Reporting
# ============================================================================

def print_inventory(
    inventory,
):
    """
    Print complete controlled inventory.
    """

    counts = Counter(
        item["type"]
        for item in inventory
    )

    print()
    print("=" * 80)
    print(
        "ONEDRIVE CONTROLLED LIVE INVENTORY"
    )
    print("=" * 80)

    print(
        "Scope: "
        + " -> ".join(
            TARGET_PATH
        )
    )

    print()

    for item in inventory:

        print(
            f"{item['type']:<10} | "
            f"{item['path']}"
        )

    print()
    print("=" * 80)
    print("INVENTORY SUMMARY")
    print("=" * 80)

    print(
        f"CONTAINER objects : "
        f"{counts.get('CONTAINER', 0)}"
    )

    print(
        f"CONTENT objects   : "
        f"{counts.get('CONTENT', 0)}"
    )

    print(
        f"TOTAL objects     : "
        f"{len(inventory)}"
    )

    print()
    print(
        "PASS: Controlled OneDrive scope "
        "enumerated successfully."
    )

    print(
        "No AlphaOmega database writes were performed."
    )

    print()


# ============================================================================
# Main
# ============================================================================

def main():

    print()
    print("=" * 80)
    print(
        "AlphaOmega Live OneDrive "
        "Controlled Inventory Test"
    )
    print("=" * 80)

    connector = (
        GraphConnector()
    )

    target_folder = (
        locate_target_folder(
            connector
        )
    )

    inventory = (
        crawl_folder(
            connector=connector,
            folder=target_folder,
        )
    )

    print_inventory(
        inventory
    )


if __name__ == "__main__":

    main()