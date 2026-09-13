"""
OneNote Timestamp Diagnostic

Purpose:
    Provides a read-only diagnostic of OneNote timestamp behavior for the
    controlled House Rules Section.

Verifies:
    - Graph page lastModifiedDateTime can be inspected.
    - Graph Section lastModifiedDateTime can be inspected.
    - TranslatorRecord.source_modified_at can be inspected.
    - Stored Knowledge Object source_modified_at can be inspected.
    - Source, translated, and persisted timestamps can be compared.

Does NOT:
    - Modify OneNote.
    - Modify Knowledge Objects.
    - Execute Load.
    - Perform AlphaOmega database writes.
"""

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)

from scripts.database.source_repository import (
    SourceRepository,
)

from scripts.database.knowledge_object_repository import (
    KnowledgeObjectRepository,
)

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)

from scripts.connectors.connector_section import (
    ConnectorSection,
)

from scripts.translator.graph_translator import (
    GraphTranslator,
)

from scripts.sync.sync_translation_input import (
    TranslationInput,
)


NOTEBOOK_NAME = "Mimic's Tavern"
SECTION_NAME = "House Rules"
EXPECTED_PAGE_COUNT = 16


# ============================================================================
# Controlled Connector
# ============================================================================

class HouseRulesDiagnosticConnector(
    GraphConnector
):

    @staticmethod
    def _find_named_object(
        objects,
        expected_name,
        name_field,
        object_type,
    ):

        matches = []

        for item in objects:

            actual_name = item.get(
                name_field
            )

            if (
                actual_name
                and actual_name.strip().casefold()
                == expected_name.casefold()
            ):
                matches.append(item)

        if not matches:
            raise RuntimeError(
                f"{object_type} not found: "
                f"'{expected_name}'."
            )

        if len(matches) > 1:
            raise RuntimeError(
                f"Multiple {object_type} objects found "
                f"with name '{expected_name}'."
            )

        return matches[0]

    def run(
        self,
        source_name,
    ):

        if (
            source_name is None
            or str(source_name).lower()
            != "onenote"
        ):
            raise ValueError(
                "Diagnostic Connector supports "
                "OneNote only."
            )

        notebooks = self._get_collection(
            "/me/onenote/notebooks"
        )

        notebook = self._find_named_object(
            notebooks,
            NOTEBOOK_NAME,
            "displayName",
            "notebook",
        )

        notebook_id = notebook.get("id")

        if not notebook_id:
            raise RuntimeError(
                "Notebook is missing Graph ID."
            )

        sections = self._get_collection(
            "/me/onenote/notebooks/"
            f"{notebook_id}/sections"
        )

        section = self._find_named_object(
            sections,
            SECTION_NAME,
            "displayName",
            "section",
        )

        section_id = section.get("id")

        if not section_id:
            raise RuntimeError(
                "Section is missing Graph ID."
            )

        live_section = self._get_json(
            "/me/onenote/sections/"
            f"{section_id}"
        )

        section_modified_at = (
            live_section.get(
                "lastModifiedDateTime"
            )
        )

        if not section_modified_at:
            raise RuntimeError(
                "Section is missing "
                "lastModifiedDateTime."
            )

        raw_objects = []

        section_path = self._join_source_path(
            NOTEBOOK_NAME,
            SECTION_NAME,
        )

        raw_objects.append(
            self._wrap_object(
                "section",
                live_section,
                connector_metadata={
                    "source_parent_object_id":
                        notebook_id,

                    "source_path":
                        NOTEBOOK_NAME,

                    "object_path":
                        section_path,

                    "hierarchy_verified":
                        True,
                },
            )
        )

        section_context = {
            "raw_object":
                live_section,

            "object_path":
                section_path,
        }

        self._enumerate_onenote_section_pages(
            section_context=section_context,
            raw_objects=raw_objects,
        )

        pages = [
            item
            for item in raw_objects
            if (
                item.get(
                    "source_object_type"
                )
                == "page"
            )
        ]

        if len(pages) != EXPECTED_PAGE_COUNT:
            raise RuntimeError(
                "Unexpected page count.\n"
                f"Expected: {EXPECTED_PAGE_COUNT}\n"
                f"Actual:   {len(pages)}"
            )

        connector_section = ConnectorSection(
            "onenote"
        )

        connector_section.raw_objects = (
            raw_objects
        )

        connector_section.raw_metadata = {
            "enumeration_complete":
                True,

            "diagnostic_mode":
                True,

            "target_notebook":
                NOTEBOOK_NAME,

            "target_section":
                SECTION_NAME,

            "target_section_id":
                section_id,

            "source_section_modified_at":
                section_modified_at,

            "pages_retrieved":
                len(pages),
        }

        connector_section.connection_succeeded = (
            True
        )

        self._validate_completed_section(
            connector_section
        )

        connector_section.lock()

        return connector_section


# ============================================================================
# Helpers
# ============================================================================

def normalize_timestamp(
    value,
):
    """
    Normalize timestamps for display comparison only.

    This does not change any source or database data.
    """

    if value is None:
        return None

    return str(value).strip()


