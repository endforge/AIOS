"""
AlphaOmega Synchronization Orchestrator

Purpose:
    Coordinates execution of the AlphaOmega synchronization pipeline for one
    requested Source.

Responsibilities:
    - Support the existing synchronization path that creates its own
      Processing Job and executes its configured Connector.
    - Support the production application path that consumes an already
      reserved Processing Job and completed ConnectorSection.
    - Assign orchestration correlation identity before Translation.
    - Execute Translator processing.
    - Preserve CONTAINER objects at their synchronization boundary.
    - Execute Discovery for eligible CONTENT.
    - Route NEW and MODIFIED records requiring Extraction.
    - Execute Extraction for eligible records.
    - Stop MODIFIED records before Load when canonical content is unchanged.
    - Execute Load for eligible changed content.
    - Maintain cross-stage synchronization associations.
    - Complete or fail the applicable Processing Job based on execution
      outcome.

Does NOT:
    - Provide UI presentation.
    - Perform application-layer synchronization admission.
    - Select synchronization scope.
    - Refresh the Source Container Catalog.
    - Reserve synchronization.
    - Create a second Processing Job for an already-reserved synchronization.
    - Reimplement stage-owned business logic.
    - Treat CONTAINER objects as Knowledge Objects.
"""

from common.object_types import (
    CONTENT,
)

from scripts.sync.sync_translation_input import (
    TranslationInput,
)

from scripts.sync.sync_association import (
    SynchronizationAssociation,
)

from scripts.sync.sync_state import (
    SyncState,
)


# ============================================================================
# Discovery Input View
# ============================================================================

class _DiscoveryInputView:
    """
    Orchestration-owned routing view supplied to Discovery.

    This is intentionally NOT a TranslatorSection.

    Translator owns the complete TranslatorSection and locks it after
    successful completion.

    Orchestration owns downstream routing. This view exposes only the
    successfully translated canonical CONTENT records that are eligible
    to enter Discovery while leaving the original TranslatorSection
    unchanged.
    """

    def __init__(
        self,
        translated_records,
    ):
        """
        Store the routed Translator records as an immutable tuple.
        """

        self.translated_records = tuple(
            translated_records
        )


