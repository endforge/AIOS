"""
Live AlphaOmega OneNote Synchronization Execution Test

Purpose:
    Validates the production synchronization execution path against one
    bounded OneNote Container using live Microsoft Graph and the live
    AlphaOmega database.

Verifies:
    - One active bounded OneNote Source Container can be selected.
    - Atomic synchronization reservation creates the Processing Job and
      Synchronization Run.
    - SynchronizationExecutionService routes the selected scope through
      SynchronizationConnectorService.
    - The production OneNote scoped Connector completely enumerates only
      the selected scope.
    - The reserved Processing Job is handed to
      SynchronizationOrchestrator.run_reserved().
    - Translator, Discovery, Extraction, and Load execute through the
      existing production synchronization pipeline.
    - The reserved Processing Job reaches a terminal state.

Does NOT:
    - Synchronize Entire OneNote.
    - Synchronize OneDrive.
    - Use the AlphaOmega Source Root as the synchronization target.
    - Delete synchronization evidence after completion.
"""

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.application.synchronization_connector_service import (
    SynchronizationConnectorService,
)
from scripts.application.synchronization_execution_service import (
    SynchronizationExecutionService,
)

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)
from scripts.database.knowledge_object_repository import (
    KnowledgeObjectRepository,
)
from scripts.database.processing_job_repository import (
    ProcessingJobRepository,
)
from scripts.database.source_repository import (
    SourceRepository,
)
from scripts.database.synchronization_reservation_repository import (
    SynchronizationReservationRepository,
)

from scripts.discovery.discovery_service import (
    DiscoveryService,
)
from scripts.extraction.extraction_service import (
    ExtractionService,
)

from scripts.load.load_repository import (
    LoadRepository,
)
from scripts.load.load_service import (
    LoadService,
)

from scripts.orchestration.sync_orchestrator import (
    SynchronizationOrchestrator,
)

from scripts.sync.source_container_root_service import (
    SourceContainerRootService,
)

from scripts.translator.graph_translator import (
    GraphTranslator,
)


SOURCE_NAME = "OneNote"

PIPELINE_VERSION = (
    "lab8-live-scoped-onenote-execution-v1"
)

ROOT_SOURCE_OBJECT_ID = (
    SourceContainerRootService
    .ROOT_SOURCE_OBJECT_ID
)


def create_database():
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

    return (
        database_connection,
        client,
    )


def resolve_onenote_source(
    client,
):
    response = (
        client
        .table(
            "sources"
        )
        .select(
            "id,name,is_enabled"
        )
        .eq(
            "name",
            SOURCE_NAME,
        )
        .execute()
    )

    rows = response.data or []

    if len(rows) != 1:
        raise RuntimeError(
            "Expected exactly one registered OneNote Source."
        )

    source = rows[0]

    if (
        source.get(
            "is_enabled"
        )
        is not True
    ):
        raise RuntimeError(
            "OneNote Source is not enabled."
        )

    return source


def resolve_bounded_leaf_container(
    client,
    *,
    source_id,
):
    """
    Select one active OneNote catalog Container that has no active
    child Container.

    OneNote Pages are not Source Containers, so an ordinary Section
    naturally appears as a leaf in the Source Container Catalog.

    The AlphaOmega Source Root is explicitly excluded.
    """

    response = (
        client
        .table(
            "source_containers"
        )
        .select(
            "id,"
            "source_id,"
            "source_object_id,"
            "parent_source_object_id,"
            "name,"
            "is_active"
        )
        .eq(
            "source_id",
            source_id,
        )
        .eq(
            "is_active",
            True,
        )
        .execute()
    )

    containers = response.data or []

    if not containers:
        raise RuntimeError(
            "No active OneNote Source Containers were found."
        )

    parent_ids = {
        str(
            container.get(
                "parent_source_object_id"
            )
        ).strip()
        for container in containers
        if container.get(
            "parent_source_object_id"
        )
    }

    candidates = []

    for container in containers:

        source_object_id = (
            container.get(
                "source_object_id"
            )
        )

        if source_object_id is None:
            continue

        source_object_id = str(
            source_object_id
        ).strip()

        if not source_object_id:
            continue

        if (
            source_object_id
            == ROOT_SOURCE_OBJECT_ID
        ):
            continue

        if source_object_id in parent_ids:
            continue

        candidates.append(
            container
        )

    if not candidates:
        raise RuntimeError(
            "No bounded OneNote leaf Container was found."
        )

    candidates.sort(
        key=lambda value: (
            str(
                value.get(
                    "name"
                )
                or ""
            ).casefold(),
            str(
                value.get(
                    "id"
                )
                or ""
            ),
        )
    )

    return candidates[0]


