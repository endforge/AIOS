"""
AlphaOmega Synchronization Execution Service Database Integration Test

Purpose:
    Validates the synchronization execution boundary using the real
    AlphaOmega database reservation mechanism while preventing live
    Source-of-Truth synchronization.

Responsibilities:
    - Authenticate to the AlphaOmega database.
    - Locate the persisted OneNote Source Root.
    - Invoke SynchronizationExecutionService.
    - Use the real SynchronizationReservationRepository.
    - Confirm one Processing Job and Synchronization Run are created.
    - Confirm reserved identity reaches Connector and Orchestrator stages.
    - Complete the reserved Processing Job through controlled orchestration.
    - Verify the Processing Job is no longer running.

Does NOT:
    - Call Microsoft Graph.
    - Enumerate OneDrive or OneNote.
    - Retrieve Source content.
    - Run Translator, Discovery, Extraction, or Load.
    - Modify Knowledge Objects.
    - Delete synchronization history.
"""

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.application.synchronization_execution_service import (
    SynchronizationExecutionService,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)

from scripts.database.processing_job_repository import (
    ProcessingJobRepository,
)

from scripts.database.synchronization_reservation_repository import (
    SynchronizationReservationRepository,
)

from scripts.sync.source_container_root_service import (
    SourceContainerRootService,
)


PIPELINE_VERSION = "lab8-execution-integration-test"

ONENOTE_SOURCE_NAME = "OneNote"

ROOT_SOURCE_OBJECT_ID = (
    SourceContainerRootService
    .ROOT_SOURCE_OBJECT_ID
)


class ControlledConnectorSection:
    """
    Minimal controlled ConnectorSection stand-in.

    This test stops before the real Translator boundary, so only identity
    and test traceability are required.
    """

    def __init__(
        self,
        *,
        source_name,
        source_object_id,
    ):
        self.source_name = source_name
        self.source_object_id = source_object_id
        self.locked = True


class ControlledConnectorService:
    """
    Prevent Microsoft Graph access while proving execution routing.
    """

    def __init__(
        self,
    ):
        self.calls = []

    def execute(
        self,
        *,
        source_name,
        source_object_id=None,
    ):
        self.calls.append(
            {
                "source_name":
                    source_name,

                "source_object_id":
                    source_object_id,
            }
        )

        return ControlledConnectorSection(
            source_name=source_name,
            source_object_id=source_object_id,
        )


class ControlledReservedOrchestrator:
    """
    Controlled reserved-job Orchestrator boundary.

    Completes the real Processing Job without executing the content
    synchronization pipeline.
    """

    def __init__(
        self,
        *,
        processing_job_repository,
    ):
        self._processing_job_repository = (
            processing_job_repository
        )

        self.calls = []

    def run_reserved(
        self,
        *,
        processing_job_id,
        connector_section,
    ):
        self.calls.append(
            {
                "processing_job_id":
                    processing_job_id,

                "connector_section":
                    connector_section,
            }
        )

        self._processing_job_repository.complete(
            processing_job_id
        )

        return {
            "processing_job_id":
                processing_job_id,

            "status":
                "completed",

            "test_mode":
                "controlled_reserved_orchestration",
        }


def create_client():
    """
    Create the authenticated AlphaOmega database client.
    """

    credential_provider = (
        LocalCredentialProvider()
    )

    database_connection = (
        DatabaseConnection(
            credential_provider=(
                credential_provider
            )
        )
    )

    return database_connection.connect()