def main():

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega OneNote Timestamp Diagnostic"
    )
    print(
        "============================================================"
    )
    print()
    print(
        f"Notebook : {NOTEBOOK_NAME}"
    )
    print(
        f"Section  : {SECTION_NAME}"
    )
    print()
    print(
        "READ ONLY: No AlphaOmega or OneNote "
        "writes will occur."
    )
    print()

    # ========================================================================
    # Database
    # ========================================================================

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

    source_id = (
        source_repository.find_id_by_name(
            "OneNote"
        )
    )

    if source_id is None:
        raise RuntimeError(
            "OneNote Source is not registered."
        )

    # ========================================================================
    # Connector
    # ========================================================================

    connector = (
        HouseRulesDiagnosticConnector()
    )

    connector_section = (
        connector.run(
            "OneNote"
        )
    )

    section_modified_at = (
        connector_section
        .raw_metadata[
            "source_section_modified_at"
        ]
    )

    print(
        "PASS: Live House Rules scope enumerated."
    )
    print(
        f"  Section modified : "
        f"{section_modified_at}"
    )
    print(
        f"  Connector objects: "
        f"{len(connector_section.raw_objects)}"
    )
    print()

    # ========================================================================
    # Capture raw Graph page timestamps
    # ========================================================================

    raw_pages = {}

    for wrapped_object in (
        connector_section.raw_objects
    ):

        if (
            wrapped_object.get(
                "source_object_type"
            )
            != "page"
        ):
            continue

        raw_object = (
            wrapped_object[
                "raw_object"
            ]
        )

        page_id = (
            raw_object.get("id")
        )

        raw_pages[page_id] = {
            "title":
                raw_object.get(
                    "title"
                ),

            "page_modified_at":
                raw_object.get(
                    "lastModifiedDateTime"
                ),
        }

    # ========================================================================
    # Translation
    # ========================================================================

    translation_input = (
        TranslationInput(
            connector_section
        )
    )

    translator = (
        GraphTranslator()
    )

    translator_section = (
        translator.run(
            translation_input
        )
    )

    if not translator_section.is_locked:
        raise RuntimeError(
            "TranslatorSection is not locked."
        )

    print(
        "PASS: Translator completed."
    )
    print()

    # ========================================================================
    # Report
    # ========================================================================

    content_count = 0
    timestamp_match_count = 0
    timestamp_difference_count = 0

    print(
        "------------------------------------------------------------"
    )
    print(
        "PAGE TIMESTAMP COMPARISON"
    )
    print(
        "------------------------------------------------------------"
    )
    print()

    for translator_record in (
        translator_section.translated_records
    ):

        if (
            translator_record.object_type
            != "CONTENT"
        ):
            continue

        content_count += 1

        page_id = (
            translator_record.source_object_id
        )

        raw_page = (
            raw_pages.get(
                page_id
            )
        )

        if raw_page is None:
            raise RuntimeError(
                "Translator CONTENT record could "
                "not be matched to raw Graph page.\n"
                f"Source Object ID: {page_id}"
            )

        knowledge_object = (
            knowledge_object_repository
            .find_by_source_identity(
                source_id=source_id,
                source_object_id=page_id,
            )
        )

        if knowledge_object is None:
            raise RuntimeError(
                "Stored Knowledge Object not found.\n"
                f"Page: {raw_page['title']}"
            )

        page_modified_at = (
            raw_page[
                "page_modified_at"
            ]
        )

        translator_modified_at = (
            translator_record
            .source_modified_at
        )

        stored_modified_at = (
            knowledge_object.get(
                "source_modified_at"
            )
        )

        translator_normalized = (
            normalize_timestamp(
                translator_modified_at
            )
        )

        stored_normalized = (
            normalize_timestamp(
                stored_modified_at
            )
        )

        if (
            translator_normalized
            == stored_normalized
        ):
            comparison = "MATCH"
            timestamp_match_count += 1

        else:
            comparison = "DIFFERENT"
            timestamp_difference_count += 1

        print(
            raw_page["title"]
        )

        print(
            f"  Source Object ID    : "
            f"{page_id}"
        )

        print(
            f"  Graph page modified : "
            f"{page_modified_at}"
        )

        print(
            f"  Graph section mod.  : "
            f"{section_modified_at}"
        )

        print(
            f"  Translator modified : "
            f"{translator_modified_at}"
        )

        print(
            f"  Stored KO modified  : "
            f"{stored_modified_at}"
        )

        print(
            f"  Comparison          : "
            f"{comparison}"
        )

        print()

    # ========================================================================
    # Reconciliation
    # ========================================================================

    if (
        content_count
        != EXPECTED_PAGE_COUNT
    ):
        raise RuntimeError(
            "Translator CONTENT count did not "
            "reconcile.\n"
            f"Expected: {EXPECTED_PAGE_COUNT}\n"
            f"Actual:   {content_count}"
        )

    print(
        "============================================================"
    )
    print(
        "SUMMARY"
    )
    print(
        "============================================================"
    )
    print()

    print(
        f"CONTENT records              : "
        f"{content_count}"
    )

    print(
        f"Translator/stored timestamp "
        f"MATCH     : "
        f"{timestamp_match_count}"
    )

    print(
        f"Translator/stored timestamp "
        f"DIFFERENT : "
        f"{timestamp_difference_count}"
    )

    print()
    print(
        "TIMESTAMP DIAGNOSTIC COMPLETED."
    )
    print()


if __name__ == "__main__":
    main()