"""
Live AlphaOmega AIOS OneDrive Synchronization Test

Purpose:
    Perform a substantial live production synchronization against the
    top-level OneDrive folder named AIOS.

Selection rule:
    Multiple folders named AIOS may exist. The test resolves every active
    AIOS Source Container through live Microsoft Graph and selects only the
    AIOS folder whose parentReference.path identifies the OneDrive root.

Verifies:
    - The enabled OneDrive Source can be resolved.
    - The top-level AIOS Source Container can be identified unambiguously.
    - The AlphaOmega synthetic Source Root is never selected.
    - The real bounded OneDrive scoped Connector is used.
    - The real atomic synchronization reservation is used.
    - The reserved Processing Job reaches SynchronizationOrchestrator.
    - Translator, Discovery, Extraction, and Load execute.
    - Real file content is extracted.
    - The Processing Job and Synchronization Run persist successfully.

Does NOT:
    - Synchronize Entire OneDrive.
    - Use the AlphaOmega Source Root as the synchronization target.
    - Guess between duplicate AIOS folder names.
    - Delete execution evidence.
"""

from common.security.local_credential_provider import LocalCredentialProvider

from scripts.application.synchronization_connector_service import (
    SynchronizationConnectorService,
)
from scripts.application.synchronization_execution_service import (
    SynchronizationExecutionService,
)

from scripts.connectors.ms_graph.graph_connector import GraphConnector

from scripts.database.database_connection import DatabaseConnection
from scripts.database.knowledge_object_repository import KnowledgeObjectRepository
from scripts.database.processing_job_repository import ProcessingJobRepository
from scripts.database.source_repository import SourceRepository
from scripts.database.synchronization_reservation_repository import (
    SynchronizationReservationRepository,
)

from scripts.discovery.discovery_service import DiscoveryService
from scripts.extraction.extraction_service import ExtractionService

from scripts.load.load_repository import LoadRepository
from scripts.load.load_service import LoadService

from scripts.orchestration.sync_orchestrator import SynchronizationOrchestrator

from scripts.sync.source_container_root_service import SourceContainerRootService

from scripts.translator.graph_translator import GraphTranslator


SOURCE_NAME = "OneDrive"
TARGET_CONTAINER_NAME = "AIOS"

PIPELINE_VERSION = "lab8-live-aios-onedrive-execution-v2"

ROOT_SOURCE_OBJECT_ID = SourceContainerRootService.ROOT_SOURCE_OBJECT_ID


def create_database():
    credential_provider = LocalCredentialProvider()

    database_connection = DatabaseConnection(
        credential_provider
    )

    client = database_connection.connect()

    return database_connection, client


def resolve_onedrive_source(client):
    response = (
        client
        .table("sources")
        .select("id,name,is_enabled")
        .eq("name", SOURCE_NAME)
        .execute()
    )

    rows = response.data or []

    if len(rows) != 1:
        raise RuntimeError(
            "Expected exactly one registered OneDrive Source."
        )

    source = rows[0]

    if source.get("is_enabled") is not True:
        raise RuntimeError(
            "OneDrive Source is not enabled."
        )

    return source


def is_drive_root_parent_path(parent_path):
    """
    Return True when Microsoft Graph reports that the item's parent is
    the OneDrive root.

    Typical Microsoft Graph value:
        /drive/root:
    """

    if parent_path is None:
        return False

    normalized = str(parent_path).strip().rstrip("/").casefold()

    return normalized in {
        "/drive/root:",
        "drive/root:",
    }


