"""
Synchronization Orchestrator Test

Purpose:
    Provides isolated regression validation of SynchronizationOrchestrator.

Verifies:
    - Required orchestration dependencies are enforced.
    - A Source name is required.
    - NEW, MODIFIED, and UNCHANGED records are routed correctly.
    - Record-level failures remain isolated.
    - Stage-level failures fail the Processing Job.
    - MODIFIED records whose extracted content hash is unchanged stop before
      Load.
    - Processing Job creation, completion, and failure follow orchestration
      results.
    - Synchronization associations preserve stage results across the run.

Does NOT:
    - Connect to live Sources of Truth.
    - Connect to the live AlphaOmega database.
    - Test UI or application admission.
    - Bypass synchronization stage boundaries.
"""

from types import SimpleNamespace
from unittest.mock import Mock

from scripts.orchestration.sync_orchestrator import (
    SynchronizationOrchestrator,
)

from scripts.sync.sync_state import (
    SyncState,
)


# ============================================================================
# Synthetic Locked Section
# ============================================================================


class SyntheticSection:
    """
    Minimal locked section used by isolated orchestration tests.
    """

    def __init__(
        self,
        **values,
    ):
        self.is_locked = True

        for name, value in values.items():
            setattr(
                self,
                name,
                value,
            )


# ============================================================================
# Synthetic Connector
# ============================================================================


class SyntheticConnector:
    """
    Produce three canonical synthetic Connector objects.

    These objects intentionally follow the actual Connector ->
    TranslationInput boundary contract:

        source_object_type
        raw_object
        connector_metadata
    """

    def __init__(self):
        self.run_calls = []

    def run(
        self,
        source_name,
    ):
        self.run_calls.append(
            source_name
        )

        raw_objects = (
            {
                "source_object_type":
                    "driveItem",

                "raw_object":
                    {
                        "id":
                            "source-new",

                        "name":
                            "New Object",

                        "file":
                            {
                                "mimeType":
                                    "text/plain",
                            },
                    },

                "connector_metadata":
                    {},
            },

            {
                "source_object_type":
                    "driveItem",

                "raw_object":
                    {
                        "id":
                            "source-modified",

                        "name":
                            "Modified Object",

                        "file":
                            {
                                "mimeType":
                                    "text/plain",
                            },
                    },

                "connector_metadata":
                    {},
            },

            {
                "source_object_type":
                    "driveItem",

                "raw_object":
                    {
                        "id":
                            "source-unchanged",

                        "name":
                            "Unchanged Object",

                        "file":
                            {
                                "mimeType":
                                    "text/plain",
                            },
                    },

                "connector_metadata":
                    {},
            },
        )

        return SyntheticSection(
            source_name=source_name,
            raw_objects=raw_objects,
        )


# ============================================================================
# Synthetic Translator
# ============================================================================


class SyntheticTranslator:
    """
    Translate correlated Connector objects while preserving
    orchestration correlation identity.
    """

    def __init__(self):
        self.received_translation_input = None

    def run(
        self,
        translation_input,
    ):
        self.received_translation_input = (
            translation_input
        )

        records = []

        for correlated_object in (
            translation_input.raw_objects
        ):
            raw_object = (
                correlated_object[
                    "raw_object"
                ]
            )

            records.append(
                SimpleNamespace(
                    correlation_id=(
                        correlated_object[
                            "correlation_id"
                        ]
                    ),

                    source_name=
                        "OneDrive",

                    source_object_id=(
                        raw_object[
                            "id"
                        ]
                    ),

                    source_parent_object_id=
                        None,

                    source_path=
                        None,

                    source_url=
                        None,

                    name=(
                        raw_object[
                            "name"
                        ]
                    ),

                    object_type=
                        "CONTENT",

                    source_created_at=
                        None,

                    source_modified_at=
                        None,

                    metadata=
                        {},
                )
            )

        return SyntheticSection(
            translated_records=tuple(
                records
            ),
            record_errors=(),
        )


# ============================================================================
# Synthetic Discovery
# ============================================================================


