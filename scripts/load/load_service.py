"""
AlphaOmega Load Service

Purpose:
    Executes the Load stage for synchronization associations eligible for
    persistence in the Canonical Knowledge Repository.

Responsibilities:
    - Validate required Translator, Discovery, and Extraction results.
    - Preserve orchestration correlation identity across Load.
    - Persist NEW Knowledge Objects.
    - Update MODIFIED Knowledge Objects.
    - Record synchronization history for persisted changes.
    - Reuse resolved Source identity within a Load run.
    - Isolate record-level Load failures.
    - Report stage-level Load failures.
    - Produce and lock the completed LoadSection.

Does NOT:
    - Retrieve source content.
    - Translate source metadata.
    - Determine synchronization state.
    - Load UNCHANGED records.
    - Perform AI interpretation or enrichment.
"""

from collections.abc import Mapping
from collections.abc import Sequence

from scripts.load.load_section import (
    LoadSection,
)

from scripts.sync.sync_state import (
    SyncState,
)


class LoadService:
    """
    Execute Load for orchestration-supplied synchronization associations.
    """

    def __init__(
        self,
        source_repository,
        load_repository,
    ):
        """
        Initialize Load dependencies.
        """

        if source_repository is None:
            raise ValueError(
                "SourceRepository is required."
            )

        if load_repository is None:
            raise ValueError(
                "LoadRepository is required."
            )

        self._source_repository = (
            source_repository
        )

        self._load_repository = (
            load_repository
        )

    def run(
        self,
        associations,
        processing_job_id,
    ):
        """
        Execute Load for an eligible synchronization batch.
        """

        if associations is None:
            raise ValueError(
                "Synchronization associations are required."
            )

        if (
            processing_job_id is None
            or not str(
                processing_job_id
            ).strip()
        ):
            raise ValueError(
                "processing_job_id is required."
            )

        load_section = (
            LoadSection()
        )

        #
        # Resolve each Source only once during this Load run.
        #
        source_ids = {}

        try:
            for association in associations:
                try:
                    self._load_association(
                        association=association,
                        processing_job_id=(
                            processing_job_id
                        ),
                        source_ids=source_ids,
                    )

                except Exception as error:
                    load_section.record_errors.append(
                        self._build_record_error(
                            association=association,
                            error=error,
                        )
                    )

        except Exception as error:
            raise RuntimeError(
                "Load stage failed."
            ) from error

        load_section.load_succeeded = True
        load_section.lock()

        return load_section

    def _load_association(
        self,
        association,
        processing_job_id,
        source_ids,
    ):
        """
        Persist one synchronization association.

        The association must already contain trusted stage-owned
        records belonging to the same orchestration correlation ID.
        """

        if association is None:
            raise ValueError(
                "SynchronizationAssociation is required."
            )

        translator_record = getattr(
            association,
            "translator_record",
            None,
        )

        discovery_record = getattr(
            association,
            "discovery_record",
            None,
        )

        extraction_record = getattr(
            association,
            "extraction_record",
            None,
        )

        if translator_record is None:
            raise ValueError(
                "Load association is missing TranslatorRecord."
            )

        if discovery_record is None:
            raise ValueError(
                "Load association is missing DiscoveryRecord."
            )

        #
        # Only NEW and MODIFIED records are eligible for Load.
        #
        if discovery_record.sync_state not in (
            SyncState.NEW,
            SyncState.MODIFIED,
        ):
            raise ValueError(
                "Load received an association that is not "
                "NEW or MODIFIED."
            )

        if extraction_record is None:
            raise ValueError(
                "Load association is missing ExtractionRecord."
            )

        self._validate_correlation(
            association=association,
            translator_record=translator_record,
            discovery_record=discovery_record,
            extraction_record=extraction_record,
        )

        source_id = (
            self._resolve_source_id(
                source_name=(
                    translator_record.source_name
                ),
                source_ids=source_ids,
            )
        )

        metadata = (
            self._build_metadata(
                translator_record=translator_record,
                extraction_record=extraction_record,
            )
        )

        persisted_knowledge_object_id = (
            self._load_repository.persist(
                sync_state=(
                    discovery_record.sync_state.value
                ),
                knowledge_object_id=(
                    discovery_record.knowledge_object_id
                ),
                source_id=source_id,
                source_object_id=(
                    translator_record.source_object_id
                ),
                source_parent_object_id=(
                    translator_record.source_parent_object_id
                ),
                source_path=(
                    translator_record.source_path
                ),
                source_url=(
                    translator_record.source_url
                ),
                title=(
                    translator_record.name
                ),
                object_type=(
                    translator_record.object_type
                ),
                canonical_content=(
                    extraction_record.canonical_content
                ),
                content_hash=(
                    extraction_record.content_hash
                ),
                source_created_at=(
                    translator_record.source_created_at
                ),
                source_modified_at=(
                    translator_record.source_modified_at
                ),
                metadata=metadata,
                processing_job_id=(
                    str(
                        processing_job_id
                    )
                ),
                comparison_reason=(
                    discovery_record.comparison_reason
                ),
            )
        )

        return persisted_knowledge_object_id

    @staticmethod
    def _validate_correlation(
        association,
        translator_record,
        discovery_record,
        extraction_record,
    ):
        """
        Verify all stage records belong to the supplied association.

        Load does not perform cross-stage matching. It only verifies
        that Synchronization Orchestration supplied a coherent
        association.
        """

        correlation_id = getattr(
            association,
            "correlation_id",
            None,
        )

        if (
            correlation_id is None
            or not str(
                correlation_id
            ).strip()
        ):
            raise ValueError(
                "SynchronizationAssociation is missing "
                "correlation_id."
            )

        stage_records = {
            "TranslatorRecord":
                translator_record,

            "DiscoveryRecord":
                discovery_record,

            "ExtractionRecord":
                extraction_record,
        }

        for record_name, record in (
            stage_records.items()
        ):
            record_correlation_id = getattr(
                record,
                "correlation_id",
                None,
            )

            if (
                record_correlation_id
                != correlation_id
            ):
                raise ValueError(
                    f"{record_name} correlation_id does not "
                    "match the SynchronizationAssociation."
                )

    def _resolve_source_id(
        self,
        source_name,
        source_ids,
    ):
        """
        Resolve and cache the AlphaOmega Source UUID.
        """

        if source_name in source_ids:
            return source_ids[
                source_name
            ]

        source_id = (
            self._source_repository
            .find_id_by_name(
                source_name
            )
        )

        if source_id is None:
            raise RuntimeError(
                f"Source '{source_name}' is not registered "
                "in AlphaOmega."
            )

        source_ids[
            source_name
        ] = source_id

        return source_id

    @staticmethod
    def _to_persistence_safe(
        value,
    ):
        """
        Recursively convert trusted immutable synchronization values
        into ordinary JSON-compatible Python structures.

        Synchronization sections intentionally expose immutable
        mappings and sequences after validation and locking.

        Persistence infrastructure must not weaken that immutability.
        Instead, Load creates a persistence-safe copy at the database
        boundary.

        Mappings become dict.
        Sequences become list.
        String and byte-like values remain scalar values rather than
        being treated as sequences.
        Primitive scalar values are returned unchanged.
        """

        if isinstance(
            value,
            Mapping,
        ):
            return {
                key:
                    LoadService._to_persistence_safe(
                        item
                    )
                for key, item
                in value.items()
            }

        if (
            isinstance(
                value,
                Sequence,
            )
            and not isinstance(
                value,
                (
                    str,
                    bytes,
                    bytearray,
                ),
            )
        ):
            return [
                LoadService._to_persistence_safe(
                    item
                )
                for item
                in value
            ]

        return value

    @staticmethod
    def _build_metadata(
        translator_record,
        extraction_record,
    ):
        """
        Assemble persisted metadata from trusted stage-owned metadata.

        Translator metadata remains source/canonical synchronization
        metadata.

        Extraction metadata remains factual metadata derived during
        extraction.

        Load combines them only for persistence and does not reinterpret
        their meaning.

        Immutable upstream collections are recursively converted into
        ordinary persistence-safe structures before crossing the
        repository/database boundary.
        """

        metadata = {}

        translator_metadata = getattr(
            translator_record,
            "metadata",
            {},
        )

        extraction_metadata = getattr(
            extraction_record,
            "canonical_metadata",
            {},
        )

        if translator_metadata:
            metadata.update(
                LoadService._to_persistence_safe(
                    translator_metadata
                )
            )

        if extraction_metadata:
            metadata[
                "extraction"
            ] = (
                LoadService._to_persistence_safe(
                    extraction_metadata
                )
            )

        extractor_name = getattr(
            extraction_record,
            "extractor_name",
            None,
        )

        extraction_timestamp = getattr(
            extraction_record,
            "extraction_timestamp",
            None,
        )

        if (
            extractor_name is not None
            or extraction_timestamp is not None
        ):
            metadata.setdefault(
                "extraction",
                {},
            )

            if extractor_name is not None:
                metadata[
                    "extraction"
                ][
                    "extractor_name"
                ] = extractor_name

            if extraction_timestamp is not None:
                metadata[
                    "extraction"
                ][
                    "extraction_timestamp"
                ] = extraction_timestamp

        return metadata

    @staticmethod
    def _get_root_cause(
        error,
    ):
        """
        Return the deepest available chained exception message.

        Repository boundaries may wrap lower-level database or
        transport exceptions while preserving them with exception
        chaining. Load diagnostics expose the deepest cause without
        changing the repository's public exception contract.
        """

        root_error = error
        visited = set()

        while root_error is not None:
            error_identity = id(
                root_error
            )

            if error_identity in visited:
                break

            visited.add(
                error_identity
            )

            next_error = getattr(
                root_error,
                "__cause__",
                None,
            )

            if next_error is None:
                next_error = getattr(
                    root_error,
                    "__context__",
                    None,
                )

            if next_error is None:
                break

            root_error = next_error

        return str(
            root_error
        )

    @staticmethod
    def _build_record_error(
        association,
        error,
    ):
        """
        Build diagnostic information for one Load record failure.

        Correlation identity is preserved so Synchronization
        Orchestration can associate the Load failure with the
        correct source object.

        Chained exceptions are inspected so the underlying repository
        or database failure remains available for diagnostics.
        """

        correlation_id = getattr(
            association,
            "correlation_id",
            None,
        )

        translator_record = getattr(
            association,
            "translator_record",
            None,
        )

        discovery_record = getattr(
            association,
            "discovery_record",
            None,
        )

        root_cause = (
            LoadService._get_root_cause(
                error
            )
        )

        return {
            "stage":
                "Load",

            "correlation_id":
                correlation_id,

            "source":
                getattr(
                    translator_record,
                    "source_name",
                    None,
                ),

            "object_id":
                getattr(
                    translator_record,
                    "source_object_id",
                    None,
                ),

            "object_name":
                getattr(
                    translator_record,
                    "name",
                    None,
                ),

            "sync_state":
                (
                    getattr(
                        discovery_record,
                        "sync_state",
                        None,
                    ).value
                    if getattr(
                        discovery_record,
                        "sync_state",
                        None,
                    )
                    is not None
                    else None
                ),

            "exception_type":
                error.__class__.__name__,

            "failure_reason":
                str(
                    error
                ),

            "root_cause":
                root_cause,

            "recommended_action":
                (
                    "Review the associated Translator, Discovery, "
                    "Extraction, Source registration, and atomic "
                    "Load persistence operation."
                ),
        }