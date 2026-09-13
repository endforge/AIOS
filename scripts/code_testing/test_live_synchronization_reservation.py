"""
Live Synchronization Reservation Test

Purpose:
    Validates the authoritative synchronization reservation boundary
    against the live AlphaOmega database.

Verifies:
    - A valid synchronization scope can be reserved.
    - Reservation creates one running Processing Job.
    - Reservation creates one Synchronization Run.
    - Same-Container synchronization is rejected while active.
    - An active ancestor blocks a descendant synchronization.
    - An active descendant blocks an ancestor synchronization.
    - Sibling synchronization scopes may run concurrently.
    - A running Source Container Refresh blocks synchronization.
    - Completed operations no longer block later synchronization.

Does NOT:
    - Connect to Microsoft Graph.
    - Enumerate OneDrive.
    - Read or synchronize OneDrive content.
    - Execute Connector, Translator, Discovery, Extraction, or Load.
    - Delete Processing Job or Synchronization Run history.
"""

from collections import defaultdict

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)

from scripts.database.processing_job_repository import (
    ProcessingJobRepository,
)

from scripts.database.source_repository import (
    SourceRepository,
)

from scripts.database.source_container_repository import (
    SourceContainerRepository,
)

from scripts.database.source_container_refresh_reservation_repository import (
    SourceContainerRefreshReservationRepository,
)

from scripts.database.synchronization_reservation_repository import (
    SynchronizationReservationRepository,
)


PIPELINE_VERSION = "lab8-live-reservation-test"

SYNC_METADATA = {
    "test":
        "live_synchronization_reservation",
}

REFRESH_METADATA = {
    "test":
        "live_synchronization_reservation_refresh_block",
}


def require(
    condition,
    message,
):
    """
    Require one test condition.
    """

    if not condition:
        raise RuntimeError(
            message
        )


def find_test_hierarchy(
    containers,
):
    """
    Find one parent having at least two active children.
    """

    by_object_id = {}

    children_by_parent = defaultdict(
        list
    )

    for container in containers:

        source_object_id = (
            container.get(
                "source_object_id"
            )
        )

        if source_object_id:

            by_object_id[
                source_object_id
            ] = container

    for container in containers:

        parent_object_id = (
            container.get(
                "parent_source_object_id"
            )
        )

        if (
            parent_object_id
            and parent_object_id
            in by_object_id
        ):

            children_by_parent[
                parent_object_id
            ].append(
                container
            )

    for (
        parent_object_id,
        children,
    ) in children_by_parent.items():

        if len(
            children
        ) >= 2:

            return (
                by_object_id[
                    parent_object_id
                ],
                children[0],
                children[1],
            )

    raise RuntimeError(
        "Could not find a parent Source Container "
        "with at least two active children."
    )


def reserve_sync(
    *,
    repository,
    source_id,
    source_container_id,
):
    """
    Reserve one synchronization scope.
    """

    return repository.reserve(
        source_id=source_id,
        source_container_id=(
            source_container_id
        ),
        pipeline_version=(
            PIPELINE_VERSION
        ),
        metadata=SYNC_METADATA,
    )


def expect_rejected(
    *,
    repository,
    source_id,
    source_container_id,
    name,
):
    """
    Require one reservation to be rejected.
    """

    try:

        reserve_sync(
            repository=repository,
            source_id=source_id,
            source_container_id=(
                source_container_id
            ),
        )

    except RuntimeError:

        print(
            f"PASS: {name}"
        )

        return

    raise RuntimeError(
        f"{name} failed. "
        "Reservation was admitted unexpectedly."
    )


def verify_processing_job(
    *,
    client,
    processing_job_id,
    source_id,
):
    """
    Verify the Processing Job created by reservation.
    """

    response = (
        client
        .table(
            "processing_jobs"
        )
        .select(
            "id,"
            "source_id,"
            "process_type,"
            "status,"
            "pipeline_version"
        )
        .eq(
            "id",
            processing_job_id,
        )
        .execute()
    )

    records = (
        response.data
        or []
    )

    require(
        len(
            records
        ) == 1,
        "Expected exactly one Processing Job.",
    )

    record = records[0]

    require(
        str(
            record.get(
                "source_id"
            )
        )
        == str(
            source_id
        ),
        "Processing Job Source ID does not match.",
    )

    require(
        record.get(
            "process_type"
        ) == "sync",
        "Processing Job process_type is not sync.",
    )

    require(
        record.get(
            "status"
        ) == "running",
        "Processing Job is not running.",
    )

    require(
        record.get(
            "pipeline_version"
        ) == PIPELINE_VERSION,
        "Processing Job pipeline version does not match.",
    )