def find_onenote_source(
    client,
):
    """
    Resolve the enabled OneNote Source.
    """

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
            ONENOTE_SOURCE_NAME,
        )
        .execute()
    )

    rows = response.data or []

    if len(
        rows
    ) != 1:
        raise RuntimeError(
            "Expected exactly one OneNote Source."
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


def find_onenote_root(
    client,
    *,
    source_id,
):
    """
    Resolve the active AlphaOmega-managed OneNote Source Root.
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
            "source_object_id",
            ROOT_SOURCE_OBJECT_ID,
        )
        .execute()
    )

    rows = response.data or []

    if len(
        rows
    ) != 1:
        raise RuntimeError(
            "Expected exactly one OneNote Source Root."
        )

    root = rows[0]

    if (
        root.get(
            "is_active"
        )
        is not True
    ):
        raise RuntimeError(
            "OneNote Source Root is not active."
        )

    if (
        root.get(
            "parent_source_object_id"
        )
        is not None
    ):
        raise RuntimeError(
            "OneNote Source Root unexpectedly has a parent."
        )

    return root


def load_processing_job(
    client,
    *,
    processing_job_id,
):
    """
    Read the persisted Processing Job created by reservation.
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

    if len(
        rows
    ) != 1:
        raise RuntimeError(
            "Reserved Processing Job was not found."
        )

    return rows[0]


def load_sync_run(
    client,
    *,
    sync_run_id,
):
    """
    Read the persisted Synchronization Run created by reservation.
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

    rows = response.data or []

    if len(
        rows
    ) != 1:
        raise RuntimeError(
            "Reserved Synchronization Run was not found."
        )

    return rows[0]


def main():
    print()
    print(
        "=" * 60
    )
    print(
        "AlphaOmega Synchronization Execution Service "
        "Database Integration Test"
    )
    print(
        "=" * 60
    )
    print()

    # -------------------------------------------------
    # Database
    # -------------------------------------------------

    client = create_client()

    print(
        "PASS: Authenticated database connection established."
    )

    # -------------------------------------------------
    # Persisted Source Root
    # -------------------------------------------------

    source = find_onenote_source(
        client
    )

    source_id = str(
        source[
            "id"
        ]
    )

    print(
        "PASS: OneNote Source resolved."
    )

    source_root = find_onenote_root(
        client,
        source_id=source_id,
    )

    source_container_id = str(
        source_root[
            "id"
        ]
    )

    print(
        "PASS: Active OneNote Source Root resolved."
    )

    print(
        f"  Source ID           : {source_id}"
    )

    print(
        f"  Source Container ID : {source_container_id}"
    )

    print(
        f"  Source Object ID    : {ROOT_SOURCE_OBJECT_ID}"
    )

    # -------------------------------------------------
    # Production repositories
    # -------------------------------------------------

    reservation_repository = (
        SynchronizationReservationRepository(
            client
        )
    )

    processing_job_repository = (
        ProcessingJobRepository(
            client
        )
    )

    # -------------------------------------------------
    # Controlled downstream boundaries
    # -------------------------------------------------

    connector_service = (
        ControlledConnectorService()
    )

    orchestrator = (
        ControlledReservedOrchestrator(
            processing_job_repository=(
                processing_job_repository
            )
        )
    )

    # -------------------------------------------------
    # Production Execution Service
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Execute
    # -------------------------------------------------

    print()
    print(
        "Executing controlled OneNote Source Root synchronization..."
    )

    result = (
        execution_service.execute(
            source_name=(
                ONENOTE_SOURCE_NAME
            ),

            source_id=(
                source_id
            ),

            source_container_id=(
                source_container_id
            ),

            source_object_id=(
                ROOT_SOURCE_OBJECT_ID
            ),

            metadata={
                "test":
                    (
                        "synchronization_execution_"
                        "service_database"
                    ),

                "live_source_access":
                    False,
            },
        )
    )

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

    if not processing_job_id:
        raise RuntimeError(
            "Execution result did not contain "
            "processing_job_id."
        )

    if not sync_run_id:
        raise RuntimeError(
            "Execution result did not contain "
            "sync_run_id."
        )

    print(
        "PASS: SynchronizationExecutionService completed."
    )

    print(
        f"  Processing Job ID : {processing_job_id}"
    )

    print(
        f"  Sync Run ID       : {sync_run_id}"
    )

    # -------------------------------------------------
    # Connector assertions
    # -------------------------------------------------

    if len(
        connector_service.calls
    ) != 1:
        raise RuntimeError(
            "Controlled Connector Service was not called "
            "exactly once."
        )

    connector_call = (
        connector_service.calls[0]
    )

    if (
        connector_call[
            "source_name"
        ]
        != ONENOTE_SOURCE_NAME
    ):
        raise RuntimeError(
            "Execution Service passed the wrong Source "
            "to the Connector Service."
        )

    # Entire OneNote must be converted from the
    # AlphaOmega Source Root identity to whole-source
    # Connector execution.
    if (
        connector_call[
            "source_object_id"
        ]
        is not None
    ):
        raise RuntimeError(
            "Entire OneNote did not route as "
            "whole-source Connector execution."
        )

    print(
        "PASS: OneNote Source Root routed as whole-source execution."
    )

    # -------------------------------------------------
    # Orchestrator assertions
    # -------------------------------------------------

    if len(
        orchestrator.calls
    ) != 1:
        raise RuntimeError(
            "Reserved Orchestrator was not called "
            "exactly once."
        )

    orchestrator_call = (
        orchestrator.calls[0]
    )

    if (
        orchestrator_call[
            "processing_job_id"
        ]
        != processing_job_id
    ):
        raise RuntimeError(
            "Reserved Orchestrator received the wrong "
            "Processing Job identity."
        )

    print(
        "PASS: Reserved Processing Job identity reached Orchestrator."
    )

    # -------------------------------------------------
    # Persisted Processing Job
    # -------------------------------------------------

    processing_job = (
        load_processing_job(
            client,
            processing_job_id=(
                processing_job_id
            ),
        )
    )

    if (
        processing_job.get(
            "status"
        )
        != "completed"
    ):
        raise RuntimeError(
            "Processing Job was not completed."
        )

    if (
        processing_job.get(
            "source_id"
        )
        != source_id
    ):
        raise RuntimeError(
            "Processing Job contains the wrong Source identity."
        )

    if (
        processing_job.get(
            "pipeline_version"
        )
        != PIPELINE_VERSION
    ):
        raise RuntimeError(
            "Processing Job contains the wrong pipeline version."
        )

    print(
        "PASS: Reserved Processing Job persisted and completed."
    )

    # -------------------------------------------------
    # Persisted Synchronization Run
    # -------------------------------------------------

    sync_run = load_sync_run(
        client,
        sync_run_id=sync_run_id,
    )

    if (
        sync_run.get(
            "processing_job_id"
        )
        != processing_job_id
    ):
        raise RuntimeError(
            "Synchronization Run references the wrong "
            "Processing Job."
        )

    if (
        sync_run.get(
            "source_id"
        )
        != source_id
    ):
        raise RuntimeError(
            "Synchronization Run references the wrong Source."
        )

    if (
        sync_run.get(
            "source_container_id"
        )
        != source_container_id
    ):
        raise RuntimeError(
            "Synchronization Run references the wrong "
            "Source Container."
        )

    print(
        "PASS: Synchronization Run persisted with correct identities."
    )

    print()
    print(
        "=" * 60
    )
    print(
        "SYNCHRONIZATION EXECUTION DATABASE INTEGRATION: PASS"
    )
    print(
        "=" * 60
    )


if __name__ == "__main__":
    main()