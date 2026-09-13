"""
Synchronization CONTAINER Boundary Test

Purpose:
    Validates the canonical CONTAINER orchestration boundary.

Verifies:
    - CONTAINER objects can pass through Connector and Translator.
    - CONTAINER objects preserve synchronization association and correlation
      identity.
    - CONTAINER objects do not proceed into content Discovery, Extraction,
      or Load behavior intended for Knowledge Objects.
    - CONTENT objects remain eligible for downstream synchronization stages.
    - Processing Job lifecycle behavior remains valid when CONTAINER objects
      are present.

Does NOT:
    - Treat CONTAINER objects as Knowledge Objects.
    - Retrieve live source content.
    - Connect to the live AlphaOmega database.
    - Change canonical object-type definitions.
"""

from common.object_types import (
    CONTAINER,
    CONTENT,
)

from scripts.orchestration.sync_orchestrator import (
    SynchronizationOrchestrator,
)

from scripts.sync.sync_state import (
    SyncState,
)


# ============================================================================
# Minimal Locked Section
# ============================================================================

class FakeLockedSection:

    def __init__(self):
        self.is_locked = True


# ============================================================================
# Connector
# ============================================================================

class FakeConnectorSection(
    FakeLockedSection
):

    def __init__(
        self,
        raw_objects,
        source_name,
    ):
        super().__init__()

        self.raw_objects = raw_objects

        self.source_name = (
            source_name
        )


class FakeConnector:

    def run(
        self,
        source_name,
    ):

        if source_name != "Test Source":
            raise RuntimeError(
                "Unexpected source name."
            )

        return FakeConnectorSection(
            [
                {
                    "source_object_type":
                        "folder",

                    "raw_object": {
                        "id":
                            "container-001",

                        "name":
                            "Test Container",
                    },
                },
                {
                    "source_object_type":
                        "file",

                    "raw_object": {
                        "id":
                            "content-001",

                        "name":
                            "Test Content.txt",
                    },
                },
            ],
            source_name=source_name,
        )


# ============================================================================
# Translator
# ============================================================================

class FakeTranslatorRecord:

    def __init__(
        self,
        *,
        correlation_id,
        source_object_id,
        object_type,
    ):
        self.correlation_id = (
            correlation_id
        )

        self.source_object_id = (
            source_object_id
        )

        self.object_type = (
            object_type
        )


class FakeTranslatorSection(
    FakeLockedSection
):

    def __init__(
        self,
        translated_records,
    ):
        super().__init__()

        self.translated_records = (
            translated_records
        )


class FakeTranslator:

    def run(
        self,
        translation_input,
    ):

        if (
            len(
                translation_input.raw_objects
            )
            != 2
        ):
            raise RuntimeError(
                "Translator did not receive "
                "both Connector objects."
            )

        translated_records = []

        for correlated_object in (
            translation_input.raw_objects
        ):

            correlation_id = (
                correlated_object[
                    "correlation_id"
                ]
            )

            raw_object = (
                correlated_object[
                    "raw_object"
                ]
            )

            source_object_type = (
                correlated_object[
                    "source_object_type"
                ]
            )

            if (
                source_object_type
                == "folder"
            ):
                object_type = (
                    CONTAINER
                )

            elif (
                source_object_type
                == "file"
            ):
                object_type = (
                    CONTENT
                )

            else:
                raise RuntimeError(
                    "Unexpected source object type."
                )

            translated_records.append(
                FakeTranslatorRecord(
                    correlation_id=(
                        correlation_id
                    ),
                    source_object_id=(
                        raw_object["id"]
                    ),
                    object_type=(
                        object_type
                    ),
                )
            )

        return FakeTranslatorSection(
            translated_records
        )


# ============================================================================
# Discovery
# ============================================================================

class FakeDiscoveryRecord:

    def __init__(
        self,
        *,
        correlation_id,
    ):
        self.correlation_id = (
            correlation_id
        )

        self.sync_state = (
            SyncState.UNCHANGED
        )

        self.requires_extraction = (
            False
        )

        self.knowledge_object_id = (
            "knowledge-object-001"
        )

        self.previous_content_hash = (
            "existing-hash"
        )