def verify_sync_run(
    *,
    client,
    sync_run_id,
    processing_job_id,
    source_id,
    source_container_id,
):
    """
    Verify the Synchronization Run created by reservation.
    """

    response = (
        client
        .table(
            "sync_runs"
        )
        .select(
            "id,"
            "processing_job_id,"
            "source_id,"
            "source_container_id"
        )
        .eq(
            "id",
            sync_run_id,
        )
        .execute()
    )

    records = (
        response.data
        or []
    )

    require(
        len(
            records
        ) == 1,
        "Expected exactly one Synchronization Run.",
    )

    record = records[0]

    require(
        str(
            record.get(
                "processing_job_id"
            )
        )
        == str(
            processing_job_id
        ),
        "Synchronization Run Processing Job ID does not match.",
    )

    require(
        str(
            record.get(
                "source_id"
            )
        )
        == str(
            source_id
        ),
        "Synchronization Run Source ID does not match.",
    )

    require(
        str(
            record.get(
                "source_container_id"
            )
        )
        == str(
            source_container_id
        ),
        "Synchronization Run Source Container ID does not match.",
    )


def main():

    print()
    print(
        "AlphaOmega Live Synchronization Reservation Test"
    )
    print(
        "================================================="
    )
    print()

    credential_provider = (
        LocalCredentialProvider()
    )

    database_connection = (
        DatabaseConnection(
            credential_provider
        )
    )

    client = (
        database_connection.connect()
    )

    source_repository = (
        SourceRepository(
            client
        )
    )

    source_container_repository = (
        SourceContainerRepository(
            database_connection
        )
    )

    processing_job_repository = (
        ProcessingJobRepository(
            client
        )
    )

    sync_reservation_repository = (
        SynchronizationReservationRepository(
            client
        )
    )

    refresh_reservation_repository = (
        SourceContainerRefreshReservationRepository(
            client
        )
    )

    # Exact canonical Source name.
    source_id = (
        source_repository.find_id_by_name(
            "OneDrive"
        )
    )

    require(
        source_id is not None,
        "Registered OneDrive Source was not found.",
    )

    containers = (
        source_container_repository
        .find_active_by_source(
            source_id
        )
    )

    require(
        len(
            containers
        ) > 0,
        "No active OneDrive Source Containers were found.",
    )

    (
        parent,
        first_child,
        second_child,
    ) = find_test_hierarchy(
        containers
    )

    parent_id = str(
        parent[
            "id"
        ]
    )

    first_child_id = str(
        first_child[
            "id"
        ]
    )

    second_child_id = str(
        second_child[
            "id"
        ]
    )

    print(
        f"Source: OneDrive"
    )

    print(
        f"Source ID: {source_id}"
    )

    print(
        "Test hierarchy:"
    )

    print(
        "  Parent: "
        f"{parent.get('name')} "
        f"({parent_id})"
    )

    print(
        "  Child 1: "
        f"{first_child.get('name')} "
        f"({first_child_id})"
    )

    print(
        "  Child 2: "
        f"{second_child.get('name')} "
        f"({second_child_id})"
    )

    print()

    # ---------------------------------------------------------
    # 1. Successful reservation
    # ---------------------------------------------------------

    first_result = (
        reserve_sync(
            repository=(
                sync_reservation_repository
            ),
            source_id=source_id,
            source_container_id=(
                first_child_id
            ),
        )
    )

    verify_processing_job(
        client=client,
        processing_job_id=(
            first_result[
                "processing_job_id"
            ]
        ),
        source_id=source_id,
    )

    verify_sync_run(
        client=client,
        sync_run_id=(
            first_result[
                "sync_run_id"
            ]
        ),
        processing_job_id=(
            first_result[
                "processing_job_id"
            ]
        ),
        source_id=source_id,
        source_container_id=(
            first_child_id
        ),
    )

    print(
        "PASS: Successful synchronization reservation "
        "created Processing Job and Synchronization Run"
    )

    # ---------------------------------------------------------
    # 2. Same Container conflict
    # ---------------------------------------------------------

    expect_rejected(
        repository=(
            sync_reservation_repository
        ),
        source_id=source_id,
        source_container_id=(
            first_child_id
        ),
        name=(
            "Same Container synchronization rejected"
        ),
    )

    processing_job_repository.complete(
        first_result[
            "processing_job_id"
        ]
    )

    # ---------------------------------------------------------
    # 3. Active ancestor blocks descendant
    # ---------------------------------------------------------

    ancestor_result = (
        reserve_sync(
            repository=(
                sync_reservation_repository
            ),
            source_id=source_id,
            source_container_id=(
                parent_id
            ),
        )
    )

    expect_rejected(
        repository=(
            sync_reservation_repository
        ),
        source_id=source_id,
        source_container_id=(
            first_child_id
        ),
        name=(
            "Active ancestor blocks descendant synchronization"
        ),
    )

    processing_job_repository.complete(
        ancestor_result[
            "processing_job_id"
        ]
    )

    # ---------------------------------------------------------
    # 4. Active descendant blocks ancestor
    # ---------------------------------------------------------

    descendant_result = (
        reserve_sync(
            repository=(
                sync_reservation_repository
            ),
            source_id=source_id,
            source_container_id=(
                first_child_id
            ),
        )
    )

    expect_rejected(
        repository=(
            sync_reservation_repository
        ),
        source_id=source_id,
        source_container_id=(
            parent_id
        ),
        name=(
            "Active descendant blocks ancestor synchronization"
        ),
    )

    processing_job_repository.complete(
        descendant_result[
            "processing_job_id"
        ]
    )

    # ---------------------------------------------------------
    # 5. Sibling scopes may run concurrently
    # ---------------------------------------------------------

    sibling_one = (
        reserve_sync(
            repository=(
                sync_reservation_repository
            ),
            source_id=source_id,
            source_container_id=(
                first_child_id
            ),
        )
    )

    sibling_two = (
        reserve_sync(
            repository=(
                sync_reservation_repository
            ),
            source_id=source_id,
            source_container_id=(
                second_child_id
            ),
        )
    )

    require(
        sibling_one[
            "processing_job_id"
        ]
        != sibling_two[
            "processing_job_id"
        ],
        "Sibling reservations unexpectedly shared "
        "a Processing Job.",
    )

    print(
        "PASS: Sibling synchronization scopes "
        "admitted concurrently"
    )

    processing_job_repository.complete(
        sibling_one[
            "processing_job_id"
        ]
    )

    processing_job_repository.complete(
        sibling_two[
            "processing_job_id"
        ]
    )

    # ---------------------------------------------------------
    # 6. Refresh blocks synchronization
    # ---------------------------------------------------------

    refresh_job_id = (
        refresh_reservation_repository.reserve(
            source_id=source_id,
            process_type=(
                "source_container_refresh"
            ),
            pipeline_version=(
                PIPELINE_VERSION
            ),
            metadata=(
                REFRESH_METADATA
            ),
        )
    )

    expect_rejected(
        repository=(
            sync_reservation_repository
        ),
        source_id=source_id,
        source_container_id=(
            first_child_id
        ),
        name=(
            "Active Source Container Refresh "
            "blocks synchronization"
        ),
    )

    processing_job_repository.complete(
        refresh_job_id
    )

    # ---------------------------------------------------------
    # 7. Completed operation no longer blocks
    # ---------------------------------------------------------

    final_result = (
        reserve_sync(
            repository=(
                sync_reservation_repository
            ),
            source_id=source_id,
            source_container_id=(
                first_child_id
            ),
        )
    )

    print(
        "PASS: Completed operations no longer "
        "block synchronization"
    )

    processing_job_repository.complete(
        final_result[
            "processing_job_id"
        ]
    )

    print()
    print(
        "LIVE SYNCHRONIZATION RESERVATION TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()