"""
Refresh every configured AlphaOmega Source Container catalog.

This application command runs one complete Source Container Refresh
for every Source registered in SOURCE_REFRESHES.

Each Source receives its own:

- Processing Job
- whole-Source reservation
- complete Source observation
- validation
- catalog reconciliation
- atomic persistence transaction
- completion or failure status

This command refreshes Source Container metadata only.

It does not:

- perform initial catalog population
- retrieve file or page content
- synchronize Knowledge Objects
- determine content synchronization scope
"""

from time import perf_counter

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)
from scripts.connectors.ms_graph.onedrive_container_enumerator import (
    OneDriveContainerEnumerator,
)
from scripts.connectors.ms_graph.onenote_container_enumerator import (
    OneNoteContainerEnumerator,
)
from scripts.database.database_connection import (
    DatabaseConnection,
)
from scripts.database.processing_job_repository import (
    ProcessingJobRepository,
)
from scripts.database.source_container_refresh_reservation_repository import (
    SourceContainerRefreshReservationRepository,
)
from scripts.database.source_container_repository import (
    SourceContainerRepository,
)
from scripts.database.source_repository import (
    SourceRepository,
)
from scripts.sync.source_container_observation_validator import (
    SourceContainerObservationValidator,
)
from scripts.sync.source_container_reconciler import (
    SourceContainerReconciler,
)
from scripts.sync.source_container_refresh_service import (
    SourceContainerRefreshService,
)


PROCESS_TYPE = "source_container_refresh"

PIPELINE_VERSION = (
    "lab8-production-source-container-refresh"
)


# -------------------------------------------------------------
# Source Container Refresh registry
#
# Adding another Source of Truth requires:
#
# 1. A compatible Container enumerator.
# 2. A registered Source database record.
# 3. An enumerator import above.
# 4. One entry in this registry.
#
# The shared Refresh workflow does not need to be rewritten.
# -------------------------------------------------------------

SOURCE_REFRESHES = (
    {
        "source_name":
            "OneDrive",

        "enumerator_factory":
            OneDriveContainerEnumerator,
    },
    {
        "source_name":
            "OneNote",

        "enumerator_factory":
            OneNoteContainerEnumerator,
    },
)


class ExistingDatabaseConnection:
    """
    Supply an existing authenticated database client to repositories
    that accept a DatabaseConnection-style dependency.
    """

    def __init__(
        self,
        client,
    ):
        self._client = client

    def connect(self):
        return self._client


def format_duration(
    seconds,
):
    """
    Return a readable elapsed-time value.
    """

    if seconds < 60:
        return f"{seconds:.2f} seconds"

    minutes = int(
        seconds // 60
    )

    remaining_seconds = (
        seconds % 60
    )

    return (
        f"{minutes} minutes "
        f"{remaining_seconds:.2f} seconds"
    )


def format_bytes(
    byte_count,
):
    """
    Return a readable payload-size value.
    """

    if byte_count < 1024:
        return f"{byte_count} bytes"

    kibibytes = (
        byte_count / 1024
    )

    if kibibytes < 1024:
        return f"{kibibytes:.2f} KiB"

    mebibytes = (
        kibibytes / 1024
    )

    return f"{mebibytes:.2f} MiB"


def build_refresh_service(
    *,
    client,
    source_container_repository,
    processing_job_repository,
    refresh_reservation_repository,
    enumerator,
):
    """
    Build one production Source Container Refresh service.
    """

    return SourceContainerRefreshService(
        enumerator=enumerator,

        observation_validator=(
            SourceContainerObservationValidator()
        ),

        source_container_repository=(
            source_container_repository
        ),

        reconciler=(
            SourceContainerReconciler()
        ),

        refresh_reservation_repository=(
            refresh_reservation_repository
        ),

        processing_job_repository=(
            processing_job_repository
        ),

        database_client=client,

        process_type=PROCESS_TYPE,

        pipeline_version=PIPELINE_VERSION,
    )


def print_source_result(
    *,
    source_name,
    result,
    elapsed_seconds,
):
    """
    Print the completed result and operational measurements
    for one Source Refresh.
    """

    persistence = (
        result.get(
            "persistence"
        )
        or {}
    )

    measurements = (
        result.get(
            "measurements"
        )
        or {}
    )

    print(
        f"PASS: {source_name} Source Container "
        "Refresh completed."
    )

    print(
        "  Processing Job ID : "
        f"{result['processing_job_id']}"
    )

    print(
        f"  Observed          : "
        f"{result['observed']}"
    )

    print(
        f"  New               : "
        f"{result['new']}"
    )

    print(
        f"  Existing          : "
        f"{result['existing']}"
    )

    print(
        f"  Reappearing       : "
        f"{result['reappearing']}"
    )

    print(
        f"  Absent            : "
        f"{result['absent']}"
    )

    print(
        "  Upserted          : "
        f"{persistence.get('upserted')}"
    )

    print(
        "  Deactivated       : "
        f"{persistence.get('deactivated')}"
    )

    print(
        "  Payload Size      : "
        f"{format_bytes(measurements['payload_size_bytes'])}"
    )

    print(
        "  Reservation Time  : "
        f"{format_duration(measurements['reservation_seconds'])}"
    )

    print(
        "  Enumeration Time  : "
        f"{format_duration(measurements['enumeration_seconds'])}"
    )

    print(
        "  Validation Time   : "
        f"{format_duration(measurements['validation_seconds'])}"
    )

    print(
        "  Catalog Read Time : "
        f"{format_duration(measurements['catalog_read_seconds'])}"
    )

    print(
        "  Reconciliation    : "
        f"{format_duration(measurements['reconciliation_seconds'])}"
    )

    print(
        "  Persistence Time  : "
        f"{format_duration(measurements['persistence_seconds'])}"
    )

    print(
        "  Job Completion    : "
        f"{format_duration(measurements['completion_seconds'])}"
    )

    print(
        "  Refresh Total     : "
        f"{format_duration(measurements['total_seconds'])}"
    )

    print(
        "  Application Time  : "
        f"{format_duration(elapsed_seconds)}"
    )

    print()


