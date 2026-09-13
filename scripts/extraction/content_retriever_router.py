"""
AlphaOmega Content Retriever Router

Purpose:
    Selects the appropriate source-specific content retriever for Extraction.

Responsibilities:
    - Route supported OneDrive content requests to the OneDrive retriever.
    - Route supported OneNote content requests to the OneNote retriever.
    - Reject unsupported Source or object combinations.
    - Keep source-specific retrieval selection outside ExtractionService.

Does NOT:
    - Retrieve content itself.
    - Enumerate Sources of Truth.
    - Extract canonical content.
    - Determine synchronization state.
    - Persist Knowledge Objects.
"""

from scripts.connectors.ms_graph.onedrive_content_retriever import (
    OneDriveContentRetriever,
)
from scripts.connectors.ms_graph.onenote_content_retriever import (
    OneNoteContentRetriever,
)


class ContentRetrieverRouter:
    """
    Resolve a Source of Truth to its content retriever.
    """

    def __init__(
        self,
        onedrive_retriever=None,
        onenote_retriever=None,
    ):
        """
        Initialize the content retriever router.

        Optional retriever injection supports isolated testing
        without live source-system access.
        """

        self._retrievers = {
            "OneDrive": (
                onedrive_retriever
                or OneDriveContentRetriever()
            ),
            "OneNote": (
                onenote_retriever
                or OneNoteContentRetriever()
            ),
        }

    def get_retriever(
        self,
        source_name,
    ):
        """
        Return the content retriever registered for a Source of Truth.

        Args:
            source_name:
                Canonical AlphaOmega Source name.

        Returns:
            Source-specific content retriever.

        Raises:
            ValueError:
                If source_name is missing or unsupported.
        """

        if not source_name:
            raise ValueError(
                "Source name is required "
                "for content retriever selection."
            )

        retriever = self._retrievers.get(
            source_name
        )

        if retriever is None:
            raise ValueError(
                "No content retriever is registered "
                f"for Source '{source_name}'."
            )

        return retriever