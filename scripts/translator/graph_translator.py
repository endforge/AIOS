"""
AlphaOmega Microsoft Graph Translator

Purpose:
    Translates raw Microsoft Graph source objects into canonical AlphaOmega
    TranslatorRecords.

Responsibilities:
    - Translate supported OneDrive and OneNote source objects.
    - Assign canonical CONTENT or CONTAINER object types.
    - Preserve orchestration correlation identity.
    - Preserve source-native object identity.
    - Preserve connector-proven parent identity and hierarchy paths.
    - Normalize source names and timestamps.
    - Use the OneNote parent Section modification timestamp for page
      source_modified_at.
    - Isolate record-level translation failures.
    - Produce and lock the completed TranslatorSection.

Does NOT:
    - Retrieve source objects.
    - Generate orchestration correlation identity.
    - Determine synchronization state.
    - Extract source content.
    - Persist Knowledge Objects.
"""

from collections.abc import Mapping
from collections.abc import Sequence

from common.object_types import CONTAINER
from scripts.translator.base_translator import BaseTranslator
from scripts.translator.graph_translator_mappings import (
    GRAPH_FIELD_MAPPING,
    RESERVED_GRAPH_FIELDS,
    get_canonical_object_type,
    get_nested_value,
)
from scripts.translator.translator_record import TranslatorRecord
from scripts.translator.translator_section import TranslatorSection
from scripts.sync.sync_exceptions import UnsupportedObjectTypeError