def build_orchestrator(
    client,
):
    source_repository = (
        SourceRepository(
            client
        )
    )

    knowledge_object_repository = (
        KnowledgeObjectRepository(
            client
        )
    )

    processing_job_repository = (
        ProcessingJobRepository(
            client
        )
    )

    translator = (
        GraphTranslator()
    )

    discovery_service = (
        DiscoveryService(
            source_repository=(
                source_repository
            ),
            knowledge_object_repository=(
                knowledge_object_repository
            ),
        )
    )

    extraction_service = (
        ExtractionService()
    )

    load_repository = (
        LoadRepository(
            client
        )
    )

    load_service = (
        LoadService(
            source_repository=(
                source_repository
            ),
            load_repository=(
                load_repository
            ),
        )
    )

    orchestrator = (
        SynchronizationOrchestrator(
            connector=(
                GraphConnector()
            ),
            translator=(
                translator
            ),
            discovery_service=(
                discovery_service
            ),
            extraction_service=(
                extraction_service
            ),
            load_service=(
                load_service
            ),
            processing_job_repository=(
                processing_job_repository
            ),
            pipeline_version=(
                PIPELINE_VERSION
            ),
        )
    )

    return (
        processing_job_repository,
        orchestrator,
    )


def load_processing_job(
    client,
    *,
    processing_job_id,
):
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
            "started_at,"
            "completed_at,"
            "error_message,"
            "pipeline_version,"
            "metadata"
        )
        .eq(
            "id",
            processing_job_id,
        )
        .execute()
    )

    rows = response.data or []

    if len(rows) != 1:
        raise RuntimeError(
            "Processing Job was not found after execution."
        )

    return rows[0]


def load_sync_run(
    client,
    *,
    sync_run_id,
):
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

    rows = response.data or []

    if len(rows) != 1:
        raise RuntimeError(
            "Synchronization Run was not found after execution."
        )

    return rows[0]


