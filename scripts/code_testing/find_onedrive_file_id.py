"""
Find OneDrive File ID

Purpose:
    Locates a specific OneDrive file by its known OneDrive-relative path
    and prints its current Microsoft Graph driveItem ID.

Verifies:
    - The configured OneDrive file can be resolved by its known path.
    - Microsoft Graph returns the current driveItem identity for that file.

Does NOT:
    - Enumerate the complete OneDrive.
    - Modify the source file.
    - Write to the AlphaOmega database.
    - Execute synchronization.
"""

from urllib.parse import quote

from scripts.connectors.ms_graph.graph_connection import (
    graph_get,
)


FILE_PATH = (
    "Mimics Tavern/"
    "D&D/"
    "Created Adventures/"
    "Bogmire Adventures/"
    "Drafts/"
    "Bogmire Introduction Draft v1.docx"
)


def main():
    """
    Locate the requested OneDrive file.
    """

    print(
        "\nLocating OneDrive test file...\n"
    )

    encoded_path = quote(
        FILE_PATH,
        safe="/",
    )

    endpoint = (
        f"/me/drive/root:/{encoded_path}"
    )

    response = graph_get(
        endpoint
    )

    item = response.json()

    item_id = item.get(
        "id"
    )

    item_name = item.get(
        "name"
    )

    if not item_id:
        raise RuntimeError(
            "Matching OneDrive file is missing "
            "its Microsoft Graph ID."
        )

    if not item_name:
        raise RuntimeError(
            "Matching OneDrive file is missing "
            "its name."
        )

    print(
        f"File found: {item_name}"
    )

    print(
        f"Path:       {FILE_PATH}"
    )

    print(
        "\nMicrosoft Graph DriveItem ID:"
    )

    print(
        item_id
    )

    print(
        "\nPASS: OneDrive file located successfully.\n"
    )


if __name__ == "__main__":
    main()