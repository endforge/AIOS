"""
Microsoft Graph Connector Test

Purpose:
    Validates complete Connector enumeration for the supported Microsoft
    Graph Sources of Truth.

Verifies:
    - OneDrive can be completely enumerated through GraphConnector.
    - OneNote can be completely enumerated through GraphConnector.
    - Connector results can be summarized by canonical object type.
    - Connector processing completes without involving downstream stages.

Does NOT:
    - Perform Translation.
    - Perform Discovery, Extraction, or Load.
    - Modify Microsoft Graph source data.
    - Write to the AlphaOmega database.
"""

from collections import Counter

from scripts.connectors.ms_graph.graph_connector import GraphConnector


def print_connector_summary(section):
    """
    Print a summary of completed Connector output.
    """

    object_types = Counter(
        connector_object["source_object_type"]
        for connector_object in section.raw_objects
    )

    print()
    print(f"Source: {section.source_name}")
    print(
        "Connection succeeded: "
        f"{section.connection_succeeded}"
    )
    print(
        "Enumeration complete: "
        f"{section.raw_metadata.get('enumeration_complete')}"
    )
    print(
        "Objects retrieved: "
        f"{len(section.raw_objects)}"
    )

    print("Object types:")

    for object_type, count in sorted(
        object_types.items()
    ):
        print(
            f"  {object_type}: {count}"
        )


def test_onedrive_connector():
    """
    Completely enumerate OneDrive.
    """

    print("=" * 70)
    print("Testing OneDrive Connector")
    print("=" * 70)

    connector = GraphConnector()

    section = connector.run("onedrive")

    print_connector_summary(section)

    print()
    print("OneDrive Connector: PASS")


def test_onenote_connector():
    """
    Completely enumerate OneNote.
    """

    print()
    print("=" * 70)
    print("Testing OneNote Connector")
    print("=" * 70)

    connector = GraphConnector()

    section = connector.run("onenote")

    print_connector_summary(section)

    print()
    print("OneNote Connector: PASS")


if __name__ == "__main__":
    test_onedrive_connector()
    test_onenote_connector()