class SynchronizationOrchestrator:
    """
    Coordinate one AlphaOmega synchronization run.
    """

    def __init__(
        self,
        *,
        connector,
        translator,
        discovery_service,
        extraction_service,
        load_service,
        processing_job_repository,
        pipeline_version,
    ):
        """
        Initialize orchestration dependencies.

        connector remains required for the existing self-created-job
        execution path.

        Reserved execution receives its completed ConnectorSection from the
        production application boundary and therefore does not invoke this
        configured Connector.
        """

        if connector is None:
            raise ValueError(
                "Connector is required."
            )

        if translator is None:
            raise ValueError(
                "Translator is required."
            )

        if discovery_service is None:
            raise ValueError(
                "DiscoveryService is required."
            )

        if extraction_service is None:
            raise ValueError(
                "ExtractionService is required."
            )

        if load_service is None:
            raise ValueError(
                "LoadService is required."
            )

        if processing_job_repository is None:
            raise ValueError(
                "ProcessingJobRepository is required."
            )

        if (
            pipeline_version is None
            or not str(
                pipeline_version
            ).strip()
        ):
            raise ValueError(
                "pipeline_version is required."
            )

        self._connector = connector
        self._translator = translator

        self._discovery_service = (
            discovery_service
        )

        self._extraction_service = (
            extraction_service
        )

        self._load_service = (
            load_service
        )

        self._processing_job_repository = (
            processing_job_repository
        )

        self._pipeline_version = (
            str(
                pipeline_version
            ).strip()
        )

    # ========================================================================
    # Existing Execution Path
    # ========================================================================

    def run(
        self,
        *,
        source_name,
        job_metadata=None,
    ):
        """
        Execute the existing synchronization path.

        This path preserves the established Lab 7 behavior:

            1. Create Processing Job.
            2. Execute configured Connector.
            3. Execute the synchronization pipeline.
            4. Complete or fail the created Processing Job.

        This method remains available for existing callers that have not
        already reserved synchronization through the Lab 8 application
        boundary.
        """

        self._validate_run_request(
            source_name
        )

        if job_metadata is None:
            job_metadata = {}

        processing_job_id = None

        try:

            processing_job_id = (
                self._processing_job_repository.create(
                    process_type="sync",
                    pipeline_version=(
                        self._pipeline_version
                    ),
                    metadata=job_metadata,
                )
            )

            connector_section = (
                self._connector.run(
                    source_name
                )
            )

            return self._execute_pipeline(
                processing_job_id=(
                    processing_job_id
                ),
                connector_section=(
                    connector_section
                ),
            )

        except Exception as error:

            self._fail_processing_job(
                processing_job_id=(
                    processing_job_id
                ),
                error=error,
            )

            raise

    # ========================================================================
    # Reserved Production Execution Path
    # ========================================================================

    def run_reserved(
        self,
        *,
        processing_job_id,
        connector_section,
    ):
        """
        Execute synchronization using an already-reserved Processing Job.

        This is the production Lab 8 orchestration entry point.

        The synchronization application boundary is responsible for:

            - persisted admission;
            - preliminary conflict information;
            - Source-of-Truth validation;
            - authoritative atomic reservation;
            - Source-specific synchronization scope selection;
            - Connector execution for the authorized scope.

        By the time this method is called:

            - processing_job_id already exists;
            - the Processing Job is already running;
            - the Synchronization Run already exists;
            - Connector execution has completed;
            - connector_section represents only the authorized scope.

        This method MUST NOT create another Processing Job.
        """

        processing_job_id = (
            self._require_text(
                processing_job_id,
                "processing_job_id",
            )
        )

        if connector_section is None:
            raise ValueError(
                "connector_section is required."
            )

        try:

            return self._execute_pipeline(
                processing_job_id=(
                    processing_job_id
                ),
                connector_section=(
                    connector_section
                ),
            )

        except Exception as error:

            self._fail_processing_job(
                processing_job_id=(
                    processing_job_id
                ),
                error=error,
            )

            raise

    # ========================================================================
    # Shared Synchronization Pipeline
    # ========================================================================

    def _execute_pipeline(
        self,
        *,
        processing_job_id,
        connector_section,
    ):
        """
        Execute the common synchronization pipeline from Connector output.

        Both execution paths converge here.

        This method owns:

            ConnectorSection validation
                ↓
            TranslationInput
                ↓
            SynchronizationAssociation construction
                ↓
            Translator
                ↓
            Discovery routing
                ↓
            Discovery
                ↓
            Extraction routing
                ↓
            Extraction
                ↓
            Load routing
                ↓
            Load
                ↓
            Processing Job completion

        Processing Job creation and Connector selection intentionally occur
        outside this shared method.
        """

        # ====================================================================
        # Connector
        # ====================================================================

        self._validate_locked_section(
            connector_section,
            "ConnectorSection",
        )

        # ====================================================================
        # Correlation Boundary
        #
        # TranslationInput assigns one orchestration-owned correlation UUID
        # to each Connector object.
        # ====================================================================

        translation_input = (
            TranslationInput(
                connector_section
            )
        )

        # ====================================================================
        # Build Associations
        #
        # Associations exist for every Connector object before Translator
        # begins.
        #
        # This includes both canonical CONTENT and CONTAINER objects.
        # ====================================================================

        associations = (
            self._create_associations(
                translation_input
            )
        )

        # ====================================================================
        # Translator
        # ====================================================================

        translator_section = (
            self._translator.run(
                translation_input
            )
        )

        self._validate_locked_section(
            translator_section,
            "TranslatorSection",
        )

        self._attach_translator_records(
            associations=associations,
            translator_section=(
                translator_section
            ),
        )

        # ====================================================================
        # Discovery Routing
        #
        # Translator owns the complete TranslatorSection.
        #
        # Orchestration owns routing.
        #
        # Only canonical CONTENT records are eligible to enter Discovery.
        #
        # CONTAINER records terminate successfully after Translator.
        # Their SynchronizationAssociation remains available for correlation,
        # diagnostics, and hierarchy traceability.
        # ====================================================================

        discovery_records = (
            self._select_discovery_records(
                translator_section
            )
        )

        discovery_section = None

        if discovery_records:

            discovery_input = (
                _DiscoveryInputView(
                    discovery_records
                )
            )

            # ================================================================
            # Discovery
            # ================================================================

            discovery_section = (
                self._discovery_service.run(
                    discovery_input
                )
            )

            self._validate_locked_section(
                discovery_section,
                "DiscoverySection",
            )

            self._attach_discovery_records(
                associations=associations,
                discovery_section=(
                    discovery_section
                ),
            )

        # ====================================================================
        # Extraction Routing
        # ====================================================================

        extraction_associations = (
            self._select_extraction_associations(
                associations
            )
        )

        extraction_section = None
        load_section = None

        if extraction_associations:

            extraction_inputs = [
                association.translator_record
                for association
                in extraction_associations
            ]

            # ================================================================
            # Extraction
            # ================================================================

            extraction_section = (
                self._extraction_service.run(
                    extraction_inputs
                )
            )

            self._validate_locked_section(
                extraction_section,
                "ExtractionSection",
            )

            self._attach_extraction_records(
                associations=(
                    extraction_associations
                ),
                extraction_section=(
                    extraction_section
                ),
            )

            # ================================================================
            # Load Routing
            #
            # Records with Extraction record-level failures have no
            # ExtractionRecord and therefore stop here.
            #
            # MODIFIED records whose extracted content hash matches the
            # previous stored content hash also stop here because canonical
            # content did not change.
            # ================================================================

            load_associations = (
                self._select_load_associations(
                    extraction_associations
                )
            )

            if load_associations:

                load_section = (
                    self._load_service.run(
                        associations=(
                            load_associations
                        ),
                        processing_job_id=(
                            processing_job_id
                        ),
                    )
                )

                self._validate_locked_section(
                    load_section,
                    "LoadSection",
                )

        # ====================================================================
        # Complete Processing Job
        # ====================================================================

        self._processing_job_repository.complete(
            processing_job_id
        )

        return {
            "processing_job_id":
                processing_job_id,

            "connector_section":
                connector_section,

            "translator_section":
                translator_section,

            "discovery_section":
                discovery_section,

            "extraction_section":
                extraction_section,

            "load_section":
                load_section,

            "associations":
                tuple(
                    associations.values()
                ),

            "counts":
                self._build_counts(
                    associations
                ),
        }

    # ========================================================================
    # Processing Job Failure
    # ========================================================================

    def _fail_processing_job(
        self,
        *,
        processing_job_id,
        error,
    ):
        """
        Fail the applicable Processing Job after synchronization failure.

        No action occurs when a Processing Job has not yet been established.

        If synchronization fails and the Processing Job also cannot be marked
        failed, raise a lifecycle error because persisted execution state can
        no longer be trusted.
        """

        if processing_job_id is None:
            return

        try:

            self._processing_job_repository.fail(
                processing_job_id,
                error,
            )

        except Exception as job_error:

            raise RuntimeError(
                "Synchronization failed and the "
                "Processing Job could not be marked failed."
            ) from job_error

    # ========================================================================
    # Association Construction
    # ========================================================================

    @staticmethod
    def _create_associations(
        translation_input,
    ):
        """
        Create one orchestration-owned association for every
        correlated Connector object.
        """

        associations = {}

        for correlated_object in (
            translation_input.raw_objects
        ):

            correlation_id = (
                correlated_object[
                    "correlation_id"
                ]
            )

            if correlation_id in associations:
                raise RuntimeError(
                    "Duplicate orchestration correlation_id."
                )

            associations[
                correlation_id
            ] = (
                SynchronizationAssociation(
                    correlation_id
                )
            )

        return associations

    # ========================================================================
    # Translator Association
    # ========================================================================

    @staticmethod
    def _attach_translator_records(
        *,
        associations,
        translator_section,
    ):
        """
        Attach successfully translated records by correlation ID.

        Translator record-level failures remain without a
        TranslatorRecord and stop downstream.
        """

        for translator_record in (
            translator_section.translated_records
        ):

            correlation_id = (
                translator_record.correlation_id
            )

            association = (
                associations.get(
                    correlation_id
                )
            )

            if association is None:
                raise RuntimeError(
                    "Translator produced an unknown "
                    "correlation_id."
                )

            association.attach_translator(
                translator_record
            )

    # ========================================================================
    # Discovery Routing
    # ========================================================================

    @staticmethod
    def _select_discovery_records(
        translator_section,
    ):
        """
        Select canonical CONTENT TranslatorRecords for Discovery.

        CONTAINER records terminate successfully after Translator.

        TranslatorSection remains unchanged and continues to contain
        the complete Translator output.
        """

        eligible = []

        for translator_record in (
            translator_section.translated_records
        ):

            if (
                translator_record.object_type
                != CONTENT
            ):
                continue

            eligible.append(
                translator_record
            )

        return tuple(
            eligible
        )

    # ========================================================================
    # Discovery Association
    # ========================================================================

    @staticmethod
    def _attach_discovery_records(
        *,
        associations,
        discovery_section,
    ):
        """
        Attach successfully discovered CONTENT records by correlation ID.
        """

        for discovery_record in (
            discovery_section.discovery_records
        ):

            correlation_id = (
                discovery_record.correlation_id
            )

            association = (
                associations.get(
                    correlation_id
                )
            )

            if association is None:
                raise RuntimeError(
                    "Discovery produced an unknown "
                    "correlation_id."
                )

            if (
                association.translator_record
                is None
            ):
                raise RuntimeError(
                    "Discovery record has no associated "
                    "TranslatorRecord."
                )

            if (
                association.translator_record.object_type
                != CONTENT
            ):
                raise RuntimeError(
                    "Discovery produced a record for a "
                    "non-CONTENT synchronization object."
                )

            association.attach_discovery(
                discovery_record
            )

    # ========================================================================
    # Extraction Routing
    # ========================================================================

    @staticmethod
    def _select_extraction_associations(
        associations,
    ):
        """
        Select CONTENT associations eligible for Extraction.

        Requirements:
            - TranslatorRecord exists.
            - TranslatorRecord is canonical CONTENT.
            - DiscoveryRecord exists.
            - Synchronization state is NEW or MODIFIED.
            - Discovery requires Extraction.

        UNCHANGED CONTENT records stop after Discovery.

        CONTAINER records cannot reach Extraction.
        """

        eligible = []

        for association in (
            associations.values()
        ):

            translator_record = (
                association.translator_record
            )

            if translator_record is None:
                continue

            if (
                translator_record.object_type
                != CONTENT
            ):
                continue

            discovery_record = (
                association.discovery_record
            )

            if discovery_record is None:
                continue

            if (
                discovery_record.sync_state
                not in (
                    SyncState.NEW,
                    SyncState.MODIFIED,
                )
            ):
                continue

            if (
                discovery_record.requires_extraction
                is not True
            ):
                continue

            eligible.append(
                association
            )

        return tuple(
            eligible
        )

    # ========================================================================
    # Load Routing
    # ========================================================================

    @staticmethod
    def _select_load_associations(
        extraction_associations,
    ):
        """
        Select successfully extracted CONTENT records eligible for Load.

        NEW records proceed to Load after successful Extraction.

        MODIFIED records proceed to Load only when the newly extracted
        canonical content hash differs from the previous stored hash.

        A MODIFIED record with matching hashes remains MODIFIED and retains
        its ExtractionRecord, but stops before Load because canonical content
        did not change.
        """

        eligible = []

        for association in (
            extraction_associations
        ):

            translator_record = (
                association.translator_record
            )

            if translator_record is None:
                continue

            if (
                translator_record.object_type
                != CONTENT
            ):
                continue

            extraction_record = (
                association.extraction_record
            )

            if extraction_record is None:
                continue

            discovery_record = (
                association.discovery_record
            )

            if discovery_record is None:
                continue

            if (
                discovery_record.sync_state
                == SyncState.NEW
            ):
                eligible.append(
                    association
                )

                continue

            if (
                discovery_record.sync_state
                != SyncState.MODIFIED
            ):
                continue

            previous_content_hash = (
                discovery_record
                .previous_content_hash
            )

            current_content_hash = (
                extraction_record
                .content_hash
            )

            if (
                previous_content_hash
                is not None
                and
                current_content_hash
                == previous_content_hash
            ):
                continue

            eligible.append(
                association
            )

        return tuple(
            eligible
        )

    # ========================================================================
    # Extraction Association
    # ========================================================================

    @staticmethod
    def _attach_extraction_records(
        *,
        associations,
        extraction_section,
    ):
        """
        Attach successful Extraction records by correlation ID.

        Only CONTENT associations are valid here.
        """

        association_map = {
            association.correlation_id:
                association
            for association
            in associations
        }

        for extraction_record in (
            extraction_section.extraction_records
        ):

            correlation_id = (
                extraction_record.correlation_id
            )

            association = (
                association_map.get(
                    correlation_id
                )
            )

            if association is None:
                raise RuntimeError(
                    "Extraction produced an unknown "
                    "correlation_id."
                )

            if (
                association.translator_record
                is None
            ):
                raise RuntimeError(
                    "Extraction record has no associated "
                    "TranslatorRecord."
                )

            if (
                association.translator_record.object_type
                != CONTENT
            ):
                raise RuntimeError(
                    "Extraction produced a record for a "
                    "non-CONTENT synchronization object."
                )

            association.attach_extraction(
                extraction_record
            )

    # ========================================================================
    # Section Validation
    # ========================================================================

    @staticmethod
    def _validate_locked_section(
        section,
        section_name,
    ):
        """
        Verify a successfully completed stage returned locked output.
        """

        if section is None:
            raise RuntimeError(
                f"{section_name} was not produced."
            )

        if not getattr(
            section,
            "is_locked",
            False,
        ):
            raise RuntimeError(
                f"{section_name} is not locked."
            )

    # ========================================================================
    # Counts
    # ========================================================================

    @staticmethod
    def _build_counts(
        associations,
    ):
        """
        Build orchestration-level synchronization counts.

        Association count includes every Connector object.

        Stage counts reflect actual stage participation:
            translated:
                every association with TranslatorRecord

            discovered:
                CONTENT associations with DiscoveryRecord

            extracted:
                CONTENT associations with ExtractionRecord

            NEW/MODIFIED/UNCHANGED:
                associations having the applicable Discovery state
        """

        values = tuple(
            associations.values()
        )

        translated = sum(
            1
            for association
            in values
            if association.translator_record
            is not None
        )

        discovered = sum(
            1
            for association
            in values
            if association.discovery_record
            is not None
        )

        extracted = sum(
            1
            for association
            in values
            if association.extraction_record
            is not None
        )

        new = sum(
            1
            for association
            in values
            if (
                association.discovery_record
                is not None
                and association.discovery_record.sync_state
                == SyncState.NEW
            )
        )

        modified = sum(
            1
            for association
            in values
            if (
                association.discovery_record
                is not None
                and association.discovery_record.sync_state
                == SyncState.MODIFIED
            )
        )

        unchanged = sum(
            1
            for association
            in values
            if (
                association.discovery_record
                is not None
                and association.discovery_record.sync_state
                == SyncState.UNCHANGED
            )
        )

        return {
            "associations":
                len(
                    values
                ),

            "translated":
                translated,

            "discovered":
                discovered,

            "extracted":
                extracted,

            "new":
                new,

            "modified":
                modified,

            "unchanged":
                unchanged,
        }

    # ========================================================================
    # Request Validation
    # ========================================================================

    @staticmethod
    def _validate_run_request(
        source_name,
    ):
        """
        Validate the existing synchronization request.
        """

        if (
            source_name is None
            or not str(
                source_name
            ).strip()
        ):
            raise ValueError(
                "source_name is required."
            )

    @staticmethod
    def _require_text(
        value,
        field_name,
    ):
        """
        Require one non-empty text value.
        """

        if (
            value is None
            or not str(
                value
            ).strip()
        ):
            raise ValueError(
                f"{field_name} is required."
            )

        return str(
            value
        ).strip()