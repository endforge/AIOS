"""
AlphaOmega Connector Loader

Purpose:
    Loads the appropriate connector for a requested Source of Truth.

Responsibilities:
    - Map supported Source of Truth names to their connector implementation.
    - Return a GraphConnector for supported OneDrive requests.
    - Return a GraphConnector for supported OneNote requests.
    - Reject unsupported Source of Truth names.

Does NOT:
    - Execute the selected connector.
    - Connect to Microsoft Graph.
    - Retrieve source objects.
    - Perform synchronization processing.
"""

from scripts.connectors.graph_connector import GraphConnector

ONEDRIVE = "onedrive"
ONENOTE = "onenote"

def load_connector(source_name):
    """
    Return the connector associated with a source.

    Raises:
        ValueError:
            If the requested source is unsupported.
    """

    source = source_name.lower()

    if source == ONEDRIVE:
        return GraphConnector()

    if source == ONENOTE:
        return GraphConnector()

    raise ValueError(
        f"Unsupported source: '{source_name}'."
    )