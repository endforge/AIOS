"""
Synchronization Conflict Service Test

Purpose:
    Performs an isolated deterministic test of application-level
    synchronization conflict evaluation.

Verifies:
    - Active synchronization scopes are read for the requested Source.
    - The active Source Container catalog is supplied to conflict detection.
    - Overlapping active synchronization scopes are returned.
    - Disjoint synchronization scopes return no conflicts.
    - No active Synchronization Runs short-circuit catalog loading.
    - Boolean conflict evaluation reflects the returned conflict state.
    - Required request identities are validated.

Does NOT:
    - Access the AlphaOmega database.
    - Access a Source of Truth.
    - Detect Source Container Refresh conflicts.
    - Create Processing Jobs or Synchronization Runs.
    - Reserve synchronization execution.
    - Execute synchronization.
"""

from scripts.application.synchronization_conflict_service import (
    SynchronizationConflictService,
)

from scripts.application.synchronization_scope_conflict_detector import (
    SynchronizationScopeConflictDetector,
)


SOURCE_ID = "source-a"

ROOT = "container-root"
BRANCH_A = "container-branch-a"
CHILD_A = "container-child-a"
BRANCH_B = "container-branch-b"


SOURCE_CONTAINERS = (
    {
        "id": ROOT,
        "source_id": SOURCE_ID,
        "source_object_id": "root",
        "parent_source_object_id": None,
        "name": "Root",
    },
    {
        "id": BRANCH_A,
        "source_id": SOURCE_ID,
        "source_object_id": "branch-a",
        "parent_source_object_id": "root",
        "name": "Branch A",
    },
    {
        "id": CHILD_A,
        "source_id": SOURCE_ID,
        "source_object_id": "child-a",
        "parent_source_object_id": "branch-a",
        "name": "Child A",
    },
    {
        "id": BRANCH_B,
        "source_id": SOURCE_ID,
        "source_object_id": "branch-b",
        "parent_source_object_id": "root",
        "name": "Branch B",
    },
)


class FakeSyncRunRepository:
    """
    Provide deterministic active synchronization scope.
    """

    def __init__(
        self,
        active_source_container_ids,
    ):
        self.active_source_container_ids = tuple(
            active_source_container_ids
        )

        self.requested_source_ids = []

    def find_active_source_container_ids_by_source(
        self,
        source_id,
    ):
        self.requested_source_ids.append(
            source_id
        )

        return self.active_source_container_ids


class FakeSourceContainerRepository:
    """
    Provide deterministic persisted Source Container hierarchy.
    """

    def __init__(
        self,
        source_containers,
    ):
        self.source_containers = tuple(
            source_containers
        )

        self.requested_source_ids = []

    def find_active_by_source(
        self,
        source_id,
    ):
        self.requested_source_ids.append(
            source_id
        )

        return self.source_containers


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


def build_service(
    active_source_container_ids,
):
    """
    Build the application service with isolated dependencies.
    """

    sync_run_repository = (
        FakeSyncRunRepository(
            active_source_container_ids
        )
    )

    source_container_repository = (
        FakeSourceContainerRepository(
            SOURCE_CONTAINERS
        )
    )

    service = (
        SynchronizationConflictService(
            sync_run_repository=(
                sync_run_repository
            ),
            source_container_repository=(
                source_container_repository
            ),
            scope_conflict_detector=(
                SynchronizationScopeConflictDetector()
            ),
        )
    )

    return (
        service,
        sync_run_repository,
        source_container_repository,
    )


def test_overlapping_scope():
    """
    Verify an active ancestor conflicts with a descendant request.
    """

    (
        service,
        sync_run_repository,
        source_container_repository,
    ) = build_service(
        (
            BRANCH_A,
        )
    )

    result = service.find_conflicts(
        source_id=SOURCE_ID,
        source_container_id=CHILD_A,
    )

    require_equal(
        actual=result,
        expected=(
            BRANCH_A,
        ),
        test_name=(
            "Active ancestor conflict is returned"
        ),
    )

    require_equal(
        actual=tuple(
            sync_run_repository
            .requested_source_ids
        ),
        expected=(
            SOURCE_ID,
        ),
        test_name=(
            "Active Synchronization Runs are read by Source"
        ),
    )

    require_equal(
        actual=tuple(
            source_container_repository
            .requested_source_ids
        ),
        expected=(
            SOURCE_ID,
        ),
        test_name=(
            "Source Container hierarchy is read by Source"
        ),
    )


def test_disjoint_scope():
    """
    Verify sibling scopes do not conflict.
    """

    (
        service,
        _sync_run_repository,
        _source_container_repository,
    ) = build_service(
        (
            BRANCH_B,
        )
    )

    result = service.find_conflicts(
        source_id=SOURCE_ID,
        source_container_id=BRANCH_A,
    )

    require_equal(
        actual=result,
        expected=(),
        test_name=(
            "Disjoint synchronization scope is allowed"
        ),
    )


def test_no_active_runs():
    """
    Verify no active runs avoid unnecessary catalog loading.
    """

    (
        service,
        _sync_run_repository,
        source_container_repository,
    ) = build_service(
        ()
    )

    result = service.find_conflicts(
        source_id=SOURCE_ID,
        source_container_id=BRANCH_A,
    )

    require_equal(
        actual=result,
        expected=(),
        test_name=(
            "No active Synchronization Runs returns no conflicts"
        ),
    )

    require_equal(
        actual=tuple(
            source_container_repository
            .requested_source_ids
        ),
        expected=(),
        test_name=(
            "Catalog lookup is skipped when no active runs exist"
        ),
    )


def test_boolean_conflict_result():
    """
    Verify convenience boolean evaluation.
    """

    (
        conflict_service,
        _sync_run_repository,
        _source_container_repository,
    ) = build_service(
        (
            ROOT,
        )
    )

    require_equal(
        actual=conflict_service.has_conflict(
            source_id=SOURCE_ID,
            source_container_id=CHILD_A,
        ),
        expected=True,
        test_name=(
            "Boolean conflict result is True for overlap"
        ),
    )

    (
        clear_service,
        _sync_run_repository,
        _source_container_repository,
    ) = build_service(
        (
            BRANCH_B,
        )
    )

    require_equal(
        actual=clear_service.has_conflict(
            source_id=SOURCE_ID,
            source_container_id=BRANCH_A,
        ),
        expected=False,
        test_name=(
            "Boolean conflict result is False for disjoint scope"
        ),
    )


def test_required_identity_validation():
    """
    Verify both request identities are required.
    """

    (
        service,
        _sync_run_repository,
        _source_container_repository,
    ) = build_service(
        ()
    )

    try:

        service.find_conflicts(
            source_id=None,
            source_container_id=BRANCH_A,
        )

    except ValueError:

        print(
            "PASS: Missing source_id is rejected"
        )

    else:

        raise RuntimeError(
            "Missing source_id did not raise ValueError."
        )

    try:

        service.find_conflicts(
            source_id=SOURCE_ID,
            source_container_id=None,
        )

    except ValueError:

        print(
            "PASS: Missing source_container_id is rejected"
        )

    else:

        raise RuntimeError(
            "Missing source_container_id did not raise ValueError."
        )


def main():

    print()
    print(
        "AlphaOmega Synchronization Conflict Service Test"
    )
    print(
        "================================================"
    )
    print()

    test_overlapping_scope()
    test_disjoint_scope()
    test_no_active_runs()
    test_boolean_conflict_result()
    test_required_identity_validation()

    print()
    print(
        "SYNCHRONIZATION CONFLICT SERVICE TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()