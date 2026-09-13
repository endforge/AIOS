"""
Microsoft Graph Content Retriever Test

Purpose:
    Validates OneDrive and OneNote content retrievers without making live
    Microsoft Graph requests.

Verifies:
    - OneDrive content can be retrieved for a valid source object ID.
    - Missing OneDrive source object identity is rejected.
    - OneNote CONTENT can be retrieved for a valid source object ID.
    - Missing OneNote source object identity is rejected.
    - Missing OneNote canonical object type is rejected.
    - OneNote CONTAINER objects are rejected from content retrieval.
    - Retriever behavior uses AlphaOmega canonical object types downstream
      of Translator.

Does NOT:
    - Make live Microsoft Graph requests.
    - Enumerate OneDrive or OneNote.
    - Perform Extraction or Load.
    - Persist Knowledge Objects.
"""

from unittest.mock import Mock, patch

from common.object_types import (
    CONTENT,
    CONTAINER,
)

from scripts.connectors.ms_graph.onedrive_content_retriever import (
    OneDriveContentRetriever,
)
from scripts.connectors.ms_graph.onenote_content_retriever import (
    OneNoteContentRetriever,
)


def test_onedrive_retrieval():
    """
    Verify OneDrive retrieval uses the expected Graph endpoint
    and returns raw response bytes.
    """

    retriever = OneDriveContentRetriever()

    mock_response = Mock()
    mock_response.content = b"OneDrive test content"

    with patch(
        "scripts.connectors.ms_graph."
        "onedrive_content_retriever.graph_get",
        return_value=mock_response,
    ) as mock_graph_get:

        result = retriever.retrieve(
            "drive-item-123"
        )

    assert result == b"OneDrive test content"

    mock_graph_get.assert_called_once_with(
        "/me/drive/items/drive-item-123/content"
    )

    print(
        "PASS: OneDrive content retrieval routed correctly."
    )


def test_onedrive_missing_id():
    """
    Verify OneDrive retrieval rejects a missing object ID.
    """

    retriever = OneDriveContentRetriever()

    try:
        retriever.retrieve(None)

        raise AssertionError(
            "Missing OneDrive object ID was accepted."
        )

    except ValueError:
        pass

    print(
        "PASS: OneDrive missing object ID rejected."
    )


def test_onenote_retrieval():
    """
    Verify canonical OneNote CONTENT retrieval uses the expected
    Graph page-content endpoint and returns raw response bytes.
    """

    retriever = OneNoteContentRetriever()

    mock_response = Mock()
    mock_response.content = b"<html>OneNote test</html>"

    with patch(
        "scripts.connectors.ms_graph."
        "onenote_content_retriever.graph_get",
        return_value=mock_response,
    ) as mock_graph_get:

        result = retriever.retrieve(
            source_object_id="page-456",
            object_type=CONTENT,
        )

    assert result == b"<html>OneNote test</html>"

    mock_graph_get.assert_called_once_with(
        "/me/onenote/pages/page-456/content"
    )

    print(
        "PASS: OneNote canonical CONTENT retrieval "
        "routed correctly."
    )


def test_onenote_missing_id():
    """
    Verify OneNote retrieval rejects a missing object ID.
    """

    retriever = OneNoteContentRetriever()

    try:
        retriever.retrieve(
            source_object_id=None,
            object_type=CONTENT,
        )

        raise AssertionError(
            "Missing OneNote object ID was accepted."
        )

    except ValueError:
        pass

    print(
        "PASS: OneNote missing object ID rejected."
    )


def test_onenote_container_rejected():
    """
    Verify canonical CONTAINER objects cannot be retrieved
    as OneNote page content.
    """

    retriever = OneNoteContentRetriever()

    try:
        retriever.retrieve(
            source_object_id="container-123",
            object_type=CONTAINER,
        )

        raise AssertionError(
            "OneNote canonical CONTAINER was accepted "
            "for content retrieval."
        )

    except ValueError:
        pass

    print(
        "PASS: OneNote canonical CONTAINER rejected."
    )


def test_onenote_missing_object_type():
    """
    Verify OneNote retrieval rejects a missing canonical
    object type.
    """

    retriever = OneNoteContentRetriever()

    try:
        retriever.retrieve(
            source_object_id="page-456",
            object_type=None,
        )

        raise AssertionError(
            "Missing OneNote canonical object type was accepted."
        )

    except ValueError:
        pass

    print(
        "PASS: OneNote missing canonical object type rejected."
    )


def main():
    """
    Run Microsoft Graph content retriever tests.
    """

    print(
        "\nRunning Microsoft Graph "
        "content retriever tests...\n"
    )

    test_onedrive_retrieval()
    test_onedrive_missing_id()

    test_onenote_retrieval()
    test_onenote_missing_id()
    test_onenote_container_rejected()
    test_onenote_missing_object_type()

    print(
        "\nMicrosoft Graph content "
        "retriever tests PASSED.\n"
    )


if __name__ == "__main__":
    main()