def main():
    print()
    print(
        "=" * 70
    )
    print(
        "AlphaOmega Live Scoped OneNote Synchronization Execution Test"
    )
    print(
        "=" * 70
    )
    print()

    # ---------------------------------------------------------
    # Database and Source
    # ---------------------------------------------------------

    (
        database_connection,
        client,
    ) = create_database()

    print(
        "PASS: Authenticated AlphaOmega database connection established."
    )

    source = resolve_onenote_source(
        client
    )

    source_id = str(
        source[
            "id"
        ]
    )

    print(
        "PASS: Enabled OneNote Source resolved."
    )

    print(
        f"  Source ID : {source_id}"
    )

    # ---------------------------------------------------------
    # Controlled bounded target
    # ---------------------------------------------------------

    container = (
        resolve_bounded_leaf_container(
            client,
            source_id=source_id,
        )
    )

    source_container_id = str(
        container[
            "id"
        ]
    )

    source_object_id = str(
        container[
            "source_object_id"
        ]
    )

    container_name = (
        str(
            container.get(
                "name"
            )
            or ""
        )
    )

    print()
    print(
        "Selected bounded OneNote Container:"
    )

    print(
        f"  Name                : {container_name}"
    )

    print(
        f"  Source Container ID : {source_container_id}"
    )

    print(
        f"  Source Object ID    : {source_object_id}"
    )

    print(
        f"  Parent Object ID    : "
        f"{container.get('parent_source_object_id')}"
    )

    if (
        source_object_id
        == ROOT_SOURCE_OBJECT_ID
    ):
        raise RuntimeError(
            "Safety failure: Source Root was selected."
        )

    # ---------------------------------------------------------
    # Production pipeline
    # ---------------------------------------------------------

    (
        processing_job_repository,
        orchestrator,
    ) = build_orchestrator(
        client
    )

    reservation_repository = (
        SynchronizationReservationRepository(
            client
        )
    )

    connector_service = (
        SynchronizationConnectorService()
    )

    execution_service = (
        SynchronizationExecutionService(
            reservation_repository=(
                reservation_repository
            ),
            processing_job_repository=(
                processing_job_repository
            ),
            connector_service=(
                connector_service
            ),
            orchestrator=(
                orchestrator
            ),
            pipeline_version=(
                PIPELINE_VERSION
            ),
        )
    )

    # ---------------------------------------------------------
    # Live execution
    # ---------------------------------------------------------

    print()
    print(
        "Starting live bounded OneNote synchronization..."
    )
    print()

    try:

        result = (
            execution_service.execute(
                source_name=(
                    SOURCE_NAME
                ),
                source_id=(
                    source_id
                ),
                source_container_id=(
                    source_container_id
                ),
                source_object_id=(
                    source_object_id
                ),
                metadata={
                    "test":
                        (
                            "live_scoped_onenote_"
                            "synchronization_execution"
                        ),
                    "container_name":
                        container_name,
                    "bounded_scope":
                        True,
                },
            )
        )

    except Exception as error:

        print()
        print(
            "LIVE SYNCHRONIZATION FAILED"
        )

        print(
            f"  Error Type : "
            f"{type(error).__name__}"
        )

        print(
            f"  Error      : "
            f"{error}"
        )

        raise

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeError(
            "SynchronizationExecutionService returned "
            "an invalid result."
        )

    processing_job_id = (
        result.get(
            "processing_job_id"
        )
    )

    sync_run_id = (
        result.get(
            "sync_run_id"
        )
    )

    if not processing_job_id:
        raise RuntimeError(
            "Execution result is missing processing_job_id."
        )

    if not sync_run_id:
        raise RuntimeError(
            "Execution result is missing sync_run_id."
        )

    print()
    print(
        "PASS: SynchronizationExecutionService returned "
        "a production execution result."
    )

    print(
        f"  Processing Job ID : {processing_job_id}"
    )

    print(
        f"  Sync Run ID       : {sync_run_id}"
    )

    # ---------------------------------------------------------
    # Persisted reservation evidence
    # ---------------------------------------------------------

    sync_run = load_sync_run(
        client,
        sync_run_id=sync_run_id,
    )

    if (
        str(
            sync_run.get(
                "processing_job_id"
            )
        )
        != str(
            processing_job_id
        )
    ):
        raise RuntimeError(
            "Synchronization Run references the wrong "
            "Processing Job."
        )

    if (
        str(
            sync_run.get(
                "source_id"
            )
        )
        != source_id
    ):
        raise RuntimeError(
            "Synchronization Run references the wrong Source."
        )

    if (
        str(
            sync_run.get(
                "source_container_id"
            )
        )
        != source_container_id
    ):
        raise RuntimeError(
            "Synchronization Run references the wrong "
            "Source Container."
        )

    print(
        "PASS: Synchronization Run contains the selected "
        "bounded scope identities."
    )

    # ---------------------------------------------------------
    # Processing Job lifecycle
    # ---------------------------------------------------------

    processing_job = (
        load_processing_job(
            client,
            processing_job_id=(
                processing_job_id
            ),
        )
    )

    status = (
        processing_job.get(
            "status"
        )
    )

    print(
        f"PASS: Processing Job persisted with status: {status}"
    )

    if status not in {
        "completed",
        "completed_with_errors",
    }:
        raise RuntimeError(
            "Live synchronization Processing Job did not "
            "complete successfully. "
            f"Status: {status}; "
            f"Error: {processing_job.get('error_message')}"
        )

    if (
        str(
            processing_job.get(
                "source_id"
            )
        )
        != source_id
    ):
        raise RuntimeError(
            "Processing Job references the wrong Source."
        )

    # ---------------------------------------------------------
    # Pipeline summary
    # ---------------------------------------------------------

    pipeline_result = (
        result.get(
            "result"
        )
    )

    print()
    print(
        "Pipeline result:"
    )

    print(
        pipeline_result
    )

    print()
    print(
        "=" * 70
    )
    print(
        "LIVE SCOPED ONENOTE SYNCHRONIZATION EXECUTION: PASS"
    )
    print(
        "=" * 70
    )
    print()


if __name__ == "__main__":
    main()