"""
Synchronization Scope Connector Test

Purpose:
    Validates the generic synchronization scope Connector routing boundary.

Verifies:
    - OneDrive scope requests route only to the OneDrive Connector.
    - OneNote scope requests route only to the OneNote Connector.
    - Source names are matched without case sensitivity.
    - The exact selected source-native Container identity is preserved.
    - Unsupported Sources are rejected.
    - Missing Source or scope identity is rejected.
    - Duplicate source registrations are rejected.
    - Missing Connector results are rejected.

Does NOT:
    - Connect to Microsoft Graph.
    - Enumerate OneDrive or OneNote.
    - Access the AlphaOmega database.
    - Create Processing Jobs or Synchronization Runs.
    - Execute the synchronization pipeline.
"""

from scripts.connectors.synchronization_scope_connector import (
    SynchronizationScopeConnector,
)


ONEDRIVE_OBJECT_ID = (
    "onedrive-container-123"
)

ONENOTE_OBJECT_ID = (
    "onenote-container-456"
)


class FakeConnectorSection:
    """
    Minimal controlled Connector result.
    """

    def __init__(
        self,
        source_name,
        source_object_id,
    ):
        self.source_name = source_name
        self.source_object_id = (
            source_object_id
        )


class FakeScopeConnector:
    """
    Controlled source-specific scope Connector.
    """

    def __init__(
        self,
        source_name,
        result=True,
    ):
        self.source_name = source_name
        self.result = result
        self.calls = []

    def run(
        self,
        *,
        source_object_id,
    ):
        self.calls.append(
            source_object_id
        )

        if not self.result:
            return None

        return FakeConnectorSection(
            source_name=(
                self.source_name
            ),
            source_object_id=(
                source_object_id
            ),
        )


def require(
    condition,
    message,
):
    """
    Require one deterministic test condition.
    """

    if not condition:
        raise RuntimeError(
            message
        )


def expect_value_error(
    action,
    test_name,
):
    """
    Require one ValueError.
    """

    try:

        action()

    except ValueError:

        print(
            f"PASS: {test_name}"
        )

        return

    raise RuntimeError(
        f"{test_name} failed."
    )


def main():

    print()
    print(
        "AlphaOmega Synchronization Scope Connector Test"
    )
    print(
        "================================================"
    )
    print()

    onedrive = (
        FakeScopeConnector(
            "onedrive"
        )
    )

    onenote = (
        FakeScopeConnector(
            "onenote"
        )
    )

    connector = (
        SynchronizationScopeConnector(
            [
                onedrive,
                onenote,
            ]
        )
    )

    # ---------------------------------------------------------
    # OneDrive routing
    # ---------------------------------------------------------

    result = connector.run(
        source_name="OneDrive",
        source_object_id=(
            ONEDRIVE_OBJECT_ID
        ),
    )

    require(
        result.source_name
        == "onedrive",
        "OneDrive request did not route to OneDrive Connector.",
    )

    require(
        onedrive.calls
        == [
            ONEDRIVE_OBJECT_ID
        ],
        "OneDrive source-native scope identity was not preserved.",
    )

    require(
        onenote.calls
        == [],
        "OneDrive request unexpectedly reached OneNote Connector.",
    )

    print(
        "PASS: OneDrive scope routed only to OneDrive Connector"
    )

    print(
        "PASS: OneDrive source-native scope identity preserved"
    )

    # ---------------------------------------------------------
    # OneNote routing
    # ---------------------------------------------------------

    result = connector.run(
        source_name="ONENOTE",
        source_object_id=(
            ONENOTE_OBJECT_ID
        ),
    )

    require(
        result.source_name
        == "onenote",
        "OneNote request did not route to OneNote Connector.",
    )

    require(
        onenote.calls
        == [
            ONENOTE_OBJECT_ID
        ],
        "OneNote source-native scope identity was not preserved.",
    )

    require(
        onedrive.calls
        == [
            ONEDRIVE_OBJECT_ID
        ],
        "OneNote request unexpectedly reached OneDrive Connector.",
    )

    print(
        "PASS: OneNote scope routed only to OneNote Connector"
    )

    print(
        "PASS: OneNote source-native scope identity preserved"
    )

    print(
        "PASS: Source routing is case-insensitive"
    )

    # ---------------------------------------------------------
    # Unsupported Source
    # ---------------------------------------------------------

    expect_value_error(
        lambda: connector.run(
            source_name="future_source",
            source_object_id="abc",
        ),
        "Unregistered Source rejected",
    )

    # ---------------------------------------------------------
    # Required values
    # ---------------------------------------------------------

    expect_value_error(
        lambda: connector.run(
            source_name="",
            source_object_id="abc",
        ),
        "Missing source_name rejected",
    )

    expect_value_error(
        lambda: connector.run(
            source_name="OneDrive",
            source_object_id="",
        ),
        "Missing source_object_id rejected",
    )

    # ---------------------------------------------------------
    # Duplicate Source registration
    # ---------------------------------------------------------

    expect_value_error(
        lambda: SynchronizationScopeConnector(
            [
                FakeScopeConnector(
                    "OneDrive"
                ),
                FakeScopeConnector(
                    "onedrive"
                ),
            ]
        ),
        "Duplicate Source Connector registration rejected",
    )

    # ---------------------------------------------------------
    # Missing Connector result
    # ---------------------------------------------------------

    empty_connector = (
        SynchronizationScopeConnector(
            [
                FakeScopeConnector(
                    "onedrive",
                    result=False,
                )
            ]
        )
    )

    try:

        empty_connector.run(
            source_name="onedrive",
            source_object_id=(
                ONEDRIVE_OBJECT_ID
            ),
        )

    except RuntimeError:

        print(
            "PASS: Missing ConnectorSection rejected"
        )

    else:

        raise RuntimeError(
            "Missing ConnectorSection was accepted."
        )

    print()
    print(
        "SYNCHRONIZATION SCOPE CONNECTOR TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()