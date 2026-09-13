"""
OneNote Content Retriever

Purpose:
    Retrieves the raw content of one identified OneNote content object
    for downstream Extraction.

Responsibilities:
    - Retrieve one identified OneNote content object by its source object ID.
    - Use Microsoft Graph to retrieve the object's raw content.
    - Require the requested object to be eligible CONTENT.
    - Return the retrieved content for downstream Extraction.

Does NOT:
    - Enumerate OneNote.
    - Determine synchronization state.
    - Extract canonical content.
    - Generate content hashes.
    - Persist Knowledge Objects.
"""

from common.object_types import CONTENT

from scripts.connectors.ms_graph.graph_connection import graph_get


class OneNoteContentRetriever:
    """
    Retrieve raw HTML content for one canonical OneNote CONTENT object.
    """

    source_name = "onenote"

    def retrieve(
        self,
        source_object_id,
        object_type,
    ):
        """
        Retrieve the raw HTML content of one OneNote content object.

        Args:
            source_object_id:
                Microsoft Graph OneNote page ID.

            object_type:
                Canonical AlphaOmega object type supplied by Translator.

        Returns:
            bytes:
                Raw OneNote page HTML.

        Raises:
            ValueError:
                If source_object_id is missing or the requested
                canonical object is not CONTENT.
        """

        if not source_object_id:
            raise ValueError(
                "OneNote source object ID is required."
            )

        if object_type != CONTENT:
            raise ValueError(
                "OneNote content retrieval supports "
                "canonical CONTENT objects only. "
                f"Received object type '{object_type}'."
            )

        endpoint = (
            "/me/onenote/pages/"
            f"{source_object_id}/content"
        )

        response = graph_get(
            endpoint
        )

        return response.content