class FakeDiscoverySection(
    FakeLockedSection
):

    def __init__(
        self,
        discovery_records,
    ):
        super().__init__()

        self.discovery_records = (
            discovery_records
        )


class FakeDiscoveryService:

    def __init__(self):
        self.records_received = []

    def run(
        self,
        discovery_input,
    ):

        self.records_received = list(
            discovery_input.translated_records
        )

        # ------------------------------------------------------------
        # This is the critical assertion.
        #
        # Discovery must receive exactly one record and that record
        # must be canonical CONTENT.
        # ------------------------------------------------------------

        if (
            len(
                self.records_received
            )
            != 1
        ):
            raise RuntimeError(
                "Discovery did not receive exactly "
                "one routed CONTENT record.\n"
                f"Actual: "
                f"{len(self.records_received)}"
            )

        record = (
            self.records_received[0]
        )

        if (
            record.object_type
            != CONTENT
        ):
            raise RuntimeError(
                "Discovery received a non-CONTENT "
                "TranslatorRecord."
            )

        if (
            record.source_object_id
            != "content-001"
        ):
            raise RuntimeError(
                "Discovery received the wrong "
                "TranslatorRecord."
            )

        return FakeDiscoverySection(
            [
                FakeDiscoveryRecord(
                    correlation_id=(
                        record.correlation_id
                    )
                )
            ]
        )


# ============================================================================
# Extraction
# ============================================================================

class FakeExtractionService:

    def __init__(self):
        self.called = False

    def run(
        self,
        translator_records,
    ):
        self.called = True

        raise RuntimeError(
            "Extraction must not execute for "
            "this test."
        )


# ============================================================================
# Load
# ============================================================================

class FakeLoadService:

    def __init__(self):
        self.called = False

    def run(
        self,
        *,
        associations,
        processing_job_id,
    ):
        self.called = True

        raise RuntimeError(
            "Load must not execute for "
            "this test."
        )


# ============================================================================
# Processing Job
# ============================================================================

class FakeProcessingJobRepository:

    def __init__(self):
        self.created = False
        self.completed = False
        self.failed = False
        self.processing_job_id = (
            "processing-job-001"
        )

    def create(
        self,
        *,
        process_type,
        pipeline_version,
        metadata,
    ):

        if process_type != "sync":
            raise RuntimeError(
                "Unexpected process_type."
            )

        self.created = True

        return (
            self.processing_job_id
        )

    def complete(
        self,
        processing_job_id,
    ):

        if (
            processing_job_id
            != self.processing_job_id
        ):
            raise RuntimeError(
                "Wrong Processing Job completed."
            )

        self.completed = True

    def fail(
        self,
        processing_job_id,
        error,
    ):
        self.failed = True


# ============================================================================
# Test
# ============================================================================