def resolve_top_level_aios_container(
    client,
    *,
    source_id,
):
    """
    Resolve the top-level AIOS folder.

    Catalog name alone is insufficient because multiple folders named AIOS
    may exist. Every catalog candidate is resolved through live Microsoft
    Graph. Only a folder whose parentReference.path is the drive root is
    accepted.
    """

    response = (
        client
        .table("source_containers")
        .select(
            "id,"
            "source_id,"
            "source_object_id,"
            "parent_source_object_id,"
            "name,"
            "is_active"
        )
        .eq("source_id", source_id)
        .eq("name", TARGET_CONTAINER_NAME)
        .eq("is_active", True)
        .execute()
    )

    candidates = response.data or []

    if not candidates:
        raise RuntimeError(
            "No active OneDrive Source Container named AIOS was found."
        )

    graph_connector = GraphConnector()

    resolved = []

    print()
    print(
        f"Found {len(candidates)} active catalog Containers named AIOS."
    )

    print()
    print(
        "Resolving candidates through live Microsoft Graph..."
    )

    for candidate in candidates:
        source_object_id = str(
            candidate.get("source_object_id")
            or ""
        ).strip()

        if not source_object_id:
            continue

        if source_object_id == ROOT_SOURCE_OBJECT_ID:
            continue

        endpoint = (
            f"/me/drive/items/{source_object_id}"
        )

        item = graph_connector._get_json(
            endpoint
        )

        if not isinstance(item, dict):
            raise RuntimeError(
                "Microsoft Graph returned an invalid driveItem "
                f"for Source Object ID {source_object_id}."
            )

        if "folder" not in item:
            raise RuntimeError(
                "An AIOS Source Container resolved to a Graph object "
                "that is not a folder."
            )

        parent_reference = (
            item.get("parentReference")
            or {}
        )

        parent_path = parent_reference.get(
            "path"
        )

        web_url = item.get(
            "webUrl"
        )

        print()
        print(
            f"  Catalog ID   : {candidate.get('id')}"
        )

        print(
            f"  Object ID    : {source_object_id}"
        )

        print(
            f"  Graph Name   : {item.get('name')}"
        )

        print(
            f"  Parent Path  : {parent_path}"
        )

        print(
            f"  Web URL      : {web_url}"
        )

        if is_drive_root_parent_path(
            parent_path
        ):
            resolved.append(
                candidate
            )

    if not resolved:
        raise RuntimeError(
            "No AIOS candidate was found directly beneath "
            "the OneDrive root."
        )

    if len(resolved) > 1:
        raise RuntimeError(
            "More than one AIOS folder exists directly beneath "
            "the OneDrive root. Synchronization was not started."
        )

    return resolved[0]


def count_catalog_descendants(
    client,
    *,
    source_id,
    root_source_object_id,
):
    """
    Count active persisted Source Containers beneath the selected AIOS
    catalog Container.

    This is informational. Live synchronization enumeration remains the
    responsibility of the scoped OneDrive Connector.
    """

    response = (
        client
        .table("source_containers")
        .select(
            "source_object_id,"
            "parent_source_object_id"
        )
        .eq("source_id", source_id)
        .eq("is_active", True)
        .execute()
    )

    rows = response.data or []

    children_by_parent = {}

    for row in rows:
        parent_id = row.get(
            "parent_source_object_id"
        )

        object_id = row.get(
            "source_object_id"
        )

        if parent_id is None or object_id is None:
            continue

        parent_id = str(parent_id).strip()
        object_id = str(object_id).strip()

        if not parent_id or not object_id:
            continue

        children_by_parent.setdefault(
            parent_id,
            [],
        ).append(
            object_id
        )

    visited = set()

    pending = list(
        children_by_parent.get(
            root_source_object_id,
            [],
        )
    )

    while pending:
        object_id = pending.pop()

        if object_id in visited:
            continue

        visited.add(
            object_id
        )

        pending.extend(
            children_by_parent.get(
                object_id,
                [],
            )
        )

    return len(visited)


def build_orchestrator(client):
    source_repository = SourceRepository(
        client
    )

    knowledge_object_repository = KnowledgeObjectRepository(
        client
    )

    processing_job_repository = ProcessingJobRepository(
        client
    )

    translator = GraphTranslator()

    discovery_service = DiscoveryService(
        source_repository=source_repository,
        knowledge_object_repository=knowledge_object_repository,
    )

    extraction_service = ExtractionService()

    load_repository = LoadRepository(
        client
    )

    load_service = LoadService(
        source_repository=source_repository,
        load_repository=load_repository,
    )

    orchestrator = SynchronizationOrchestrator(
        connector=GraphConnector(),
        translator=translator,
        discovery_service=discovery_service,
        extraction_service=extraction_service,
        load_service=load_service,
        processing_job_repository=processing_job_repository,
        pipeline_version=PIPELINE_VERSION,
    )

    return processing_job_repository, orchestrator