class SyntheticDiscoveryService:
    """
    Classify the three synthetic records as NEW, MODIFIED,
    and UNCHANGED.
    """

    def __init__(self):
        self.received_translator_section = None

    def run(
        self,
        translator_section,
    ):
        self.received_translator_section = (
            translator_section
        )

        discovery_records = []

        for translator_record in (
            translator_section.translated_records
        ):
            source_object_id = (
                translator_record.source_object_id
            )

            if (
                source_object_id
                == "source-new"
            ):
                sync_state = (
                    SyncState.NEW
                )

                requires_extraction = (
                    True
                )

                knowledge_object_id = (
                    None
                )

                previous_content_hash = (
                    None
                )

            elif (
                source_object_id
                == "source-modified"
            ):
                sync_state = (
                    SyncState.MODIFIED
                )

                requires_extraction = (
                    True
                )

                knowledge_object_id = (
                    "ko-modified"
                )

                previous_content_hash = (
                    "old-modified-hash"
                )

            elif (
                source_object_id
                == "source-unchanged"
            ):
                sync_state = (
                    SyncState.UNCHANGED
                )

                requires_extraction = (
                    False
                )

                knowledge_object_id = (
                    "ko-unchanged"
                )

                previous_content_hash = (
                    "unchanged-hash"
                )

            else:
                raise RuntimeError(
                    "Unexpected synthetic object."
                )

            discovery_records.append(
                SimpleNamespace(
                    correlation_id=(
                        translator_record
                        .correlation_id
                    ),

                    sync_state=(
                        sync_state
                    ),

                    requires_extraction=(
                        requires_extraction
                    ),

                    knowledge_object_id=(
                        knowledge_object_id
                    ),

                    previous_content_hash=(
                        previous_content_hash
                    ),

                    comparison_reason=
                        None,
                )
            )

        return SyntheticSection(
            discovery_records=tuple(
                discovery_records
            ),
            record_errors=(),
        )


# ============================================================================
# Synthetic Extraction
# ============================================================================


class SyntheticExtractionService:
    """
    Extract only records routed by Orchestration.
    """

    def __init__(self):
        self.received_records = None

    def run(
        self,
        records,
    ):
        self.received_records = tuple(
            records
        )

        extraction_records = []

        for translator_record in (
            self.received_records
        ):
            extraction_records.append(
                SimpleNamespace(
                    correlation_id=(
                        translator_record
                        .correlation_id
                    ),

                    canonical_content=(
                        "Extracted content for "
                        + translator_record.name
                    ),

                    content_hash=(
                        "hash-"
                        + translator_record
                        .source_object_id
                    ),

                    canonical_metadata=
                        {},

                    extractor_name=
                        "SyntheticExtractor",

                    extraction_timestamp=
                        None,
                )
            )

        return SyntheticSection(
            extraction_records=tuple(
                extraction_records
            ),
            record_errors=(),
        )


# ============================================================================
# Synthetic Load
# ============================================================================


class SyntheticLoadService:
    """
    Capture associations routed to Load.
    """

    def __init__(self):
        self.received_associations = None
        self.processing_job_id = None

    def run(
        self,
        *,
        associations,
        processing_job_id,
    ):
        self.received_associations = tuple(
            associations
        )

        self.processing_job_id = (
            processing_job_id
        )

        return SyntheticSection(
            load_succeeded=True,
            record_errors=(),
        )


# ============================================================================
# Synthetic Processing Job Repository
# ============================================================================


class SyntheticProcessingJobRepository:
    """
    Capture Processing Job lifecycle operations.
    """

    def __init__(self):
        self.created = []
        self.completed = []
        self.failed = []

        self.processing_job_id = (
            "processing-job-123"
        )

    def create(
        self,
        *,
        process_type,
        pipeline_version,
        metadata,
    ):
        self.created.append(
            {
                "process_type":
                    process_type,

                "pipeline_version":
                    pipeline_version,

                "metadata":
                    metadata,
            }
        )

        return self.processing_job_id

    def complete(
        self,
        processing_job_id,
    ):
        self.completed.append(
            processing_job_id
        )

    def fail(
        self,
        processing_job_id,
        error,
    ):
        self.failed.append(
            (
                processing_job_id,
                error,
            )
        )


# ============================================================================
# Infrastructure
# ============================================================================


def build_orchestrator():
    """
    Build one fully synthetic orchestration environment.
    """

    connector = (
        SyntheticConnector()
    )

    translator = (
        SyntheticTranslator()
    )

    discovery_service = (
        SyntheticDiscoveryService()
    )

    extraction_service = (
        SyntheticExtractionService()
    )

    load_service = (
        SyntheticLoadService()
    )

    processing_job_repository = (
        SyntheticProcessingJobRepository()
    )

    orchestrator = (
        SynchronizationOrchestrator(
            connector=connector,

            translator=translator,

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
                "lab7-orchestration"
            ),
        )
    )

    return (
        orchestrator,
        connector,
        translator,
        discovery_service,
        extraction_service,
        load_service,
        processing_job_repository,
    )


# ============================================================================
# Primary Routing Test
# ============================================================================


