"""
AlphaOmega Discovery Service

Purpose:
    Executes the Discovery stage by comparing translated source facts with
    persisted AlphaOmega Knowledge Object facts.

Responsibilities:
    - Resolve registered Source identity.
    - Reuse Source identity within a Discovery run.
    - Locate existing Knowledge Objects by source identity.
    - Classify records as NEW, MODIFIED, or UNCHANGED.
    - Record factual comparison reasons.
    - Determine whether Extraction is required.
    - Preserve orchestration correlation identity.
    - Isolate record-level Discovery failures.
    - Report stage-level Discovery failures.
    - Produce and lock the completed DiscoverySection.

Does NOT:
    - Retrieve source content.
    - Modify Translator-owned facts.
    - Perform Extraction or Load.
    - Persist Knowledge Object changes.
    - Perform semantic interpretation.
"""

from scripts.discovery.discovery_record import DiscoveryRecord
from scripts.discovery.discovery_section import DiscoverySection
from scripts.sync.sync_state import SyncState
from scripts.discovery.discovery_comparator import DiscoveryComparator
from scripts.sync.sync_exceptions import (
    DiscoveryError,
    DiscoveryRecordError,
)

class DiscoveryService:
    """
    Execute Discovery against validated Translator output.

    Discovery owns synchronization-state determination.

    Database-specific access is delegated to repository classes.
    """

    def __init__(
        self,
        source_repository,
        knowledge_object_repository,
    ):
        """
        Initialize Discovery.

        Args:
            source_repository:
                Repository used to resolve AlphaOmega source IDs.

            knowledge_object_repository:
                Repository used to locate existing Knowledge Objects.
        """

        if source_repository is None:
            raise ValueError(
                "SourceRepository is required."
            )

        if knowledge_object_repository is None:
            raise ValueError(
                "KnowledgeObjectRepository is required."
            )

        self._source_repository = source_repository
        self._knowledge_object_repository = (
            knowledge_object_repository
        )

    def run(self, translator_section):
        """
        Execute Discovery for all successfully translated records.

        Args:
            translator_section:
                Completed and locked TranslatorSection.

        Returns:
            DiscoverySection:
                Completed and locked Discovery output.

        Raises:
            RuntimeError:
                If Discovery cannot fulfill its stage contract.
        """

        if translator_section is None:
            raise ValueError(
                "TranslatorSection is required."
            )

        discovery_section = DiscoverySection()

        #
        # Source resolution is performed once per source name and cached
        # for the duration of this Discovery run.
        #
        source_ids = {}

        for translator_record in (
            translator_section.translated_records
        ):
            try:
                discovery_record = self._discover_record(
                    translator_record=translator_record,
                    source_ids=source_ids,
                )

                discovery_section.discovery_records.append(
                    discovery_record
                )

            except DiscoveryRecordError as error:
                discovery_section.record_errors.append(
                    self._build_record_error(
                        translator_record=translator_record,
                        error=error,
                    )
                )

            except DiscoveryError:
                raise

            except Exception as error:
                raise DiscoveryError(
                    "Discovery stage encountered an unexpected failure."
                ) from error

        discovery_section.discovery_succeeded = True

        discovery_section.lock()

        return discovery_section

    def _discover_record(
        self,
        translator_record,
        source_ids,
    ):
        """
        Determine synchronization state for one TranslatorRecord.
        """

        source_id = self._resolve_source_id(
            source_name=translator_record.source_name,
            source_ids=source_ids,
        )

        knowledge_object = (
            self._knowledge_object_repository
            .find_by_source_identity(
                source_id=source_id,
                source_object_id=(
                    translator_record.source_object_id
                ),
            )
        )

        discovery_record = DiscoveryRecord()

        #
        # Orchestration correlation identity
        #
        discovery_record.correlation_id = (
            translator_record.correlation_id
        )

        #
        # NEW
        #
        if knowledge_object is None:
            discovery_record.sync_state = SyncState.NEW
            discovery_record.comparison_reason = None
            discovery_record.previous_content_hash = None
            discovery_record.requires_extraction = True

            return discovery_record

        #
        # Existing Knowledge Object
        #
        discovery_record.knowledge_object_id = (
            knowledge_object["id"]
        )

        discovery_record.previous_content_hash = (
            knowledge_object["content_hash"]
        )

        comparison_reasons = DiscoveryComparator.compare(
            translator_record=translator_record,
            knowledge_object=knowledge_object,
        )

        #
        # UNCHANGED
        #
        if not comparison_reasons:
            discovery_record.sync_state = SyncState.UNCHANGED
            discovery_record.comparison_reason = None
            discovery_record.requires_extraction = False

            return discovery_record

        #
        # MODIFIED
        #
        discovery_record.sync_state = SyncState.MODIFIED
        discovery_record.comparison_reason = "; ".join(
            comparison_reasons
        )
        discovery_record.requires_extraction = True

        return discovery_record

    def _resolve_source_id(
        self,
        source_name,
        source_ids,
    ):
        """
        Resolve and cache the AlphaOmega ID for a Source of Truth.
        """

        if source_name in source_ids:
            return source_ids[source_name]

        source_id = self._source_repository.find_id_by_name(
            source_name
        )

        if source_id is None:
            raise DiscoveryError(
                f"Source '{source_name}' is not registered "
                f"in AlphaOmega."
            )

        source_ids[source_name] = source_id

        return source_id

    @staticmethod
    def _build_record_error(
        translator_record,
        error,
    ):
        """
        Build diagnostic information for a record-level Discovery error.

        Correlation identity is propagated from the TranslatorRecord
        so Synchronization Orchestration can associate the failure with
        the source object throughout the synchronization run.
        """

        return {
            "stage": "Discovery",

            "correlation_id": (
                translator_record.correlation_id
            ),

            "source": translator_record.source_name,

            "object_id": (
                translator_record.source_object_id
            ),

            "object_name": translator_record.name,

            "exception_type": (
                error.__class__.__name__
            ),

            "failure_reason": str(error),

            "recommended_action": (
                "Review Source registration, repository access, "
                "and the affected Knowledge Object."
            ),
        }