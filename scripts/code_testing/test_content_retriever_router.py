"""
Content Retriever Router Test

Purpose:
    Validates selection behavior of the Extraction content retriever router.

Verifies:
    - Supported source and object combinations resolve to the appropriate
      content retriever.
    - Unsupported retrieval requests are rejected as expected.
    - Retriever routing remains separate from content retrieval itself.

Does NOT:
    - Connect to a live Source of Truth.
    - Retrieve source content.
    - Perform Extraction.
    - Persist Knowledge Objects.
"""

from unittest.mock import Mock

from scripts.extraction.content_retriever_router import (
    ContentRetrieverRouter,
)


def test_onedrive_routing():
    """
    Verify canonical OneDrive Source routing.
    """

    onedrive_retriever = Mock()
    onenote_retriever = Mock()

    router = ContentRetrieverRouter(
        onedrive_retriever=onedrive_retriever,
        onenote_retriever=onenote_retriever,
    )

    result = router.get_retriever(
        "OneDrive"
    )

    assert result is onedrive_retriever

    print(
        "PASS: OneDrive retriever selected correctly."
    )


def test_onenote_routing():
    """
    Verify canonical OneNote Source routing.
    """

    onedrive_retriever = Mock()
    onenote_retriever = Mock()

    router = ContentRetrieverRouter(
        onedrive_retriever=onedrive_retriever,
        onenote_retriever=onenote_retriever,
    )

    result = router.get_retriever(
        "OneNote"
    )

    assert result is onenote_retriever

    print(
        "PASS: OneNote retriever selected correctly."
    )


def test_missing_source():
    """
    Verify a missing Source name is rejected.
    """

    router = ContentRetrieverRouter()

    try:
        router.get_retriever(None)

        raise AssertionError(
            "Missing Source name was accepted."
        )

    except ValueError:
        pass

    print(
        "PASS: Missing Source name rejected."
    )


def test_unsupported_source():
    """
    Verify an unregistered Source cannot silently route.
    """

    router = ContentRetrieverRouter()

    try:
        router.get_retriever(
            "UnsupportedSource"
        )

        raise AssertionError(
            "Unsupported Source was accepted."
        )

    except ValueError:
        pass

    print(
        "PASS: Unsupported Source rejected."
    )


def test_noncanonical_source_name():
    """
    Verify Extraction does not silently normalize Source names.
    """

    router = ContentRetrieverRouter()

    for source_name in (
        "onedrive",
        "onenote",
    ):
        try:
            router.get_retriever(
                source_name
            )

            raise AssertionError(
                "Noncanonical Source name "
                f"'{source_name}' was accepted."
            )

        except ValueError:
            pass

    print(
        "PASS: Noncanonical Source names rejected."
    )


def main():
    """
    Run content retriever router tests.
    """

    print(
        "\nRunning content retriever router tests...\n"
    )

    test_onedrive_routing()
    test_onenote_routing()
    test_missing_source()
    test_unsupported_source()
    test_noncanonical_source_name()

    print(
        "\nContent retriever router tests PASSED.\n"
    )


if __name__ == "__main__":
    main()