def test_new_modified_unchanged_routing():
    """
    Verify complete synthetic orchestration routing.
    """

    (
        orchestrator,
        connector,
        translator,
        discovery_service,
        extraction_service,
        load_service,
        processing_job_repository,
    ) = build_orchestrator()

    result = orchestrator.run(
        source_name="OneDrive",

        job_metadata={
            "test":
                "synthetic-orchestration",
        },
    )

    if (
        len(
            processing_job_repository.created
        )
        != 1
    ):
        raise AssertionError(
            "Processing Job was not created exactly once."
        )

    created_job = (
        processing_job_repository.created[
            0
        ]
    )

    if (
        created_job[
            "process_type"
        ]
        != "sync"
    ):
        raise AssertionError(
            "Processing Job process_type incorrect."
        )

    if (
        created_job[
            "pipeline_version"
        ]
        != "lab7-orchestration"
    ):
        raise AssertionError(
            "Processing Job pipeline version incorrect."
        )

    if (
        connector.run_calls
        != ["OneDrive"]
    ):
        raise AssertionError(
            "Connector did not receive the expected Source."
        )

    raw_objects = (
        translator
        .received_translation_input
        .raw_objects
    )

    if (
        len(
            raw_objects
        )
        != 3
    ):
        raise AssertionError(
            "TranslationInput did not contain three objects."
        )

    correlation_ids = [
        item[
            "correlation_id"
        ]
        for item
        in raw_objects
    ]

    if (
        len(
            set(
                correlation_ids
            )
        )
        != 3
    ):
        raise AssertionError(
            "Correlation IDs are not unique."
        )

    if any(
        correlation_id is None
        for correlation_id
        in correlation_ids
    ):
        raise AssertionError(
            "Missing orchestration correlation identity."
        )

    associations = (
        result[
            "associations"
        ]
    )

    if (
        len(
            associations
        )
        != 3
    ):
        raise AssertionError(
            "Expected exactly three associations."
        )

    for association in associations:

        if (
            association.translator_record
            is None
        ):
            raise AssertionError(
                "Association missing TranslatorRecord."
            )

        if (
            association.discovery_record
            is None
        ):
            raise AssertionError(
                "Association missing DiscoveryRecord."
            )

    for association in associations:

        correlation_id = (
            association.correlation_id
        )

        if (
            association
            .translator_record
            .correlation_id
            != correlation_id
        ):
            raise AssertionError(
                "Translator correlation identity mismatch."
            )

        if (
            association
            .discovery_record
            .correlation_id
            != correlation_id
        ):
            raise AssertionError(
                "Discovery correlation identity mismatch."
            )

    extraction_inputs = (
        extraction_service
        .received_records
    )

    if (
        extraction_inputs
        is None
    ):
        raise AssertionError(
            "Extraction was not invoked."
        )

    extracted_source_ids = {
        record.source_object_id
        for record
        in extraction_inputs
    }

    expected_extracted_ids = {
        "source-new",
        "source-modified",
    }

    if (
        extracted_source_ids
        != expected_extracted_ids
    ):
        raise AssertionError(
            "Extraction routing incorrect."
        )

    if (
        "source-unchanged"
        in extracted_source_ids
    ):
        raise AssertionError(
            "UNCHANGED record reached Extraction."
        )

    load_associations = (
        load_service
        .received_associations
    )

    if (
        load_associations
        is None
    ):
        raise AssertionError(
            "Load was not invoked."
        )

    loaded_source_ids = {
        association
        .translator_record
        .source_object_id

        for association
        in load_associations
    }

    if (
        loaded_source_ids
        != expected_extracted_ids
    ):
        raise AssertionError(
            "Load routing incorrect."
        )

    if (
        load_service.processing_job_id
        != "processing-job-123"
    ):
        raise AssertionError(
            "Processing Job identity was not propagated "
            "to Load."
        )

    for association in (
        load_associations
    ):

        if (
            association.extraction_record
            is None
        ):
            raise AssertionError(
                "Load association missing ExtractionRecord."
            )

        if (
            association
            .extraction_record
            .correlation_id
            != association.correlation_id
        ):
            raise AssertionError(
                "Extraction correlation identity mismatch."
            )

    unchanged_association = next(
        association

        for association
        in associations

        if (
            association
            .translator_record
            .source_object_id
            == "source-unchanged"
        )
    )

    if (
        unchanged_association
        .discovery_record
        .sync_state
        != SyncState.UNCHANGED
    ):
        raise AssertionError(
            "Expected UNCHANGED association was not UNCHANGED."
        )

    if (
        unchanged_association
        .extraction_record
        is not None
    ):
        raise AssertionError(
            "UNCHANGED association received an ExtractionRecord."
        )

    if (
        processing_job_repository.completed
        != [
            "processing-job-123"
        ]
    ):
        raise AssertionError(
            "Processing Job was not completed correctly."
        )

    if (
        processing_job_repository.failed
    ):
        raise AssertionError(
            "Successful synchronization was marked failed."
        )

    expected_counts = {
        "associations":
            3,

        "translated":
            3,

        "discovered":
            3,

        "extracted":
            2,

        "new":
            1,

        "modified":
            1,

        "unchanged":
            1,
    }

    if (
        result[
            "counts"
        ]
        != expected_counts
    ):
        raise AssertionError(
            "Orchestration counts incorrect.\n"
            f"Expected: {expected_counts}\n"
            f"Actual:   {result['counts']}"
        )

    print(
        "PASS: NEW/MODIFIED/UNCHANGED routing correct."
    )

    print(
        "PASS: Correlation identity created and preserved."
    )

    print(
        "PASS: UNCHANGED stopped before Extraction."
    )

    print(
        "PASS: NEW and MODIFIED routed through Extraction."
    )

    print(
        "PASS: Successfully extracted records routed to Load."
    )

    print(
        "PASS: Processing Job identity propagated to Load."
    )

    print(
        "PASS: Processing Job completed."
    )

    print(
        "PASS: Orchestration counts correct."
    )