def main():

    print()

    print(
        "Running CONTAINER orchestration "
        "boundary test..."
    )

    print()

    discovery_service = (
        FakeDiscoveryService()
    )

    extraction_service = (
        FakeExtractionService()
    )

    load_service = (
        FakeLoadService()
    )

    processing_job_repository = (
        FakeProcessingJobRepository()
    )

    orchestrator = (
        SynchronizationOrchestrator(
            connector=(
                FakeConnector()
            ),
            translator=(
                FakeTranslator()
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
                "container-boundary-test"
            ),
        )
    )

    result = (
        orchestrator.run(
            source_name=(
                "Test Source"
            ),
            job_metadata={
                "test":
                    "container-boundary",
            },
        )
    )

    associations = list(
        result["associations"]
    )

    counts = (
        result["counts"]
    )

    # ========================================================================
    # Association Count
    # ========================================================================

    if len(associations) != 2:
        raise RuntimeError(
            "Expected exactly two "
            "SynchronizationAssociations."
        )

    print(
        "PASS: Both Connector objects received "
        "SynchronizationAssociations."
    )

    # ========================================================================
    # Identify Associations
    # ========================================================================

    container_association = None
    content_association = None

    for association in associations:

        translator_record = (
            association.translator_record
        )

        if translator_record is None:
            raise RuntimeError(
                "Association is missing "
                "TranslatorRecord."
            )

        if (
            translator_record.object_type
            == CONTAINER
        ):
            container_association = (
                association
            )

        elif (
            translator_record.object_type
            == CONTENT
        ):
            content_association = (
                association
            )

    if container_association is None:
        raise RuntimeError(
            "CONTAINER association not found."
        )

    if content_association is None:
        raise RuntimeError(
            "CONTENT association not found."
        )

    print(
        "PASS: CONTAINER and CONTENT both "
        "reached Translator."
    )

    # ========================================================================
    # CONTAINER Boundary
    # ========================================================================

    if (
        container_association
        .discovery_record
        is not None
    ):
        raise RuntimeError(
            "CONTAINER crossed the "
            "Translator -> Discovery boundary."
        )

    print(
        "PASS: CONTAINER stopped before Discovery."
    )

    if (
        container_association
        .extraction_record
        is not None
    ):
        raise RuntimeError(
            "CONTAINER reached Extraction."
        )

    print(
        "PASS: CONTAINER did not reach Extraction."
    )

    # ========================================================================
    # CONTENT Routing
    # ========================================================================

    if (
        content_association
        .discovery_record
        is None
    ):
        raise RuntimeError(
            "CONTENT did not reach Discovery."
        )

    if (
        content_association
        .discovery_record
        .sync_state
        != SyncState.UNCHANGED
    ):
        raise RuntimeError(
            "CONTENT did not retain expected "
            "UNCHANGED state."
        )

    print(
        "PASS: CONTENT reached Discovery normally."
    )

    # ========================================================================
    # Downstream Stop
    # ========================================================================

    if extraction_service.called:
        raise RuntimeError(
            "Extraction unexpectedly executed."
        )

    print(
        "PASS: UNCHANGED CONTENT stopped "
        "before Extraction."
    )

    if load_service.called:
        raise RuntimeError(
            "Load unexpectedly executed."
        )

    print(
        "PASS: Load did not execute."
    )

    # ========================================================================
    # Discovery Input
    # ========================================================================

    if (
        len(
            discovery_service
            .records_received
        )
        != 1
    ):
        raise RuntimeError(
            "Discovery input count incorrect."
        )

    if (
        discovery_service
        .records_received[0]
        .object_type
        != CONTENT
    ):
        raise RuntimeError(
            "Discovery input was not CONTENT."
        )

    print(
        "PASS: Discovery received only "
        "canonical CONTENT."
    )

    # ========================================================================
    # Counts
    # ========================================================================

    expected_counts = {
        "associations":
            2,

        "translated":
            2,

        "discovered":
            1,

        "extracted":
            0,

        "new":
            0,

        "modified":
            0,

        "unchanged":
            1,
    }

    if counts != expected_counts:
        raise RuntimeError(
            "Orchestration counts incorrect.\n"
            f"Expected: {expected_counts}\n"
            f"Actual:   {counts}"
        )

    print(
        "PASS: Orchestration counts reflect "
        "the CONTAINER boundary."
    )

    # ========================================================================
    # Processing Job
    # ========================================================================

    if (
        not processing_job_repository.created
    ):
        raise RuntimeError(
            "Processing Job was not created."
        )

    if (
        not processing_job_repository.completed
    ):
        raise RuntimeError(
            "Processing Job was not completed."
        )

    if (
        processing_job_repository.failed
    ):
        raise RuntimeError(
            "Processing Job was unexpectedly failed."
        )

    print(
        "PASS: Processing Job completed normally."
    )

    print()

    print(
        "CONTAINER ORCHESTRATION BOUNDARY "
        "TEST PASSED."
    )

    print()


if __name__ == "__main__":
    main()