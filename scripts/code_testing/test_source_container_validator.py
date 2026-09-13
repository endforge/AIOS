"""
Source Container Validator Test

Purpose:
    Performs isolated deterministic tests of generic and source-specific
    Source Container validation.

Verifies:
    - Generic validation routes requests by Source.
    - Unsupported Sources are rejected.
    - OneDrive validates a matching Microsoft Graph folder.
    - OneDrive rejects an object that is not a folder.
    - OneDrive treats HTTP 404 as confirmed absence.
    - OneDrive preserves non-404 HTTP failures.
    - OneNote validates a Container present in a complete observation.
    - OneNote confirms absence only after complete enumeration.
    - OneNote rejects incomplete enumeration as authoritative evidence.
    - Required identities are validated.

Does NOT:
    - Authenticate with Microsoft Graph.
    - Access live Sources of Truth.
    - Modify the AlphaOmega database.
    - Determine synchronization conflicts.
    - Reserve or execute synchronization.
"""

from unittest.mock import patch

import requests

from scripts.connectors.source_container_validator import (
    SourceContainerValidator,
)

from scripts.connectors.ms_graph.onedrive_container_validator import (
    OneDriveContainerValidator,
)

from scripts.connectors.ms_graph.onenote_container_validator import (
    OneNoteContainerValidator,
)


ONEDRIVE_OBJECT_ID = "onedrive-folder-123"
ONENOTE_OBJECT_ID = "onenote-section-456"


class FakeResponse:
    """
    Minimal Microsoft Graph response.
    """

    def __init__(
        self,
        *,
        data=None,
        status_code=200,
    ):
        self._data = (
            data
            if data is not None
            else {}
        )

        self.status_code = status_code

    def json(
        self,
    ):
        return self._data


class FakeOneNoteEnumerator:
    """
    Provide deterministic OneNote observations.
    """

    def __init__(
        self,
        observation,
    ):
        self.observation = observation
        self.calls = 0

    def enumerate(
        self,
    ):
        self.calls += 1

        return self.observation


class FakeValidator:
    """
    Verify generic Source routing independently.
    """

    def __init__(
        self,
        source_name,
    ):
        self.source_name = source_name
        self.requests = []

    def validate(
        self,
        *,
        source_object_id,
    ):
        self.requests.append(
            source_object_id
        )

        return {
            "exists":
                True,

            "source_name":
                self.source_name,

            "source_object_id":
                source_object_id,
        }


def require_equal(
    *,
    actual,
    expected,
    test_name,
):
    """
    Require one deterministic result.
    """

    if actual != expected:
        raise RuntimeError(
            f"{test_name} failed. "
            f"Expected {expected}, "
            f"received {actual}."
        )

    print(
        f"PASS: {test_name}"
    )


def test_generic_routing():
    """
    Verify the generic validator routes without Source-specific knowledge.
    """

    onedrive = FakeValidator(
        "onedrive"
    )

    onenote = FakeValidator(
        "onenote"
    )

    validator = (
        SourceContainerValidator(
            {
                "onedrive":
                    onedrive,

                "onenote":
                    onenote,
            }
        )
    )

    result = validator.validate(
        source_name="OneDrive",
        source_object_id=(
            ONEDRIVE_OBJECT_ID
        ),
    )

    require_equal(
        actual=result[
            "source_name"
        ],
        expected="onedrive",
        test_name=(
            "Generic validator routes by normalized Source name"
        ),
    )

    require_equal(
        actual=tuple(
            onedrive.requests
        ),
        expected=(
            ONEDRIVE_OBJECT_ID,
        ),
        test_name=(
            "OneDrive request reaches only OneDrive validator"
        ),
    )

    require_equal(
        actual=tuple(
            onenote.requests
        ),
        expected=(),
        test_name=(
            "OneDrive request does not reach OneNote validator"
        ),
    )


def test_unsupported_source():
    """
    Verify an unregistered Source is rejected.
    """

    validator = (
        SourceContainerValidator(
            {}
        )
    )

    try:

        validator.validate(
            source_name="future-source",
            source_object_id="object-1",
        )

    except ValueError:

        print(
            "PASS: Unregistered Source is rejected"
        )

        return

    raise RuntimeError(
        "Unregistered Source did not raise ValueError."
    )


def test_onedrive_existing_folder():
    """
    Verify direct OneDrive folder validation.
    """

    validator = (
        OneDriveContainerValidator()
    )

    response = FakeResponse(
        data={
            "id":
                ONEDRIVE_OBJECT_ID,

            "name":
                "Example Folder",

            "folder":
                {},
        }
    )

    with patch(
        "scripts.connectors.ms_graph."
        "onedrive_container_validator.graph_get",
        return_value=response,
    ) as graph_get_mock:

        result = validator.validate(
            source_object_id=(
                ONEDRIVE_OBJECT_ID
            )
        )

    require_equal(
        actual=result[
            "exists"
        ],
        expected=True,
        test_name=(
            "Existing OneDrive folder validates"
        ),
    )

    require_equal(
        actual=graph_get_mock.call_args.args[
            0
        ],
        expected=(
            "/me/drive/items/"
            f"{ONEDRIVE_OBJECT_ID}"
        ),
        test_name=(
            "OneDrive uses direct Graph object lookup"
        ),
    )