# ============================================================================
# Constructor Validation
# ============================================================================


def test_required_dependencies():
    """
    Verify all orchestration dependencies are required.
    """

    valid = {
        "connector":
            Mock(),

        "translator":
            Mock(),

        "discovery_service":
            Mock(),

        "extraction_service":
            Mock(),

        "load_service":
            Mock(),

        "processing_job_repository":
            Mock(),

        "pipeline_version":
            "test",
    }

    dependency_names = (
        "connector",
        "translator",
        "discovery_service",
        "extraction_service",
        "load_service",
        "processing_job_repository",
    )

    for dependency_name in (
        dependency_names
    ):

        arguments = dict(
            valid
        )

        arguments[
            dependency_name
        ] = None

        try:
            SynchronizationOrchestrator(
                **arguments
            )

            raise AssertionError(
                f"Missing {dependency_name} was accepted."
            )

        except ValueError:
            pass

    for pipeline_version in (
        None,
        "",
        "   ",
    ):

        arguments = dict(
            valid
        )

        arguments[
            "pipeline_version"
        ] = pipeline_version

        try:
            SynchronizationOrchestrator(
                **arguments
            )

            raise AssertionError(
                "Invalid pipeline_version was accepted."
            )

        except ValueError:
            pass

    print(
        "PASS: Required orchestration dependencies validated."
    )


# ============================================================================
# Run Request Validation
# ============================================================================


def test_source_name_required():
    """
    Verify a Source name is required before a Processing Job
    is created.
    """

    (
        orchestrator,
        _connector,
        _translator,
        _discovery_service,
        _extraction_service,
        _load_service,
        processing_job_repository,
    ) = build_orchestrator()

    for source_name in (
        None,
        "",
        "   ",
    ):

        try:
            orchestrator.run(
                source_name=source_name
            )

            raise AssertionError(
                "Invalid source_name was accepted."
            )

        except ValueError:
            pass

    if (
        processing_job_repository.created
    ):
        raise AssertionError(
            "Processing Job was created for an invalid request."
        )

    print(
        "PASS: Invalid Source request rejected before job creation."
    )


# ============================================================================
# Stage-Level Failure
# ============================================================================


class FailingConnector:
    """
    Synthetic Connector with a stage-level failure.
    """

    def run(
        self,
        source_name,
    ):
        raise RuntimeError(
            "Synthetic Connector stage failure."
        )


def test_stage_failure_fails_processing_job():
    """
    Verify a stage-level failure stops execution and marks the
    existing Processing Job failed.
    """

    translator = Mock()
    discovery_service = Mock()
    extraction_service = Mock()
    load_service = Mock()

    processing_job_repository = (
        SyntheticProcessingJobRepository()
    )

    orchestrator = (
        SynchronizationOrchestrator(
            connector=(
                FailingConnector()
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
                "test"
            ),
        )
    )

    try:
        orchestrator.run(
            source_name="OneDrive"
        )

        raise AssertionError(
            "Connector stage failure did not escape "
            "Orchestration."
        )

    except RuntimeError as error:

        if (
            str(
                error
            )
            != "Synthetic Connector stage failure."
        ):
            raise

    if (
        len(
            processing_job_repository.created
        )
        != 1
    ):
        raise AssertionError(
            "Processing Job was not created before Connector."
        )

    if (
        processing_job_repository.completed
    ):
        raise AssertionError(
            "Failed Processing Job was completed."
        )

    if (
        len(
            processing_job_repository.failed
        )
        != 1
    ):
        raise AssertionError(
            "Failed synchronization did not fail "
            "the Processing Job."
        )

    (
        failed_job_id,
        failed_error,
    ) = (
        processing_job_repository.failed[
            0
        ]
    )

    if (
        failed_job_id
        != "processing-job-123"
    ):
        raise AssertionError(
            "Wrong Processing Job was marked failed."
        )

    if (
        str(
            failed_error
        )
        != "Synthetic Connector stage failure."
    ):
        raise AssertionError(
            "Processing Job failure did not preserve "
            "the stage error."
        )

    translator.run.assert_not_called()
    discovery_service.run.assert_not_called()
    extraction_service.run.assert_not_called()
    load_service.run.assert_not_called()

    print(
        "PASS: Stage-level failure stopped downstream execution."
    )

    print(
        "PASS: Stage-level failure marked Processing Job failed."
    )