class GraphTranslator(BaseTranslator):
    """
    Translator for Microsoft Graph sources.
    """

    # ========================================================================
    # Canonical Source Names
    # ========================================================================

    CANONICAL_SOURCE_NAMES = {
        "onedrive": "OneDrive",
        "onenote": "OneNote",
    }

    # ========================================================================
    # Public Interface
    # ========================================================================

    def run(
        self,
        translation_input,
    ):
        """
        Execute the Translator stage.

        Translation input is supplied by Synchronization Orchestration
        after Connector completes.

        Each source object contains an orchestration-owned correlation
        UUID plus the Connector-owned source information.

        Record-level errors affect only the individual source object.
        Remaining objects continue processing.

        Stage-level errors propagate to Synchronization Orchestration.
        """

        if translation_input is None:
            raise ValueError(
                "TranslationInput is required."
            )

        translator_section = (
            TranslatorSection()
        )

        connector_objects = (
            self._get_source_objects(
                translation_input.raw_objects
            )
        )

        for connector_object in (
            connector_objects
        ):

            correlation_id = (
                connector_object[
                    "correlation_id"
                ]
            )

            source_object_type = (
                connector_object[
                    "source_object_type"
                ]
            )

            raw_object = (
                connector_object[
                    "raw_object"
                ]
            )

            connector_metadata = (
                connector_object.get(
                    "connector_metadata",
                    {},
                )
            )

            try:

                translator_record = (
                    self._translate_record(
                        correlation_id=(
                            correlation_id
                        ),
                        source_name=(
                            translation_input.source_name
                        ),
                        source_object_type=(
                            source_object_type
                        ),
                        raw_object=(
                            raw_object
                        ),
                        connector_metadata=(
                            connector_metadata
                        ),
                    )
                )

                translator_section.translated_records.append(
                    translator_record
                )

            except UnsupportedObjectTypeError as error:

                translator_section.record_errors.append(
                    self._build_record_error(
                        correlation_id=(
                            correlation_id
                        ),
                        source_name=(
                            translation_input.source_name
                        ),
                        source_object_type=(
                            source_object_type
                        ),
                        raw_object=(
                            raw_object
                        ),
                        error=(
                            error
                        ),
                    )
                )

        translator_section.translation_succeeded = (
            True
        )

        translator_section.lock()

        return translator_section

    # ========================================================================
    # Translator Input Validation
    # ========================================================================

    def _get_source_objects(
        self,
        raw_data,
    ):
        """
        Validate and return orchestration-supplied source objects.
        """

        if (
            not isinstance(
                raw_data,
                Sequence,
            )
            or isinstance(
                raw_data,
                (str, bytes),
            )
        ):

            raise TypeError(
                "Translator stage received invalid Translator input. "
                "Expected a sequence of source objects."
            )

        for connector_object in (
            raw_data
        ):

            if not isinstance(
                connector_object,
                Mapping,
            ):

                raise TypeError(
                    "Translator stage received invalid source object. "
                    "Expected a mapping."
                )

            if (
                "correlation_id"
                not in connector_object
            ):

                raise TypeError(
                    "Translator stage received a source object "
                    "without correlation_id."
                )

            if (
                "source_object_type"
                not in connector_object
            ):

                raise TypeError(
                    "Translator stage received a source object "
                    "without source_object_type."
                )

            if (
                "raw_object"
                not in connector_object
            ):

                raise TypeError(
                    "Translator stage received a source object "
                    "without raw_object."
                )

            correlation_id = (
                connector_object[
                    "correlation_id"
                ]
            )

            source_object_type = (
                connector_object[
                    "source_object_type"
                ]
            )

            raw_object = (
                connector_object[
                    "raw_object"
                ]
            )

            connector_metadata = (
                connector_object.get(
                    "connector_metadata",
                    {},
                )
            )

            if (
                correlation_id is None
                or not str(
                    correlation_id
                ).strip()
            ):

                raise TypeError(
                    "Translator stage received an invalid "
                    "correlation_id."
                )

            if not isinstance(
                source_object_type,
                str,
            ):

                raise TypeError(
                    "Translator stage received invalid Microsoft "
                    "Graph source_object_type. Expected a string."
                )

            if not isinstance(
                raw_object,
                Mapping,
            ):

                raise TypeError(
                    "Translator stage received invalid Microsoft "
                    "Graph raw_object. Expected a mapping."
                )

            if not isinstance(
                connector_metadata,
                Mapping,
            ):

                raise TypeError(
                    "Translator stage received invalid Microsoft "
                    "Graph connector_metadata. Expected a mapping."
                )

        return raw_data

    # ========================================================================
    # Record Translation
    # ========================================================================

    def _translate_record(
        self,
        correlation_id,
        source_name,
        source_object_type,
        raw_object,
        connector_metadata,
    ):
        """
        Translate one Microsoft Graph object into a TranslatorRecord.
        """

        canonical_object_type = (
            self._get_object_type(
                source_object_type=(
                    source_object_type
                ),
                raw_object=(
                    raw_object
                ),
            )
        )

        if canonical_object_type is None:

            raise UnsupportedObjectTypeError(
                stage="Translator",
                source_name=source_name,
                object_type=source_object_type,
                object_id=raw_object.get(
                    "id"
                ),
                object_name=(
                    raw_object.get(
                        "displayName"
                    )
                    or raw_object.get(
                        "name"
                    )
                    or raw_object.get(
                        "title"
                    )
                ),
            )

        record = TranslatorRecord()

        #
        # Orchestration correlation identity
        #
        record.correlation_id = str(
            correlation_id
        )

        # --------------------------------------------------------------------
        # Canonical Source Name
        # --------------------------------------------------------------------

        record.source_name = (
            self.CANONICAL_SOURCE_NAMES.get(
                source_name,
                source_name,
            )
        )

        record.object_type = (
            canonical_object_type
        )

        # --------------------------------------------------------------------
        # Canonical Graph field mapping
        # --------------------------------------------------------------------

        for (
            source_field,
            canonical_field,
        ) in GRAPH_FIELD_MAPPING.items():

            value = get_nested_value(
                raw_object,
                source_field,
            )

            if value is None:
                continue

            if (
                canonical_field == "name"
                and record.name is not None
            ):
                continue

            if canonical_field == "name":
                value = str(
                    value
                ).strip()

            setattr(
                record,
                canonical_field,
                value,
            )

        # --------------------------------------------------------------------
        # OneNote Page modification signal
        # --------------------------------------------------------------------
        #
        # Microsoft Graph Page.lastModifiedDateTime is not reliable for
        # detecting OneNote page body changes.
        #
        # Connector preserves the containing Section's
        # lastModifiedDateTime as source_section_modified_at.
        #
        # For OneNote Pages only, use that value as the canonical
        # source_modified_at synchronization signal.
        #
        # The raw Microsoft Graph Page metadata remains unchanged and is
        # preserved below in record.metadata.
        # --------------------------------------------------------------------

        if (
            record.source_name == "OneNote"
            and source_object_type == "page"
        ):

            section_modified_at = (
                connector_metadata.get(
                    "source_section_modified_at"
                )
            )

            if section_modified_at is not None:

                record.source_modified_at = (
                    section_modified_at
                )

        # --------------------------------------------------------------------
        # OneNote blank-page normalization
        # --------------------------------------------------------------------

        if (
            source_object_type == "page"
            and (
                record.name is None
                or not str(
                    record.name
                ).strip()
            )
        ):
            record.name = "Untitled"

        # --------------------------------------------------------------------
        # Connector-proven hierarchy
        # --------------------------------------------------------------------

        if (
            "source_parent_object_id"
            in connector_metadata
        ):
            record.source_parent_object_id = (
                connector_metadata.get(
                    "source_parent_object_id"
                )
            )

        if (
            "source_path"
            in connector_metadata
        ):
            record.source_path = (
                connector_metadata.get(
                    "source_path"
                )
            )

        # --------------------------------------------------------------------
        # Source metadata preservation
        # --------------------------------------------------------------------

        record.metadata = {
            key: value
            for key, value
            in raw_object.items()
            if key
            not in RESERVED_GRAPH_FIELDS
        }

        if connector_metadata:
            record.metadata[
                "connector_hierarchy"
            ] = dict(
                connector_metadata
            )

        return record

    # ========================================================================
    # Object Type Translation
    # ========================================================================

    def _get_object_type(
        self,
        source_object_type,
        raw_object,
    ):
        """
        Determine the AlphaOmega canonical object type.

        Microsoft Graph uses driveItem for both files and folders.
        Folder-faceted driveItems therefore become CONTAINER.
        """

        if (
            source_object_type
            == "driveItem"
            and "folder"
            in raw_object
        ):
            return CONTAINER

        return get_canonical_object_type(
            source_object_type
        )

    # ========================================================================
    # Record-Level Error Handling
    # ========================================================================

    def _build_record_error(
        self,
        correlation_id,
        source_name,
        source_object_type,
        raw_object,
        error,
    ):
        """
        Build diagnostic information for a record-level Translator error.
        """

        return {
            "stage":
                "Translator",

            "correlation_id":
                str(
                    correlation_id
                ),

            "source":
                source_name,

            "object_id":
                raw_object.get(
                    "id"
                ),

            "object_name":
                (
                    raw_object.get(
                        "displayName"
                    )
                    or raw_object.get(
                        "name"
                    )
                    or raw_object.get(
                        "title"
                    )
                    or "Untitled"
                ),

            "object_type":
                source_object_type,

            "exception_type":
                error.__class__.__name__,

            "failure_reason":
                str(error),

            "recommended_action":
                (
                    "Review the Microsoft Graph object type and "
                    "add or correct the required Graph translation "
                    "mapping."
                ),
        }