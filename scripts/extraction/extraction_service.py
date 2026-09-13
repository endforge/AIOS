"""
AlphaOmega Extraction Service

Purpose:
    Coordinates Extraction for source objects already determined by
    synchronization orchestration to require extraction.

Responsibilities:
    - Retrieve source content through registered content retrievers.
    - Perform format-specific canonical content extraction.
    - Generate canonical content hashes.
    - Produce Extraction-owned factual metadata.
    - Produce ExtractionRecords.
    - Preserve orchestration correlation identity.
    - Isolate record-level Extraction failures.
    - Report stage-level Extraction failures.
    - Produce and lock the completed ExtractionSection.

Does NOT:
    - Enumerate Sources of Truth.
    - Translate source metadata.
    - Determine synchronization state.
    - Generate or interpret orchestration correlation identity.
    - Persist Knowledge Objects.
    - Perform AI interpretation or enrichment.
"""

from datetime import datetime, timezone

from scripts.extraction.content_retriever_router import (
    ContentRetrieverRouter,
)
from scripts.extraction.text_extractor import (
    TextExtractor,
)
from scripts.extraction.content_hasher import (
    ContentHasher,
)
from scripts.extraction.extraction_record import (
    ExtractionRecord,
)
from scripts.extraction.extraction_section import (
    ExtractionSection,
)
from scripts.sync.sync_exceptions import (
    ExtractionError,
    ExtractionRecordError,
)


class ExtractionService:
    """
    Execute Extraction for an orchestration-supplied batch.
    """

    def __init__(
        self,
        retriever_router=None,
        text_extractor=None,
        content_hasher=None,
    ):
        """
        Initialize Extraction dependencies.

        Dependency injection supports isolated testing without
        live source-system access.
        """

        self.retriever_router = (
            retriever_router
            or ContentRetrieverRouter()
        )

        self.text_extractor = (
            text_extractor
            or TextExtractor
        )

        self.content_hasher = (
            content_hasher
            or ContentHasher
        )

    def run(
        self,
        extraction_inputs,
    ):
        """
        Execute Extraction for an eligible batch.

        Record-level failures are captured and processing continues.

        Stage-level failures terminate Extraction and return control
        to the Synchronization Orchestrator.

        Args:
            extraction_inputs:
                Iterable of orchestration-supplied records containing
                the upstream information required for Extraction.

        Returns:
            ExtractionSection:
                Locked Extraction output containing successful
                ExtractionRecords and record-level errors.

        Raises:
            ExtractionError:
                If Extraction cannot fulfill its stage contract.
        """

        if extraction_inputs is None:
            raise ExtractionError(
                "Extraction input batch is required."
            )

        extraction_section = ExtractionSection()

        try:
            for extraction_input in extraction_inputs:
                try:
                    extraction_record = (
                        self._extract_record(
                            extraction_input
                        )
                    )

                    extraction_section.extraction_records.append(
                        extraction_record
                    )

                except ExtractionRecordError as error:
                    extraction_section.record_errors.append(
                        {
                            "correlation_id": getattr(
                                extraction_input,
                                "correlation_id",
                                None,
                            ),
                            "source_object_id": getattr(
                                extraction_input,
                                "source_object_id",
                                None,
                            ),
                            "error_type": type(error).__name__,
                            "message": str(error),
                        }
                    )

        except ExtractionError:
            raise

        except Exception as error:
            raise ExtractionError(
                "Extraction stage failed."
            ) from error

        extraction_section.extraction_succeeded = True
        extraction_section.lock()

        return extraction_section

    def _extract_record(
        self,
        extraction_input,
    ):
        """
        Extract canonical knowledge for one eligible source object.

        Correlation identity is propagated from the
        orchestration-supplied input. Extraction does not generate,
        modify, or interpret the identifier.

        Raises:
            ExtractionRecordError:
                If this individual source object cannot be extracted
                while the Extraction stage can safely continue.
        """

        source_object_id = getattr(
            extraction_input,
            "source_object_id",
            None,
        )

        try:
            source_name = getattr(
                extraction_input,
                "source_name",
                None,
            )

            object_type = getattr(
                extraction_input,
                "object_type",
                None,
            )

            file_name = getattr(
                extraction_input,
                "name",
                None,
            )

            if not source_name:
                raise ValueError(
                    "Extraction input is missing source_name."
                )

            if not source_object_id:
                raise ValueError(
                    "Extraction input is missing source_object_id."
                )

            if not file_name:
                raise ValueError(
                    "Extraction input is missing name."
                )

            retriever = (
                self.retriever_router.get_retriever(
                    source_name
                )
            )

            raw_content = self._retrieve_content(
                retriever=retriever,
                source_name=source_name,
                source_object_id=source_object_id,
                object_type=object_type,
            )

            extraction_file_name = (
                self._resolve_extraction_file_name(
                    source_name=source_name,
                    file_name=file_name,
                )
            )

            canonical_content = (
                self.text_extractor.extract(
                    extraction_file_name,
                    raw_content,
                )
            )

            content_hash = (
                self.content_hasher.generate(
                    canonical_content
                )
            )

            extraction_record = ExtractionRecord()

            #
            # Orchestration correlation identity
            #
            extraction_record.correlation_id = getattr(
                extraction_input,
                "correlation_id",
                None,
            )

            #
            # Extraction-owned canonical knowledge
            #
            extraction_record.canonical_content = (
                canonical_content
            )

            extraction_record.content_hash = (
                content_hash
            )

            extraction_record.canonical_metadata = {
                "content_length": len(
                    canonical_content
                ),
            }

            extraction_record.extractor_name = (
                self.text_extractor.extractor_name
            )

            extraction_record.extraction_timestamp = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            extraction_record.validate()

            return extraction_record

        except ExtractionError:
            raise

        except Exception as error:
            raise ExtractionRecordError(
                "Extraction failed for source object "
                f"'{source_object_id}': {error}"
            ) from error

    @staticmethod
    def _retrieve_content(
        retriever,
        source_name,
        source_object_id,
        object_type,
    ):
        """
        Call the appropriate source-specific retriever.
        """

        if source_name == "OneDrive":
            return retriever.retrieve(
                source_object_id
            )

        if source_name == "OneNote":
            return retriever.retrieve(
                source_object_id=source_object_id,
                object_type=object_type,
            )

        raise ValueError(
            "Unsupported Source for Extraction: "
            f"'{source_name}'."
        )

    @staticmethod
    def _resolve_extraction_file_name(
        source_name,
        file_name,
    ):
        """
        Resolve the filename used for format-specific extraction.

        OneNote page content is retrieved from Microsoft Graph
        as HTML regardless of the page's display name.
        """

        if source_name == "OneNote":
            return f"{file_name}.html"

        return file_name