"""
Synchronization Preliminary Conflict Service Test

Purpose:
    Performs isolated deterministic tests of complete preliminary
    synchronization conflict evaluation.

Verifies:
    - A running Source Container Refresh blocks synchronization.
    - Refresh conflict takes precedence over synchronization scope lookup.
    - An overlapping running synchronization blocks synchronization.
    - A disjoint running synchronization does not block synchronization.
    - No persisted conflicts allow progression to later admission stages.
    - Conflict results identify the reason for rejection.
    - Required request identities are validated.

Does NOT:
    - Access the AlphaOmega database.
    - Access a Source of Truth.
    - Perform persisted synchronization identity admission.
    - Guarantee authoritative concurrency reservation.
    - Create Processing Jobs or Synchronization Runs.
    - Execute synchronization.
"""


from scripts.application.synchronization_preliminary_conflict_service import (
    SynchronizationPreliminaryConflictService,
)


SOURCE_ID = "source-a"
REQUESTED_CONTAINER = "container-requested"
CONFLICTING_CONTAINER = "container-conflicting"


class FakeRefreshStatusRepository:
    """
    Provide deterministic whole-Source Refresh state.
    """

    def __init__(
        self,
        active,
    ):
        self.active = active
        self.requested_source_ids = []

    def has_active_refresh(
        self,
        source_id,
    ):
        self.requested_source_ids.append(
            source_id
        )

        return self.active


class FakeSynchronizationConflictService:
    """
    Provide deterministic synchronization scope conflict state.
    """

    def __init__(
        self,
        conflicts,
    ):
        self.conflicts = tuple(
            conflicts
        )

        self.requests = []

    def find_conflicts(
        self,
        *,
        source_id,
        source_container_id,
    ):
        self.requests.append(
            (
                source_id,
                source_container_id,
            )
        )

        return self.conflicts


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


def build_service(
    *,
    refresh_active,
    synchronization_conflicts,
):
    """
    Build the preliminary conflict service with isolated dependencies.
    """

    refresh_repository = (
        FakeRefreshStatusRepository(
            refresh_active
        )
    )

    synchronization_conflict_service = (
        FakeSynchronizationConflictService(
            synchronization_conflicts
        )
    )

    service = (
        SynchronizationPreliminaryConflictService(
            refresh_status_repository=(
                refresh_repository
            ),
            synchronization_conflict_service=(
                synchronization_conflict_service
            ),
        )
    )

    return (
        service,
        refresh_repository,
        synchronization_conflict_service,
    )


def test_refresh_blocks_synchronization():
    """
    Verify whole-Source Refresh blocks every synchronization scope.
    """

    (
        service,
        refresh_repository,
        synchronization_conflict_service,
    ) = build_service(
        refresh_active=True,
        synchronization_conflicts=(
            CONFLICTING_CONTAINER,
        ),
    )

    result = service.evaluate(
        source_id=SOURCE_ID,
        source_container_id=(
            REQUESTED_CONTAINER
        ),
    )

    require_equal(
        actual=result,
        expected={
            "allowed":
                False,

            "conflict_type":
                "source_container_refresh",

            "conflicting_source_container_ids":
                (),
        },
        test_name=(
            "Running Source Refresh blocks synchronization"
        ),
    )

    require_equal(
        actual=tuple(
            refresh_repository
            .requested_source_ids
        ),
        expected=(
            SOURCE_ID,
        ),
        test_name=(
            "Refresh state is checked for requested Source"
        ),
    )

    require_equal(
        actual=tuple(
            synchronization_conflict_service
            .requests
        ),
        expected=(),
        test_name=(
            "Synchronization conflict lookup is skipped after Refresh conflict"
        ),
    )


def test_overlapping_sync_blocks_synchronization():
    """
    Verify overlapping active synchronization scope blocks the request.
    """

    (
        service,
        _refresh_repository,
        synchronization_conflict_service,
    ) = build_service(
        refresh_active=False,
        synchronization_conflicts=(
            CONFLICTING_CONTAINER,
        ),
    )

    result = service.evaluate(
        source_id=SOURCE_ID,
        source_container_id=(
            REQUESTED_CONTAINER
        ),
    )

    require_equal(
        actual=result,
        expected={
            "allowed":
                False,

            "conflict_type":
                "synchronization_scope",

            "conflicting_source_container_ids":
                (
                    CONFLICTING_CONTAINER,
                ),
        },
        test_name=(
            "Overlapping synchronization scope blocks request"
        ),
    )

    require_equal(
        actual=tuple(
            synchronization_conflict_service
            .requests
        ),
        expected=(
            (
                SOURCE_ID,
                REQUESTED_CONTAINER,
            ),
        ),
        test_name=(
            "Synchronization conflict lookup receives admitted scope"
        ),
    )


def test_disjoint_sync_allows_progression():
    """
    Verify a clear synchronization conflict result allows progression.
    """

    (
        service,
        _refresh_repository,
        _synchronization_conflict_service,
    ) = build_service(
        refresh_active=False,
        synchronization_conflicts=(),
    )

    result = service.evaluate(
        source_id=SOURCE_ID,
        source_container_id=(
            REQUESTED_CONTAINER
        ),
    )

    require_equal(
        actual=result,
        expected={
            "allowed":
                True,

            "conflict_type":
                None,

            "conflicting_source_container_ids":
                (),
        },
        test_name=(
            "No persisted conflicts allows progression"
        ),
    )


def test_required_identity_validation():
    """
    Verify request identities are required.
    """

    (
        service,
        _refresh_repository,
        _synchronization_conflict_service,
    ) = build_service(
        refresh_active=False,
        synchronization_conflicts=(),
    )

    try:

        service.evaluate(
            source_id=None,
            source_container_id=(
                REQUESTED_CONTAINER
            ),
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

        service.evaluate(
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
        "AlphaOmega Synchronization Preliminary Conflict Test"
    )
    print(
        "===================================================="
    )
    print()

    test_refresh_blocks_synchronization()
    test_overlapping_sync_blocks_synchronization()
    test_disjoint_sync_allows_progression()
    test_required_identity_validation()

    print()
    print(
        "SYNCHRONIZATION PRELIMINARY CONFLICT TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()