def load_processing_job(
    client,
    *,
    processing_job_id,
):
    response = (
        client
        .table("processing_jobs")
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
        .eq("id", processing_job_id)
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
        .table("sync_runs")
        .select(
            "id,"
            "processing_job_id,"
            "source_id,"
            "source_container_id"
        )
        .eq("id", sync_run_id)
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
        "=" * 72
    )
    print(
        "AlphaOmega LIVE AIOS OneDrive Synchronization Test"
    )
    print(
        "=" * 72
    )
    print()

    _, client = create_database()

    print(
        "PASS: Authenticated AlphaOmega database connection established."
    )

    source = resolve_onedrive_source(
        client
    )

    source_id = str(
        source["id"]
    )

    print(
        "PASS: Enabled OneDrive Source resolved."
    )

    print(
        f"  Source ID : {source_id}"
    )

    # ---------------------------------------------------------
    # Resolve the actual top-level AIOS folder
    # ---------------------------------------------------------

    container = resolve_top_level_aios_container(
        client,
        source_id=source_id,
    )

    source_container_id = str(
        container["id"]
    )

    source_object_id = str(
        container["source_object_id"]
    )

    parent_source_object_id = container.get(
        "parent_source_object_id"
    )

    print()
    print(
        "PASS: Top-level OneDrive AIOS Container resolved."
    )

    print(
        f"  Name                : {container.get('name')}"
    )

    print(
        f"  Source Container ID : {source_container_id}"
    )

    print(
        f"  Source Object ID    : {source_object_id}"
    )

    print(
        f"  Parent Object ID    : {parent_source_object_id}"
    )

    if source_object_id == ROOT_SOURCE_OBJECT_ID:
        raise RuntimeError(
            "Safety failure: AIOS resolved to the AlphaOmega "
            "synthetic Source Root."
        )

    # ---------------------------------------------------------
    # Show the expected catalog scope
    # ---------------------------------------------------------

    descendant_count = count_catalog_descendants(
        client,
        source_id=source_id,
        root_source_object_id=source_object_id,
    )

    print()
    print(
        "Persisted AIOS catalog scope:"
    )

    print(
        f"  Descendant Containers : {descendant_count}"
    )

    # ---------------------------------------------------------
    # Build the real production execution path
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
            reservation_repository=reservation_repository,
            processing_job_repository=processing_job_repository,
            connector_service=connector_service,
            orchestrator=orchestrator,
            pipeline_version=PIPELINE_VERSION,
        )
    )

    # ---------------------------------------------------------
    # Execute AIOS
    # ---------------------------------------------------------

    print()
    print(
        "=" * 72
    )

    print(
        "STARTING LIVE AIOS ONEDRIVE SYNCHRONIZATION"
    )

    print(
        "=" * 72
    )

    print()
    print(
        "Selected production scope:"
    )

    print(
        "  OneDrive → top-level AIOS → complete AIOS subtree"
    )

    print()

    try:
        result = execution_service.execute(
            source_name=SOURCE_NAME,
            source_id=source_id,
            source_container_id=source_container_id,
            source_object_id=source_object_id,
            metadata={
                "test": (
                    "live_aios_onedrive_"
                    "synchronization"
                ),
                "container_name": TARGET_CONTAINER_NAME,
                "bounded_scope": True,
                "target": "AIOS",
            },
        )

    except Exception as error:
        print()
        print(
            "=" * 72
        )

        print(
            "LIVE AIOS SYNCHRONIZATION FAILED"
        )

        print(
            "=" * 72
        )

        print(
            f"  Error Type : {type(error).__name__}"
        )

        print(
            f"  Error      : {error}"
        )

        print()

        raise

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeError(
            "SynchronizationExecutionService returned "
            "an invalid result."
        )

    processing_job_id = result.get(
        "processing_job_id"
    )

    sync_run_id = result.get(
        "sync_run_id"
    )

    pipeline_result = result.get(
        "result"
    )

    if not processing_job_id:
        raise RuntimeError(
            "Execution result is missing processing_job_id."
        )

    if not sync_run_id:
        raise RuntimeError(
            "Execution result is missing sync_run_id."
        )

    if not isinstance(
        pipeline_result,
        dict,
    ):
        raise RuntimeError(
            "Execution result is missing the pipeline result."
        )

    print()
    print(
        "PASS: Production AIOS execution returned."
    )

    print(
        f"  Processing Job ID : {processing_job_id}"
    )

    print(
        f"  Sync Run ID       : {sync_run_id}"
    )

    # ---------------------------------------------------------
    # Pipeline evidence
    # ---------------------------------------------------------

    counts = pipeline_result.get(
        "counts"
    ) or {}

    associations = int(
        counts.get("associations")
        or 0
    )

    translated = int(
        counts.get("translated")
        or 0
    )

    discovered = int(
        counts.get("discovered")
        or 0
    )

    extracted = int(
        counts.get("extracted")
        or 0
    )

    new_count = int(
        counts.get("new")
        or 0
    )

    modified_count = int(
        counts.get("modified")
        or 0
    )

    unchanged_count = int(
        counts.get("unchanged")
        or 0
    )

    connector_section = pipeline_result.get(
        "connector_section"
    )

    load_section = pipeline_result.get(
        "load_section"
    )

    print()
    print(
        "AIOS Pipeline Results:"
    )

    print(
        f"  Associations : {associations}"
    )

    print(
        f"  Translated   : {translated}"
    )

    print(
        f"  Discovered   : {discovered}"
    )

    print(
        f"  Extracted    : {extracted}"
    )

    print(
        f"  New          : {new_count}"
    )

    print(
        f"  Modified     : {modified_count}"
    )

    print(
        f"  Unchanged    : {unchanged_count}"
    )

    if connector_section is None:
        raise RuntimeError(
            "TEST FAILED: Production scoped Connector did not "
            "return a ConnectorSection."
        )

    print(
        "PASS: Production scoped OneDrive Connector executed."
    )

    if associations <= 1:
        raise RuntimeError(
            "TEST FAILED: AIOS synchronization did not produce "
            "a meaningful subtree."
        )

    print(
        "PASS: AIOS subtree produced multiple associations."
    )

    if translated <= 1:
        raise RuntimeError(
            "TEST FAILED: AIOS subtree did not produce "
            "meaningful Translator output."
        )

    print(
        "PASS: AIOS subtree reached Translator."
    )

    if discovered < 1:
        raise RuntimeError(
            "TEST FAILED: AIOS synchronization produced no "
            "Discovery results."
        )

    print(
        "PASS: AIOS content reached Discovery."
    )

    if extracted < 1:
        raise RuntimeError(
            "TEST FAILED: AIOS synchronization extracted no "
            "real file content."
        )

    print(
        "PASS: Real AIOS file content was extracted."
    )

    if (
        new_count + modified_count > 0
        and load_section is None
    ):
        raise RuntimeError(
            "TEST FAILED: NEW/MODIFIED AIOS content existed "
            "but Load did not execute."
        )

    if load_section is not None:
        print(
            "PASS: Load stage executed."
        )

    # ---------------------------------------------------------
    # Synchronization Run evidence
    # ---------------------------------------------------------

    sync_run = load_sync_run(
        client,
        sync_run_id=sync_run_id,
    )

    if str(
        sync_run.get("processing_job_id")
    ) != str(
        processing_job_id
    ):
        raise RuntimeError(
            "Synchronization Run references the wrong "
            "Processing Job."
        )

    if str(
        sync_run.get("source_id")
    ) != source_id:
        raise RuntimeError(
            "Synchronization Run references the wrong Source."
        )

    if str(
        sync_run.get("source_container_id")
    ) != source_container_id:
        raise RuntimeError(
            "Synchronization Run references the wrong "
            "AIOS Source Container."
        )

    print(
        "PASS: Synchronization Run is bound to top-level AIOS."
    )

    # ---------------------------------------------------------
    # Processing Job lifecycle
    # ---------------------------------------------------------

    processing_job = load_processing_job(
        client,
        processing_job_id=processing_job_id,
    )

    status = processing_job.get(
        "status"
    )

    if status not in {
        "completed",
        "completed_with_errors",
    }:
        raise RuntimeError(
            "AIOS Processing Job did not complete successfully. "
            f"Status: {status}; "
            f"Error: {processing_job.get('error_message')}"
        )

    print(
        f"PASS: AIOS Processing Job completed "
        f"with status: {status}"
    )

    # ---------------------------------------------------------
    # Final
    # ---------------------------------------------------------

    print()
    print(
        "=" * 72
    )

    print(
        "LIVE AIOS ONEDRIVE SYNCHRONIZATION: PASS"
    )

    print(
        "=" * 72
    )

    print()


if __name__ == "__main__":
    main()