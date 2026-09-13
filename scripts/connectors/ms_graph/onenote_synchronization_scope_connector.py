"""
OneNote Synchronization Scope Connector

Purpose:
    Completely enumerates one selected OneNote Container synchronization
    scope.

Responsibilities:
    - Accept one selected OneNote Container source-native identity.
    - Resolve whether the selected Container is a notebook,
      section group, or section.
    - Enumerate only the selected Container and its descendants.
    - Reuse the existing Graph Connector's OneNote hierarchy behavior.
    - Preserve the containing Section modification timestamp with Pages.
    - Return Connector output only after complete scope enumeration.

Does NOT:
    - Perform whole-Source OneNote enumeration.
    - Refresh the Source Container Catalog.
    - Determine synchronization state.
    - Extract canonical content.
    - Create Processing Jobs or Synchronization Runs.
    - Execute Discovery, Extraction, or Load.

Whole-Source OneNote synchronization remains the responsibility of the
existing GraphConnector.run("onenote") path.
"""

import requests

from scripts.connectors.connector_section import (
    ConnectorSection,
)

from scripts.connectors.ms_graph.graph_connection import (
    graph_get,
)

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)


class OneNoteSynchronizationScopeConnector(
    GraphConnector
):
    """
    Enumerate one selected OneNote Container subtree.
    """

    source_name = "onenote"

    def run(
        self,
        *,
        source_object_id,
    ):
        """
        Completely enumerate one selected OneNote Container.
        """

        source_object_id = self._require_text(
            source_object_id,
            "source_object_id",
        )

        (
            selected_type,
            selected_object,
        ) = self._resolve_selected_container(
            source_object_id
        )

        raw_objects = []

        sections = []

        section_ids = set()

        section_group_ids = set()

        if selected_type == "notebook":

            self._enumerate_notebook_scope(
                notebook=selected_object,
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
                section_group_ids=(
                    section_group_ids
                ),
            )

        elif (
            selected_type
            == "sectionGroup"
        ):

            self._enumerate_section_group_scope(
                section_group=selected_object,
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
                section_group_ids=(
                    section_group_ids
                ),
            )

        elif selected_type == "section":

            self._enumerate_section_scope(
                section=selected_object,
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
            )

        else:

            raise RuntimeError(
                "Unsupported resolved OneNote "
                "Container type."
            )

        for section_context in sections:

            self._enumerate_onenote_section_pages(
                section_context=(
                    section_context
                ),
                raw_objects=raw_objects,
            )

        connector_section = (
            ConnectorSection(
                self.source_name
            )
        )

        connector_section.raw_objects = (
            raw_objects
        )

        connector_section.raw_metadata = {
            "enumeration_complete":
                True,

            "retrieval_strategy":
                "selected_onenote_container",

            "scope_source_object_id":
                source_object_id,

            "scope_object_type":
                selected_type,

            "objects_retrieved":
                len(raw_objects),

            "sections_retrieved":
                len(section_ids),

            "section_groups_retrieved":
                len(section_group_ids),

            "page_hierarchy_required":
                True,
        }

        connector_section.connection_succeeded = (
            True
        )

        self._validate_scope_section(
            connector_section
        )

        connector_section.lock()

        return connector_section

    # ========================================================================
    # Selected Container Resolution
    # ========================================================================

    def _resolve_selected_container(
        self,
        source_object_id,
    ):
        """
        Determine which supported OneNote Container owns the selected ID.

        The Source Container Catalog currently preserves stable source-native
        identity but not the OneNote Container type, so Graph is queried
        against the three supported Container endpoints.

        Only HTTP 404 means the identity is absent from an endpoint.
        """

        candidates = (
            (
                "notebook",
                "/me/onenote/notebooks/"
                f"{source_object_id}",
            ),
            (
                "sectionGroup",
                "/me/onenote/sectionGroups/"
                f"{source_object_id}",
            ),
            (
                "section",
                "/me/onenote/sections/"
                f"{source_object_id}",
            ),
        )

        for (
            source_object_type,
            endpoint,
        ) in candidates:

            raw_object = (
                self._get_object_if_found(
                    endpoint
                )
            )

            if raw_object is None:
                continue

            returned_id = (
                raw_object.get(
                    "id"
                )
            )

            if not returned_id:

                raise RuntimeError(
                    "Resolved OneNote Container is "
                    "missing its source object ID."
                )

            if (
                str(returned_id)
                != source_object_id
            ):
                raise RuntimeError(
                    "Microsoft Graph returned a different "
                    "OneNote Container than the requested "
                    "synchronization scope."
                )

            return (
                source_object_type,
                raw_object,
            )

        raise RuntimeError(
            "Selected OneNote Container does not "
            "exist in the Source of Truth."
        )

    @staticmethod
    def _get_object_if_found(
        endpoint,
    ):
        """
        Return one Graph object or None only for HTTP 404.

        Source-of-Truth validation already occurs before reservation and
        execution. This lookup exists only to determine the selected OneNote
        Container type.
        """

        try:

            response = graph_get(
                endpoint
            )

            return response.json()

        except requests.HTTPError as exception:

            response = (
                exception.response
            )

            if (
                response is not None
                and response.status_code == 404
            ):
                return None

            raise

    # ========================================================================
    # Notebook Scope
    # ========================================================================

    def _enumerate_notebook_scope(
        self,
        *,
        notebook,
        raw_objects,
        sections,
        section_ids,
        section_group_ids,
    ):
        """
        Enumerate one selected notebook and everything beneath it.
        """

        notebook_id = (
            notebook.get(
                "id"
            )
        )

        notebook_name = (
            self._get_onenote_name(
                notebook,
                "notebook",
            )
        )

        if not notebook_id:

            raise RuntimeError(
                "OneNote notebook is missing "
                "its source object ID."
            )

        if not notebook_name:

            raise RuntimeError(
                "OneNote notebook is missing "
                "its display name."
            )

        raw_objects.append(
            self._wrap_object(
                "notebook",
                notebook,
                connector_metadata={
                    "source_parent_object_id":
                        None,

                    "source_path":
                        None,

                    "object_path":
                        notebook_name,

                    "hierarchy_verified":
                        True,
                },
            )
        )

        notebook_sections = (
            self._get_collection(
                "/me/onenote/notebooks/"
                f"{notebook_id}/sections"
            )
        )

        for section in notebook_sections:

            self._add_onenote_section(
                section=section,
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
                parent_object_id=(
                    notebook_id
                ),
                parent_path=(
                    notebook_name
                ),
            )

        section_groups = (
            self._get_collection(
                "/me/onenote/notebooks/"
                f"{notebook_id}/sectionGroups"
                "?$expand=sections"
            )
        )

        for section_group in section_groups:

            self._add_onenote_section_group(
                section_group=(
                    section_group
                ),
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
                section_group_ids=(
                    section_group_ids
                ),
                parent_object_id=(
                    notebook_id
                ),
                parent_path=(
                    notebook_name
                ),
            )

    # ========================================================================
    # Section Group Scope
    # ========================================================================

    def _enumerate_section_group_scope(
        self,
        *,
        section_group,
        raw_objects,
        sections,
        section_ids,
        section_group_ids,
    ):
        """
        Enumerate one selected section group and everything beneath it.
        """

        section_group_id = (
            section_group.get(
                "id"
            )
        )

        section_group_name = (
            self._get_onenote_name(
                section_group,
                "sectionGroup",
            )
        )

        if not section_group_id:

            raise RuntimeError(
                "OneNote section group is missing "
                "its source object ID."
            )

        if not section_group_name:

            raise RuntimeError(
                "OneNote section group is missing "
                "its display name."
            )

        section_group_ids.add(
            section_group_id
        )

        raw_objects.append(
            self._wrap_object(
                "sectionGroup",
                section_group,
                connector_metadata={
                    "source_parent_object_id":
                        None,

                    "source_path":
                        None,

                    "object_path":
                        section_group_name,

                    "hierarchy_verified":
                        True,
                },
            )
        )

        direct_sections = (
            self._get_collection(
                "/me/onenote/sectionGroups/"
                f"{section_group_id}/sections"
            )
        )

        for section in direct_sections:

            self._add_onenote_section(
                section=section,
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
                parent_object_id=(
                    section_group_id
                ),
                parent_path=(
                    section_group_name
                ),
            )

        child_groups = (
            self._get_collection(
                "/me/onenote/sectionGroups/"
                f"{section_group_id}/sectionGroups"
                "?$expand=sections"
            )
        )

        for child_group in child_groups:

            self._add_onenote_section_group(
                section_group=child_group,
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
                section_group_ids=(
                    section_group_ids
                ),
                parent_object_id=(
                    section_group_id
                ),
                parent_path=(
                    section_group_name
                ),
            )

    # ========================================================================
    # Section Scope
    # ========================================================================

    def _enumerate_section_scope(
        self,
        *,
        section,
        raw_objects,
        sections,
        section_ids,
    ):
        """
        Enumerate one selected Section and all Pages beneath it.
        """

        section_id = (
            section.get(
                "id"
            )
        )

        if not section_id:

            raise RuntimeError(
                "OneNote section is missing "
                "its source object ID."
            )

        section_name = (
            self._get_onenote_name(
                section,
                "section",
            )
        )

        if not section_name:

            raise RuntimeError(
                "OneNote section is missing "
                "its display name."
            )

        self._add_onenote_section(
            section=section,
            raw_objects=raw_objects,
            sections=sections,
            section_ids=section_ids,
            parent_object_id=None,
            parent_path=None,
        )

    # ========================================================================
    # Completed Scope Validation
    # ========================================================================

    @staticmethod
    def _validate_scope_section(
        connector_section,
    ):
        """
        Validate completed bounded OneNote Connector output.
        """

        if (
            connector_section
            .connection_succeeded
            is not True
        ):
            raise RuntimeError(
                "OneNote synchronization scope Connector "
                "did not complete successfully."
            )

        if not isinstance(
            connector_section.raw_objects,
            list,
        ):
            raise TypeError(
                "Connector raw_objects must be a list."
            )

        if not isinstance(
            connector_section.raw_metadata,
            dict,
        ):
            raise TypeError(
                "Connector raw_metadata must be a dictionary."
            )

        if (
            connector_section
            .raw_metadata
            .get(
                "enumeration_complete"
            )
            is not True
        ):
            raise RuntimeError(
                "Selected OneNote synchronization scope "
                "was not completely enumerated."
            )

        if not (
            connector_section
            .raw_metadata
            .get(
                "scope_source_object_id"
            )
        ):
            raise RuntimeError(
                "Completed selected OneNote scope "
                "is missing its scope identity."
            )

        if (
            connector_section
            .raw_metadata
            .get(
                "scope_object_type"
            )
            not in {
                "notebook",
                "sectionGroup",
                "section",
            }
        ):
            raise RuntimeError(
                "Completed selected OneNote scope "
                "is missing a valid Container type."
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