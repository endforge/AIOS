"""
AlphaOmega Synchronization Application Service Test

Purpose:
    Verifies the assembled application-level synchronization coordination
    boundary without accessing Microsoft Graph or creating real
    synchronization operations.

Verifies:
    - Persisted admission occurs first.
    - Preliminary conflict evaluation occurs after admission.
    - Source-of-Truth validation occurs after preliminary conflict approval.
    - Execution occurs only after successful validation.
    - Admitted identities are passed correctly to execution.
    - Entire OneNote is permitted through the Source Root.
    - Entire OneDrive is rejected through the normal application path.
    - Preliminary conflicts stop processing before Source validation.
    - Missing Source-of-Truth Containers stop processing before execution.

Does NOT:
    - Access Microsoft Graph.
    - Access Supabase.
    - Create Processing Jobs.
    - Create Synchronization Runs.
    - Execute Connector, Translator, Discovery, Extraction, or Load.
"""

from scripts.application.synchronization_application_service import (
    SynchronizationApplicationService,
)
from scripts.sync.source_container_root_service import (
    SourceContainerRootService,
)


SOURCE_ROOT = (
    SourceContainerRootService
    .ROOT_SOURCE_OBJECT_ID
)


class FakeRequest:
    def __init__(
        self,
        *,
        source_id,
        source_container_id,
    ):
        self.source_id = source_id
        self.source_container_id = (
            source_container_id
        )


class FakeAdmissionService:
    def __init__(
        self,
        *,
        result,
        events,
    ):
        self._result = result
        self._events = events

    def validate(
        self,
        request,
    ):
        self._events.append(
            "admission"
        )

        return dict(
            self._result
        )


class FakePreliminaryConflictService:
    def __init__(
        self,
        *,
        result,
        events,
    ):
        self._result = result
        self._events = events

    def evaluate(
        self,
        *,
        source_id,
        source_container_id,
    ):
        self._events.append(
            "preliminary_conflict"
        )

        return dict(
            self._result
        )


class FakeSourceContainerValidator:
    def __init__(
        self,
        *,
        result,
        events,
    ):
        self._result = result
        self._events = events

        self.calls = []

    def validate(
        self,
        *,
        source_name,
        source_object_id,
    ):
        self._events.append(
            "source_validation"
        )

        self.calls.append(
            {
                "source_name":
                    source_name,

                "source_object_id":
                    source_object_id,
            }
        )

        result = dict(
            self._result
        )

        result.setdefault(
            "source_name",
            source_name,
        )

        result.setdefault(
            "source_object_id",
            source_object_id,
        )

        return result


class FakeExecutionService:
    def __init__(
        self,
        *,
        events,
    ):
        self._events = events
        self.calls = []

    def execute(
        self,
        *,
        source_name,
        source_id,
        source_container_id,
        source_object_id,
        metadata=None,
    ):
        self._events.append(
            "execution"
        )

        call = {
            "source_name":
                source_name,

            "source_id":
                source_id,

            "source_container_id":
                source_container_id,

            "source_object_id":
                source_object_id,

            "metadata":
                metadata,
        }

        self.calls.append(
            call
        )

        return {
            "processing_job_id":
                "processing-job-1",

            "sync_run_id":
                "sync-run-1",

            "source_id":
                source_id,

            "source_container_id":
                source_container_id,

            "source_object_id":
                source_object_id,
        }


def build_service(
    *,
    source_name,
    source_object_id,
    conflict_allowed=True,
    source_exists=True,
):
    events = []

    admission = (
        FakeAdmissionService(
            result={
                "source_id":
                    "source-1",

                "source_container_id":
                    "container-1",

                "source_name":
                    source_name,

                "source_object_id":
                    source_object_id,

                "container_name":
                    "Test Container",
            },
            events=events,
        )
    )

    conflict = (
        FakePreliminaryConflictService(
            result={
                "allowed":
                    conflict_allowed,

                "conflict_type":
                    (
                        None
                        if conflict_allowed
                        else "synchronization_scope"
                    ),

                "conflicting_source_container_ids":
                    (
                        ()
                        if conflict_allowed
                        else ("container-2",)
                    ),
            },
            events=events,
        )
    )

    validator = (
        FakeSourceContainerValidator(
            result={
                "exists":
                    source_exists,
            },
            events=events,
        )
    )

    execution = (
        FakeExecutionService(
            events=events
        )
    )

    service = (
        SynchronizationApplicationService(
            admission_service=admission,
            preliminary_conflict_service=(
                conflict
            ),
            source_container_validator=(
                validator
            ),
            execution_service=execution,
        )
    )

    return (
        service,
        events,
        validator,
        execution,
    )