# ============================================================================
# Record-Level Failure Isolation
# ============================================================================


class RecordFailureConnector:
    """
    Produce five canonical synthetic Connector objects.
    """

    def run(
        self,
        source_name,
    ):
        object_ids = (
            "source-new",
            "source-translator-failure",
            "source-extraction-failure",
            "source-unchanged",
            "source-modified",
        )

        raw_objects = []

        for object_id in object_ids:

            raw_objects.append(
                {
                    "source_object_type":
                        "driveItem",

                    "raw_object":
                        {
                            "id":
                                object_id,

                            "name":
                                object_id,

                            "file":
                                {
                                    "mimeType":
                                        "text/plain",
                                },
                        },

                    "connector_metadata":
                        {},
                }
            )

        return SyntheticSection(
            source_name=source_name,
            raw_objects=tuple(
                raw_objects
            ),
        )


class RecordFailureTranslator:
    """
    Simulate one Translator record-level failure.
    """

    def __init__(self):
        self.failed_correlation_id = None

    def run(
        self,
        translation_input,
    ):
        translated_records = []
        record_errors = []

        for correlated_object in (
            translation_input.raw_objects
        ):

            raw_object = (
                correlated_object[
                    "raw_object"
                ]
            )

            correlation_id = (
                correlated_object[
                    "correlation_id"
                ]
            )

            if (
                raw_object["id"]
                == "source-translator-failure"
            ):

                self.failed_correlation_id = (
                    correlation_id
                )

                record_errors.append(
                    {
                        "correlation_id":
                            correlation_id,

                        "source_object_id":
                            raw_object["id"],

                        "error_type":
                            "TranslatorRecordError",

                        "message":
                            "Synthetic Translator record failure.",
                    }
                )

                continue

            translated_records.append(
                SimpleNamespace(
                    correlation_id=(
                        correlation_id
                    ),

                    source_name=
                        "OneDrive",

                    source_object_id=(
                        raw_object["id"]
                    ),

                    source_parent_object_id=
                        None,

                    source_path=
                        None,

                    source_url=
                        None,

                    name=(
                        raw_object["name"]
                    ),

                    object_type=
                        "CONTENT",

                    source_created_at=
                        None,

                    source_modified_at=
                        None,

                    metadata=
                        {},
                )
            )

        return SyntheticSection(
            translated_records=tuple(
                translated_records
            ),
            record_errors=tuple(
                record_errors
            ),
        )


class RecordFailureDiscoveryService:
    """
    Classify every successfully translated record.
    """

    def run(
        self,
        translator_section,
    ):
        discovery_records = []

        for translator_record in (
            translator_section.translated_records
        ):

            source_object_id = (
                translator_record.source_object_id
            )

            if (
                source_object_id
                == "source-new"
            ):

                sync_state = (
                    SyncState.NEW
                )

                requires_extraction = (
                    True
                )

                knowledge_object_id = (
                    None
                )

                previous_content_hash = (
                    None
                )

            elif (
                source_object_id
                == "source-unchanged"
            ):

                sync_state = (
                    SyncState.UNCHANGED
                )

                requires_extraction = (
                    False
                )

                knowledge_object_id = (
                    "ko-unchanged"
                )

                previous_content_hash = (
                    "unchanged-hash"
                )

            else:

                sync_state = (
                    SyncState.MODIFIED
                )

                requires_extraction = (
                    True
                )

                knowledge_object_id = (
                    "ko-"
                    + source_object_id
                )

                previous_content_hash = (
                    "old-hash-"
                    + source_object_id
                )

            discovery_records.append(
                SimpleNamespace(
                    correlation_id=(
                        translator_record
                        .correlation_id
                    ),

                    sync_state=(
                        sync_state
                    ),

                    requires_extraction=(
                        requires_extraction
                    ),

                    knowledge_object_id=(
                        knowledge_object_id
                    ),

                    previous_content_hash=(
                        previous_content_hash
                    ),

                    comparison_reason=
                        None,
                )
            )

        return SyntheticSection(
            discovery_records=tuple(
                discovery_records
            ),
            record_errors=(),
        )


