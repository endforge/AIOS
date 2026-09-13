"""
Synchronization Scope Conflict Detector Test

Purpose:
    Performs an isolated deterministic test of synchronization scope
    overlap rules using representative Source Container hierarchy data.

Verifies:
    - The same Source Container conflicts with itself.
    - An active ancestor conflicts with a requested descendant.
    - An active descendant conflicts with a requested ancestor.
    - Sibling Source Containers do not conflict.
    - Disjoint Source Container branches do not conflict.
    - Containers belonging to another Source do not conflict.
    - Multiple active scopes return only the scopes that overlap.
    - Duplicate active scope identifiers do not duplicate conflicts.

Does NOT:
    - Access the AlphaOmega database.
    - Communicate with a Source of Truth.
    - Detect Source Container Refresh conflicts.
    - Create Processing Jobs or Synchronization Runs.
    - Reserve synchronization execution.
    - Execute synchronization.
"""

from scripts.application.synchronization_scope_conflict_detector import (
    SynchronizationScopeConflictDetector,
)


SOURCE_A = "source-a"
SOURCE_B = "source-b"

ROOT = "container-root"
BRANCH_A = "container-branch-a"
CHILD_A = "container-child-a"
BRANCH_B = "container-branch-b"
CHILD_B = "container-child-b"

OTHER_SOURCE_ROOT = "other-source-root"


SOURCE_CONTAINERS = (
    {
        "id":
            ROOT,

        "source_id":
            SOURCE_A,

        "source_object_id":
            "root",

        "parent_source_object_id":
            None,

        "name":
            "Root",
    },
    {
        "id":
            BRANCH_A,

        "source_id":
            SOURCE_A,

        "source_object_id":
            "branch-a",

        "parent_source_object_id":
            "root",

        "name":
            "Branch A",
    },
    {
        "id":
            CHILD_A,

        "source_id":
            SOURCE_A,

        "source_object_id":
            "child-a",

        "parent_source_object_id":
            "branch-a",

        "name":
            "Child A",
    },
    {
        "id":
            BRANCH_B,

        "source_id":
            SOURCE_A,

        "source_object_id":
            "branch-b",

        "parent_source_object_id":
            "root",

        "name":
            "Branch B",
    },
    {
        "id":
            CHILD_B,

        "source_id":
            SOURCE_A,

        "source_object_id":
            "child-b",

        "parent_source_object_id":
            "branch-b",

        "name":
            "Child B",
    },
    {
        "id":
            OTHER_SOURCE_ROOT,

        "source_id":
            SOURCE_B,

        "source_object_id":
            "root",

        "parent_source_object_id":
            None,

        "name":
            "Other Source Root",
    },
)


def require_equal(
    *,
    actual,
    expected,
    test_name,
):
    """
    Require one deterministic test result.
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


def main():

    print()
    print(
        "AlphaOmega Synchronization Scope Conflict Test"
    )
    print(
        "==============================================="
    )
    print()

    detector = (
        SynchronizationScopeConflictDetector()
    )

    # ---------------------------------------------------------
    # Same Container
    # ---------------------------------------------------------

    result = detector.find_conflicts(
        requested_source_container_id=(
            BRANCH_A
        ),
        active_source_container_ids=(
            BRANCH_A,
        ),
        source_containers=(
            SOURCE_CONTAINERS
        ),
    )

    require_equal(
        actual=result,
        expected=(
            BRANCH_A,
        ),
        test_name=(
            "Same Container conflicts"
        ),
    )

    # ---------------------------------------------------------
    # Active ancestor
    # ---------------------------------------------------------

    result = detector.find_conflicts(
        requested_source_container_id=(
            CHILD_A
        ),
        active_source_container_ids=(
            BRANCH_A,
        ),
        source_containers=(
            SOURCE_CONTAINERS
        ),
    )

    require_equal(
        actual=result,
        expected=(
            BRANCH_A,
        ),
        test_name=(
            "Ancestor conflicts with descendant request"
        ),
    )

    # ---------------------------------------------------------
    # Active descendant
    # ---------------------------------------------------------

    result = detector.find_conflicts(
        requested_source_container_id=(
            BRANCH_A
        ),
        active_source_container_ids=(
            CHILD_A,
        ),
        source_containers=(
            SOURCE_CONTAINERS
        ),
    )

    require_equal(
        actual=result,
        expected=(
            CHILD_A,
        ),
        test_name=(
            "Descendant conflicts with ancestor request"
        ),
    )

    # ---------------------------------------------------------
    # Sibling scopes
    # ---------------------------------------------------------

    result = detector.find_conflicts(
        requested_source_container_id=(
            BRANCH_A
        ),
        active_source_container_ids=(
            BRANCH_B,
        ),
        source_containers=(
            SOURCE_CONTAINERS
        ),
    )

    require_equal(
        actual=result,
        expected=(),
        test_name=(
            "Sibling scopes are allowed"
        ),
    )

    # ---------------------------------------------------------
    # Disjoint descendant branches
    # ---------------------------------------------------------

    result = detector.find_conflicts(
        requested_source_container_id=(
            CHILD_A
        ),
        active_source_container_ids=(
            CHILD_B,
        ),
        source_containers=(
            SOURCE_CONTAINERS
        ),
    )

    require_equal(
        actual=result,
        expected=(),
        test_name=(
            "Disjoint branches are allowed"
        ),
    )

    # ---------------------------------------------------------
    # Different Sources
    # ---------------------------------------------------------

    result = detector.find_conflicts(
        requested_source_container_id=(
            BRANCH_A
        ),
        active_source_container_ids=(
            OTHER_SOURCE_ROOT,
        ),
        source_containers=(
            SOURCE_CONTAINERS
        ),
    )

    require_equal(
        actual=result,
        expected=(),
        test_name=(
            "Different Sources do not conflict"
        ),
    )

    # ---------------------------------------------------------
    # Multiple active scopes
    # ---------------------------------------------------------

    result = detector.find_conflicts(
        requested_source_container_id=(
            CHILD_A
        ),
        active_source_container_ids=(
            ROOT,
            BRANCH_A,
            BRANCH_B,
            CHILD_B,
        ),
        source_containers=(
            SOURCE_CONTAINERS
        ),
    )

    require_equal(
        actual=result,
        expected=(
            ROOT,
            BRANCH_A,
        ),
        test_name=(
            "Only overlapping active scopes conflict"
        ),
    )

    # ---------------------------------------------------------
    # Duplicate active scope identifiers
    # ---------------------------------------------------------

    result = detector.find_conflicts(
        requested_source_container_id=(
            CHILD_A
        ),
        active_source_container_ids=(
            BRANCH_A,
            BRANCH_A,
        ),
        source_containers=(
            SOURCE_CONTAINERS
        ),
    )

    require_equal(
        actual=result,
        expected=(
            BRANCH_A,
        ),
        test_name=(
            "Duplicate active scopes produce one conflict"
        ),
    )

    print()
    print(
        "SYNCHRONIZATION SCOPE CONFLICT TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()