def test_onedrive_non_folder():
    """
    Verify a OneDrive file is not a valid Source Container.
    """

    validator = (
        OneDriveContainerValidator()
    )

    response = FakeResponse(
        data={
            "id":
                ONEDRIVE_OBJECT_ID,

            "name":
                "Example.docx",

            "file":
                {},
        }
    )

    with patch(
        "scripts.connectors.ms_graph."
        "onedrive_container_validator.graph_get",
        return_value=response,
    ):

        result = validator.validate(
            source_object_id=(
                ONEDRIVE_OBJECT_ID
            )
        )

    require_equal(
        actual=result[
            "exists"
        ],
        expected=False,
        test_name=(
            "OneDrive file is rejected as Container"
        ),
    )


def test_onedrive_404():
    """
    Verify HTTP 404 confirms absence.
    """

    validator = (
        OneDriveContainerValidator()
    )

    response = FakeResponse(
        status_code=404
    )

    exception = requests.HTTPError(
        "404 Not Found",
        response=response,
    )

    with patch(
        "scripts.connectors.ms_graph."
        "onedrive_container_validator.graph_get",
        side_effect=exception,
    ):

        result = validator.validate(
            source_object_id=(
                ONEDRIVE_OBJECT_ID
            )
        )

    require_equal(
        actual=result[
            "exists"
        ],
        expected=False,
        test_name=(
            "OneDrive HTTP 404 confirms absence"
        ),
    )


def test_onedrive_non_404_failure():
    """
    Verify other Graph failures remain failures.
    """

    validator = (
        OneDriveContainerValidator()
    )

    response = FakeResponse(
        status_code=403
    )

    exception = requests.HTTPError(
        "403 Forbidden",
        response=response,
    )

    try:

        with patch(
            "scripts.connectors.ms_graph."
            "onedrive_container_validator.graph_get",
            side_effect=exception,
        ):

            validator.validate(
                source_object_id=(
                    ONEDRIVE_OBJECT_ID
                )
            )

    except requests.HTTPError:

        print(
            "PASS: OneDrive non-404 HTTP failure remains a failure"
        )

        return

    raise RuntimeError(
        "OneDrive non-404 failure was treated as absence."
    )


def test_onenote_existing_container():
    """
    Verify a Container present in complete observation exists.
    """

    enumerator = FakeOneNoteEnumerator(
        {
            "containers": [
                {
                    "source_object_id":
                        ONENOTE_OBJECT_ID,

                    "parent_source_object_id":
                        "notebook-1",

                    "name":
                        "Example Section",
                },
            ],

            "enumeration_complete":
                True,
        }
    )

    validator = (
        OneNoteContainerValidator(
            enumerator=enumerator
        )
    )

    result = validator.validate(
        source_object_id=(
            ONENOTE_OBJECT_ID
        )
    )

    require_equal(
        actual=result[
            "exists"
        ],
        expected=True,
        test_name=(
            "Existing OneNote Container validates"
        ),
    )

    require_equal(
        actual=enumerator.calls,
        expected=1,
        test_name=(
            "OneNote validation performs one observation"
        ),
    )


def test_onenote_missing_container():
    """
    Verify complete observation can establish absence.
    """

    enumerator = FakeOneNoteEnumerator(
        {
            "containers": [],
            "enumeration_complete":
                True,
        }
    )

    validator = (
        OneNoteContainerValidator(
            enumerator=enumerator
        )
    )

    result = validator.validate(
        source_object_id=(
            ONENOTE_OBJECT_ID
        )
    )

    require_equal(
        actual=result[
            "exists"
        ],
        expected=False,
        test_name=(
            "Complete OneNote observation confirms absence"
        ),
    )


def test_onenote_incomplete_observation():
    """
    Verify incomplete observation cannot establish absence.
    """

    enumerator = FakeOneNoteEnumerator(
        {
            "containers": [],
            "enumeration_complete":
                False,
        }
    )

    validator = (
        OneNoteContainerValidator(
            enumerator=enumerator
        )
    )

    try:

        validator.validate(
            source_object_id=(
                ONENOTE_OBJECT_ID
            )
        )

    except RuntimeError:

        print(
            "PASS: Incomplete OneNote observation cannot prove absence"
        )

        return

    raise RuntimeError(
        "Incomplete OneNote observation was accepted."
    )


def test_required_identity_validation():
    """
    Verify generic request identities are required.
    """

    validator = (
        SourceContainerValidator(
            {
                "onedrive":
                    FakeValidator(
                        "onedrive"
                    ),
            }
        )
    )

    try:

        validator.validate(
            source_name=None,
            source_object_id="object-1",
        )

    except ValueError:

        print(
            "PASS: Missing source_name is rejected"
        )

    else:

        raise RuntimeError(
            "Missing source_name did not raise ValueError."
        )

    try:

        validator.validate(
            source_name="onedrive",
            source_object_id=None,
        )

    except ValueError:

        print(
            "PASS: Missing source_object_id is rejected"
        )

    else:

        raise RuntimeError(
            "Missing source_object_id did not raise ValueError."
        )


def main():

    print()
    print(
        "AlphaOmega Source Container Validator Test"
    )
    print(
        "=========================================="
    )
    print()

    test_generic_routing()
    test_unsupported_source()

    test_onedrive_existing_folder()
    test_onedrive_non_folder()
    test_onedrive_404()
    test_onedrive_non_404_failure()

    test_onenote_existing_container()
    test_onenote_missing_container()
    test_onenote_incomplete_observation()

    test_required_identity_validation()

    print()
    print(
        "SOURCE CONTAINER VALIDATOR TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()