class RecordFailureExtractionService:
    """
    Simulate one Extraction record-level failure.
    """

    def __init__(self):
        self.received_records = None
        self.failed_correlation_id = None

    def run(
        self,
        records,
    ):
        self.received_records = tuple(
            records
        )

        extraction_records = []
        record_errors = []

        for translator_record in (
            self.received_records
        ):

            if (
                translator_record.source_object_id
                == "source-extraction-failure"
            ):

                self.failed_correlation_id = (
                    translator_record
                    .correlation_id
                )

                record_errors.append(
                    {
                        "correlation_id":
                            translator_record
                            .correlation_id,

                        "source_object_id":
                            translator_record
                            .source_object_id,

                        "error_type":
                            "ExtractionRecordError",

                        "message":
                            "Synthetic Extraction record failure.",
                    }
                )

                continue

            extraction_records.append(
                SimpleNamespace(
                    correlation_id=(
                        translator_record
                        .correlation_id
                    ),

                    canonical_content=(
                        "Extracted content for "
                        + translator_record.name
                    ),

                    content_hash=(
                        "hash-"
                        + translator_record
                        .source_object_id
                    ),

                    canonical_metadata=
                        {},

                    extractor_name=
                        "SyntheticExtractor",

                    extraction_timestamp=
                        None,
                )
            )

        return SyntheticSection(
            extraction_records=tuple(
                extraction_records
            ),
            record_errors=tuple(
                record_errors
            ),
        )


def test_record_level_failure_isolation():
    """
    Verify record-level failures stop only the affected record.
    """

    connector = (
        RecordFailureConnector()
    )

    translator = (
        RecordFailureTranslator()
    )

    discovery_service = (
        RecordFailureDiscoveryService()
    )

    extraction_service = (
        RecordFailureExtractionService()
    )

    load_service = (
        SyntheticLoadService()
    )

    processing_job_repository = (
        SyntheticProcessingJobRepository()
    )

    orchestrator = (
        SynchronizationOrchestrator(
            connector=connector,

            translator=translator,

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
                "record-failure-test"
            ),
        )
    )

    result = orchestrator.run(
        source_name="OneDrive",

        job_metadata={
            "test":
                "record-failure-isolation",
        },
    )

    if (
        len(
            result["associations"]
        )
        != 5
    ):
        raise AssertionError(
            "Expected five orchestration associations."
        )

    translator_failure_association = next(
        association

        for association
        in result["associations"]

        if (
            association.correlation_id
            == translator.failed_correlation_id
        )
    )

    if (
        translator_failure_association
        .translator_record
        is not None
    ):
        raise AssertionError(
            "Translator-failed record received "
            "a TranslatorRecord."
        )

    if (
        translator_failure_association
        .discovery_record
        is not None
    ):
        raise AssertionError(
            "Translator-failed record reached Discovery."
        )

    if (
        translator_failure_association
        .extraction_record
        is not None
    ):
        raise AssertionError(
            "Translator-failed record reached Extraction."
        )

    if (
        result["counts"]["translated"]
        != 4
    ):
        raise AssertionError(
            "Translator failure did not reduce translated count."
        )

    if (
        result["counts"]["discovered"]
        != 4
    ):
        raise AssertionError(
            "Translator-failed record leaked into Discovery."
        )

    extraction_source_ids = {
        record.source_object_id

        for record
        in extraction_service.received_records
    }

    expected_extraction_ids = {
        "source-new",
        "source-extraction-failure",
        "source-modified",
    }

    if (
        extraction_source_ids
        != expected_extraction_ids
    ):
        raise AssertionError(
            "Extraction record-level routing incorrect.\n"
            f"Expected: {expected_extraction_ids}\n"
            f"Actual:   {extraction_source_ids}"
        )

    extraction_failure_association = next(
        association

        for association
        in result["associations"]

        if (
            association.correlation_id
            == extraction_service
            .failed_correlation_id
        )
    )

    if (
        extraction_failure_association
        .translator_record
        is None
    ):
        raise AssertionError(
            "Extraction-failed record lost TranslatorRecord."
        )

    if (
        extraction_failure_association
        .discovery_record
        is None
    ):
        raise AssertionError(
            "Extraction-failed record lost DiscoveryRecord."
        )

    if (
        extraction_failure_association
        .extraction_record
        is not None
    ):
        raise AssertionError(
            "Extraction-failed record received "
            "an ExtractionRecord."
        )

    loaded_source_ids = {
        association
        .translator_record
        .source_object_id

        for association
        in load_service.received_associations
    }

    expected_loaded_ids = {
        "source-new",
        "source-modified",
    }

    if (
        loaded_source_ids
        != expected_loaded_ids
    ):
        raise AssertionError(
            "Record-level failure leaked into Load.\n"
            f"Expected: {expected_loaded_ids}\n"
            f"Actual:   {loaded_source_ids}"
        )

    for association in (
        load_service.received_associations
    ):

        if (
            association
            .translator_record
            .correlation_id
            != association.correlation_id
        ):
            raise AssertionError(
                "Translator correlation identity changed."
            )

        if (
            association
            .discovery_record
            .correlation_id
            != association.correlation_id
        ):
            raise AssertionError(
                "Discovery correlation identity changed."
            )

        if (
            association
            .extraction_record
            .correlation_id
            != association.correlation_id
        ):
            raise AssertionError(
                "Extraction correlation identity changed."
            )

    unchanged_association = next(
        association

        for association
        in result["associations"]

        if (
            association.translator_record
            is not None

            and

            association
            .translator_record
            .source_object_id
            == "source-unchanged"
        )
    )

    if (
        unchanged_association
        .discovery_record
        .sync_state
        != SyncState.UNCHANGED
    ):
        raise AssertionError(
            "UNCHANGED record was classified incorrectly."
        )

    if (
        unchanged_association
        .extraction_record
        is not None
    ):
        raise AssertionError(
            "UNCHANGED record reached Extraction."
        )

    if (
        processing_job_repository.completed
        != [
            "processing-job-123"
        ]
    ):
        raise AssertionError(
            "Processing Job did not complete."
        )

    if (
        processing_job_repository.failed
    ):
        raise AssertionError(
            "Record-level failure incorrectly failed "
            "the Processing Job."
        )

    expected_counts = {
        "associations":
            5,

        "translated":
            4,

        "discovered":
            4,

        "extracted":
            2,

        "new":
            1,

        "modified":
            2,

        "unchanged":
            1,
    }

    if (
        result["counts"]
        != expected_counts
    ):
        raise AssertionError(
            "Record-level failure counts incorrect.\n"
            f"Expected: {expected_counts}\n"
            f"Actual:   {result['counts']}"
        )

    print(
        "PASS: Translator record-level failure isolated."
    )

    print(
        "PASS: Translator-failed record stopped before Discovery."
    )

    print(
        "PASS: Extraction record-level failure isolated."
    )

    print(
        "PASS: Extraction-failed record stopped before Load."
    )

    print(
        "PASS: UNCHANGED record stopped normally."
    )

    print(
        "PASS: Healthy records continued through Load."
    )

    print(
        "PASS: Healthy correlation identities preserved."
    )

    print(
        "PASS: Record-level failures did not fail Processing Job."
    )

    print(
        "PASS: Record-level failure orchestration counts correct."
    )