def run_source_refresh(
    *,
    source_name,
    enumerator,
    client,
    source_repository,
    source_container_repository,
    processing_job_repository,
    refresh_reservation_repository,
):
    """
    Resolve and refresh one complete Source Container catalog.
    """

    source_id = (
        source_repository.find_id_by_name(
            source_name
        )
    )

    if source_id is None:
        raise RuntimeError(
            f"Registered {source_name} Source "
            "was not found."
        )

    print(
        f"Starting complete {source_name} "
        "Source Container Refresh."
    )

    print(
        f"  Source ID : {source_id}"
    )

    print()

    refresh_service = (
        build_refresh_service(
            client=client,

            source_container_repository=(
                source_container_repository
            ),

            processing_job_repository=(
                processing_job_repository
            ),

            refresh_reservation_repository=(
                refresh_reservation_repository
            ),

            enumerator=enumerator,
        )
    )

    started_at = perf_counter()

    result = refresh_service.refresh(
        source_id=source_id,

        job_metadata={
            "operation":
                "refresh_all_source_containers",

            "source":
                source_name,
        },
    )

    elapsed_seconds = (
        perf_counter()
        - started_at
    )

    print_source_result(
        source_name=source_name,
        result=result,
        elapsed_seconds=elapsed_seconds,
    )

    return {
        "source_name":
            source_name,

        "elapsed_seconds":
            elapsed_seconds,

        "result":
            result,
    }


def main():

    total_started_at = perf_counter()

    print()

    print(
        "============================================================"
    )

    print(
        "AlphaOmega Complete Source Container Refresh"
    )

    print(
        "============================================================"
    )

    print()

    # ---------------------------------------------------------
    # Shared authenticated database infrastructure
    # ---------------------------------------------------------

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

    existing_database_connection = (
        ExistingDatabaseConnection(
            client
        )
    )

    source_repository = (
        SourceRepository(
            client
        )
    )

    source_container_repository = (
        SourceContainerRepository(
            existing_database_connection
        )
    )

    processing_job_repository = (
        ProcessingJobRepository(
            client
        )
    )

    refresh_reservation_repository = (
        SourceContainerRefreshReservationRepository(
            client
        )
    )

    results = []

    # ---------------------------------------------------------
    # Run every configured Source Refresh
    # ---------------------------------------------------------

    for source_refresh in SOURCE_REFRESHES:

        source_name = (
            source_refresh[
                "source_name"
            ]
        )

        enumerator_factory = (
            source_refresh[
                "enumerator_factory"
            ]
        )

        enumerator = (
            enumerator_factory()
        )

        result = run_source_refresh(
            source_name=source_name,

            enumerator=enumerator,

            client=client,

            source_repository=(
                source_repository
            ),

            source_container_repository=(
                source_container_repository
            ),

            processing_job_repository=(
                processing_job_repository
            ),

            refresh_reservation_repository=(
                refresh_reservation_repository
            ),
        )

        results.append(
            result
        )

    # ---------------------------------------------------------
    # Combined application-operation summary
    # ---------------------------------------------------------

    total_seconds = (
        perf_counter()
        - total_started_at
    )

    total_observed = sum(
        result["result"]["observed"]
        for result in results
    )

    total_new = sum(
        result["result"]["new"]
        for result in results
    )

    total_existing = sum(
        result["result"]["existing"]
        for result in results
    )

    total_reappearing = sum(
        result["result"]["reappearing"]
        for result in results
    )

    total_absent = sum(
        result["result"]["absent"]
        for result in results
    )

    total_upserted = sum(
        (
            result["result"]
            .get(
                "persistence",
                {},
            )
            .get(
                "upserted",
                0,
            )
        )
        for result in results
    )

    total_deactivated = sum(
        (
            result["result"]
            .get(
                "persistence",
                {},
            )
            .get(
                "deactivated",
                0,
            )
        )
        for result in results
    )

    total_payload_size = sum(
        (
            result["result"]
            .get(
                "measurements",
                {},
            )
            .get(
                "payload_size_bytes",
                0,
            )
        )
        for result in results
    )

    print(
        "============================================================"
    )

    print(
        "Complete Refresh Summary"
    )

    print(
        "============================================================"
    )

    print(
        f"  Sources Refreshed : "
        f"{len(results)}"
    )

    print(
        f"  Total Observed    : "
        f"{total_observed}"
    )

    print(
        f"  Total New         : "
        f"{total_new}"
    )

    print(
        f"  Total Existing    : "
        f"{total_existing}"
    )

    print(
        f"  Total Reappearing : "
        f"{total_reappearing}"
    )

    print(
        f"  Total Absent      : "
        f"{total_absent}"
    )

    print(
        f"  Total Upserted    : "
        f"{total_upserted}"
    )

    print(
        f"  Total Deactivated : "
        f"{total_deactivated}"
    )

    print(
        "  Total Payload     : "
        f"{format_bytes(total_payload_size)}"
    )

    print(
        "  Total Time        : "
        f"{format_duration(total_seconds)}"
    )

    print()

    print(
        "ALL SOURCE CONTAINER REFRESHES: PASS"
    )

    print()


if __name__ == "__main__":
    main()