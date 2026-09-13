"""
OneDrive Content Retriever

Purpose:
    Retrieves the raw content of one identified OneDrive source object
    for downstream Extraction.

Responsibilities:
    - Retrieve one identified OneDrive file by its source object ID.
    - Use Microsoft Graph to retrieve the file's raw binary content.
    - Return the retrieved content for downstream Extraction.

Does NOT:
    - Enumerate OneDrive.
    - Determine synchronization state.
    - Extract canonical content.
    - Generate content hashes.
    - Persist Knowledge Objects.
"""

from scripts.connectors.ms_graph.graph_connection import graph_get


class OneDriveContentRetriever:
    """
    Retrieve raw binary content for one OneDrive file.
    """

    source_name = "onedrive"

    def retrieve(
        self,
        source_object_id,
    ):
        """
        Retrieve the raw content of one OneDrive file.

        Args:
            source_object_id:
                Microsoft Graph driveItem ID.

        Returns:
            bytes:
                Raw file content.

        Raises:
            ValueError:
                If source_object_id is missing.
        """

        if not source_object_id:
            raise ValueError(
                "OneDrive source object ID is required."
            )

        endpoint = (
            "/me/drive/items/"
            f"{source_object_id}/content"
        )

        response = graph_get(
            endpoint
        )

        return response.content