# ============================================================================
# MODIFIED Same-Hash Load Gate
# ============================================================================


class SameHashConnector:
    """
    Produce one synthetic object for the same-hash routing test.
    """

    def run(
        self,
        source_name,
    ):
        return SyntheticSection(
            source_name=source_name,

            raw_objects=(
                {
                    "source_object_type":
                        "driveItem",

                    "raw_object":
                        {
                            "id":
                                "source-same-hash",

                            "name":
                                "Same Hash Object",

                            "file":
                                {
                                    "mimeType":
                                        "text/plain",
                                },
                        },

                    "connector_metadata":
                        {},
                },
            ),
        )


class SameHashTranslator:
    """
    Translate the same-hash synthetic object.
    """

    def run(
        self,
        translation_input,
    ):
        correlated_object = (
            translation_input.raw_objects[
                0
            ]
        )

        raw_object = (
            correlated_object[
                "raw_object"
            ]
        )

        record = SimpleNamespace(
            correlation_id=(
                correlated_object[
                    "correlation_id"
                ]
            ),

            source_name=
                "OneDrive",

            source_object_id=(
                raw_object[
                    "id"
                ]
            ),

            source_parent_object_id=
                None,

            source_path=
                None,

            source_url=
                None,

            name=(
                raw_object[
                    "name"
                ]
            ),

            object_type=
                "CONTENT",

            source_created_at=
                None,

            source_modified_at=
                None,

            metadata=
                {},
        )

        return SyntheticSection(
            translated_records=(
                record,
            ),

            record_errors=(),
        )


class SameHashDiscoveryService:
    """
    Classify the record MODIFIED while preserving the previous hash.
    """

    PREVIOUS_HASH = (
        "same-canonical-content-hash"
    )

    def run(
        self,
        translator_section,
    ):
        translator_record = (
            translator_section
            .translated_records[
                0
            ]
        )

        discovery_record = (
            SimpleNamespace(
                correlation_id=(
                    translator_record
                    .correlation_id
                ),

                sync_state=(
                    SyncState.MODIFIED
                ),

                requires_extraction=
                    True,

                knowledge_object_id=
                    "ko-same-hash",

                previous_content_hash=(
                    self.PREVIOUS_HASH
                ),

                comparison_reason=(
                    "source modified timestamp changed"
                ),
            )
        )

        return SyntheticSection(
            discovery_records=(
                discovery_record,
            ),

            record_errors=(),
        )


class SameHashExtractionService:
    """
    Extract successfully while producing the same canonical hash
    preserved by Discovery.
    """

    def __init__(self):
        self.received_records = None

    def run(
        self,
        records,
    ):
        self.received_records = tuple(
            records
        )

        translator_record = (
            self.received_records[
                0
            ]
        )

        extraction_record = (
            SimpleNamespace(
                correlation_id=(
                    translator_record
                    .correlation_id
                ),

                canonical_content=(
                    "Canonical content did not change."
                ),

                content_hash=(
                    SameHashDiscoveryService
                    .PREVIOUS_HASH
                ),

                canonical_metadata=
                    {},

                extractor_name=
                    "SyntheticExtractor",

                extraction_timestamp=
                    None,
            )
        )

        return SyntheticSection(
            extraction_records=(
                extraction_record,
            ),

            record_errors=(),
        )