def test_selected_onedrive():
    (
        service,
        events,
        validator,
        execution,
    ) = build_service(
        source_name="OneDrive",
        source_object_id="graph-folder-1",
    )

    request = FakeRequest(
        source_id="source-1",
        source_container_id="container-1",
    )

    result = service.execute(
        request,
        metadata={
            "test":
                "selected_onedrive"
        },
    )

    assert events == [
        "admission",
        "preliminary_conflict",
        "source_validation",
        "execution",
    ]

    assert (
        validator.calls[0][
            "source_object_id"
        ]
        == "graph-folder-1"
    )

    assert (
        execution.calls[0][
            "source_object_id"
        ]
        == "graph-folder-1"
    )

    assert (
        result[
            "is_source_root"
        ]
        is False
    )


def test_selected_onenote():
    (
        service,
        events,
        validator,
        execution,
    ) = build_service(
        source_name="OneNote",
        source_object_id="graph-section-1",
    )

    request = FakeRequest(
        source_id="source-1",
        source_container_id="container-1",
    )

    result = service.execute(
        request
    )

    assert events == [
        "admission",
        "preliminary_conflict",
        "source_validation",
        "execution",
    ]

    assert (
        result[
            "is_source_root"
        ]
        is False
    )


def test_entire_onenote():
    (
        service,
        events,
        validator,
        execution,
    ) = build_service(
        source_name="OneNote",
        source_object_id=SOURCE_ROOT,
    )

    request = FakeRequest(
        source_id="source-1",
        source_container_id="container-1",
    )

    result = service.execute(
        request
    )

    assert events == [
        "admission",
        "preliminary_conflict",
        "source_validation",
        "execution",
    ]

    assert (
        validator.calls[0][
            "source_object_id"
        ]
        == SOURCE_ROOT
    )

    assert (
        execution.calls[0][
            "source_object_id"
        ]
        == SOURCE_ROOT
    )

    assert (
        result[
            "is_source_root"
        ]
        is True
    )


def test_entire_onedrive_rejected():
    (
        service,
        events,
        validator,
        execution,
    ) = build_service(
        source_name="OneDrive",
        source_object_id=SOURCE_ROOT,
    )

    request = FakeRequest(
        source_id="source-1",
        source_container_id="container-1",
    )

    try:

        service.execute(
            request
        )

    except ValueError as error:

        assert (
            "Entire OneDrive"
            in str(
                error
            )
        )

    else:

        raise AssertionError(
            "Entire OneDrive was not rejected."
        )

    assert events == [
        "admission",
    ]

    assert not validator.calls
    assert not execution.calls


def test_preliminary_conflict_rejected():
    (
        service,
        events,
        validator,
        execution,
    ) = build_service(
        source_name="OneDrive",
        source_object_id="graph-folder-1",
        conflict_allowed=False,
    )

    request = FakeRequest(
        source_id="source-1",
        source_container_id="container-1",
    )

    try:

        service.execute(
            request
        )

    except RuntimeError as error:

        assert (
            "conflict"
            in str(
                error
            ).lower()
        )

    else:

        raise AssertionError(
            "Preliminary conflict was not rejected."
        )

    assert events == [
        "admission",
        "preliminary_conflict",
    ]

    assert not validator.calls
    assert not execution.calls


def test_missing_source_container_rejected():
    (
        service,
        events,
        validator,
        execution,
    ) = build_service(
        source_name="OneNote",
        source_object_id="graph-section-1",
        source_exists=False,
    )

    request = FakeRequest(
        source_id="source-1",
        source_container_id="container-1",
    )

    try:

        service.execute(
            request
        )

    except RuntimeError as error:

        assert (
            "no longer exists"
            in str(
                error
            )
        )

    else:

        raise AssertionError(
            "Missing Source Container was not rejected."
        )

    assert events == [
        "admission",
        "preliminary_conflict",
        "source_validation",
    ]

    assert not execution.calls


def run_test(
    name,
    function,
):
    try:

        function()

        print(
            f"PASS: {name}"
        )

    except Exception:

        print(
            f"FAIL: {name}"
        )

        raise


def main():
    print()
    print(
        "=" * 60
    )
    print(
        "AlphaOmega Synchronization Application Service Test"
    )
    print(
        "=" * 60
    )
    print()

    tests = [
        (
            "Selected OneDrive Container",
            test_selected_onedrive,
        ),
        (
            "Selected OneNote Container",
            test_selected_onenote,
        ),
        (
            "Entire OneNote Source Root",
            test_entire_onenote,
        ),
        (
            "Entire OneDrive Rejected",
            test_entire_onedrive_rejected,
        ),
        (
            "Preliminary Conflict Rejected",
            test_preliminary_conflict_rejected,
        ),
        (
            "Missing Source Container Rejected",
            test_missing_source_container_rejected,
        ),
    ]

    for name, function in tests:

        run_test(
            name,
            function,
        )

    print()
    print(
        "=" * 60
    )
    print(
        "SYNCHRONIZATION APPLICATION SERVICE TEST: PASS"
    )
    print(
        "=" * 60
    )


if __name__ == "__main__":
    main()