class SameHashLoadService:
    """
    Fail immediately if a same-hash MODIFIED record reaches Load.
    """

    def __init__(self):
        self.called = False

    def run(
        self,
        *,
        associations,
        processing_job_id,
    ):
        self.called = True

        raise AssertionError(
            "Same-hash MODIFIED record incorrectly reached Load."
        )


def test_modified_same_hash_stops_before_load():
    """
    Verify the post-Extraction hash gate.

    Expected:

        MODIFIED
            -> Extraction
            -> same canonical hash
            -> STOP before Load

    Discovery remains MODIFIED.
    ExtractionRecord remains attached.
    Processing Job completes normally.
    """

    connector = (
        SameHashConnector()
    )

    translator = (
        SameHashTranslator()
    )

    discovery_service = (
        SameHashDiscoveryService()
    )

    extraction_service = (
        SameHashExtractionService()
    )

    load_service = (
        SameHashLoadService()
    )

    processing_job_repository = (
        SyntheticProcessingJobRepository()
    )

    orchestrator = (
        SynchronizationOrchestrator(
            connector=connector,

            translator=translator,

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
                "same-hash-routing-test"
            ),
        )
    )

    result = (
        orchestrator.run(
            source_name="OneDrive",

            job_metadata={
                "test":
                    "modified-same-hash-gate",
            },
        )
    )

    associations = (
        result[
            "associations"
        ]
    )

    if (
        len(
            associations
        )
        != 1
    ):
        raise AssertionError(
            "Expected exactly one same-hash association."
        )

    association = (
        associations[
            0
        ]
    )

    if (
        association.discovery_record
        is None
    ):
        raise AssertionError(
            "Same-hash association lost DiscoveryRecord."
        )

    if (
        association
        .discovery_record
        .sync_state
        != SyncState.MODIFIED
    ):
        raise AssertionError(
            "Same-hash association was not preserved as MODIFIED."
        )

    if (
        association.extraction_record
        is None
    ):
        raise AssertionError(
            "Same-hash MODIFIED record lost ExtractionRecord."
        )

    if (
        extraction_service
        .received_records
        is None
        or
        len(
            extraction_service
            .received_records
        )
        != 1
    ):
        raise AssertionError(
            "Same-hash MODIFIED record did not reach Extraction."
        )

    if (
        association
        .extraction_record
        .content_hash
        !=
        association
        .discovery_record
        .previous_content_hash
    ):
        raise AssertionError(
            "Same-hash test did not produce matching hashes."
        )

    if (
        load_service.called
    ):
        raise AssertionError(
            "Same-hash MODIFIED record reached Load."
        )

    if (
        processing_job_repository
        .completed
        != [
            "processing-job-123"
        ]
    ):
        raise AssertionError(
            "Same-hash synchronization did not complete "
            "its Processing Job."
        )

    if (
        processing_job_repository
        .failed
    ):
        raise AssertionError(
            "Same-hash routing incorrectly failed "
            "the Processing Job."
        )

    expected_counts = {
        "associations":
            1,

        "translated":
            1,

        "discovered":
            1,

        "extracted":
            1,

        "new":
            0,

        "modified":
            1,

        "unchanged":
            0,
    }

    if (
        result[
            "counts"
        ]
        != expected_counts
    ):
        raise AssertionError(
            "Same-hash orchestration counts incorrect.\n"
            f"Expected: {expected_counts}\n"
            f"Actual:   {result['counts']}"
        )

    print(
        "PASS: MODIFIED same-hash record reached Extraction."
    )

    print(
        "PASS: MODIFIED same-hash ExtractionRecord preserved."
    )

    print(
        "PASS: MODIFIED same-hash record stopped before Load."
    )

    print(
        "PASS: MODIFIED same-hash Processing Job completed."
    )

    print(
        "PASS: MODIFIED same-hash orchestration counts correct."
    )


# ============================================================================
# Main
# ============================================================================


def main():
    """
    Run isolated SynchronizationOrchestrator tests.
    """

    print()

    print(
        "Running SynchronizationOrchestrator isolated tests..."
    )

    print()

    test_required_dependencies()

    test_source_name_required()

    test_new_modified_unchanged_routing()

    test_stage_failure_fails_processing_job()

    test_record_level_failure_isolation()

    test_modified_same_hash_stops_before_load()

    print()

    print(
        "SynchronizationOrchestrator isolated tests PASSED."
    )

    print()


if __name__ == "__main__":
    main()