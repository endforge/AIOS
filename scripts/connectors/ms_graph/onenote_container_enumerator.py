"""
File:
    onenote_container_enumerator.py

Purpose:
    Completely enumerates the current OneNote container structure.

Responsibilities:
    - Enumerate OneNote notebooks.
    - Enumerate section groups, including nested section groups.
    - Enumerate sections.
    - Preserve each container's Microsoft Graph source object ID.
    - Preserve its immediate parent source object ID.
    - Preserve its human-readable name.
    - Return containers only after enumeration completes successfully.

This module does NOT:
    - Enumerate OneNote pages.
    - Retrieve OneNote page content.
    - Synchronize content.
    - Translate AlphaOmega Knowledge Objects.
    - Determine synchronization state.
    - Create Processing Jobs.
    - Persist Source Containers.
    - Reconcile the Source Container Catalog.
"""

from scripts.connectors.ms_graph.graph_connection import graph_get


ONENOTE_NOTEBOOKS_ENDPOINT = (
    "/me/onenote/notebooks"
    "?$expand=sections,sectionGroups($expand=sections)"
)


class OneNoteContainerEnumerator:
    """
    Enumerate the complete current OneNote container structure.
    """

    source_name = "onenote"

    def enumerate(self):
        """
        Return the complete current OneNote container observation.

        Returns:
            dict:
                {
                    "containers": [...],
                    "enumeration_complete": True
                }
        """

        containers = []

        section_ids = set()
        section_group_ids = set()

        notebooks = self._get_collection(
            ONENOTE_NOTEBOOKS_ENDPOINT
        )

        for notebook in notebooks:

            notebook_id = notebook.get(
                "id"
            )

            notebook_name = notebook.get(
                "displayName"
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

            containers.append(
                {
                    "source_object_id":
                        notebook_id,

                    "parent_source_object_id":
                        None,

                    "name":
                        str(notebook_name).strip(),
                }
            )

            for section in notebook.get(
                "sections",
                [],
            ):
                self._add_section(
                    section=section,
                    containers=containers,
                    section_ids=section_ids,
                    parent_object_id=notebook_id,
                )

            for section_group in notebook.get(
                "sectionGroups",
                [],
            ):
                self._add_section_group(
                    section_group=section_group,
                    containers=containers,
                    section_ids=section_ids,
                    section_group_ids=section_group_ids,
                    parent_object_id=notebook_id,
                )

        return {
            "containers":
                containers,

            "enumeration_complete":
                True,
        }

    def _get_collection(
        self,
        endpoint,
    ):
        """
        Retrieve an entire Microsoft Graph collection.

        Follows @odata.nextLink until the collection is complete.
        """

        objects = []

        next_endpoint = endpoint

        while next_endpoint is not None:

            response = graph_get(
                next_endpoint
            )

            response_data = response.json()

            page_objects = response_data.get(
                "value"
            )

            if page_objects is None:
                raise RuntimeError(
                    "Microsoft Graph collection "
                    "response did not contain "
                    "the expected 'value' field."
                )

            objects.extend(
                page_objects
            )

            next_endpoint = response_data.get(
                "@odata.nextLink"
            )

        return objects

    def _add_section(
        self,
        section,
        containers,
        section_ids,
        parent_object_id,
    ):
        """
        Add one OneNote section to the container observation.
        """

        section_id = section.get(
            "id"
        )

        if not section_id:
            raise RuntimeError(
                "OneNote section is missing "
                "its source object ID."
            )

        if section_id in section_ids:
            return

        section_name = (
            section.get("displayName")
            or section.get("name")
        )

        if not section_name:
            raise RuntimeError(
                "OneNote section is missing "
                "its display name."
            )

        section_ids.add(
            section_id
        )

        containers.append(
            {
                "source_object_id":
                    section_id,

                "parent_source_object_id":
                    parent_object_id,

                "name":
                    str(section_name).strip(),
            }
        )

    def _add_section_group(
        self,
        section_group,
        containers,
        section_ids,
        section_group_ids,
        parent_object_id,
    ):
        """
        Add one OneNote section group and recursively enumerate
        nested section groups.
        """

        section_group_id = section_group.get(
            "id"
        )

        if not section_group_id:
            raise RuntimeError(
                "OneNote section group is missing "
                "its source object ID."
            )

        if section_group_id in section_group_ids:
            return

        section_group_name = (
            section_group.get("displayName")
            or section_group.get("name")
        )

        if not section_group_name:
            raise RuntimeError(
                "OneNote section group is missing "
                "its display name."
            )

        section_group_ids.add(
            section_group_id
        )

        containers.append(
            {
                "source_object_id":
                    section_group_id,

                "parent_source_object_id":
                    parent_object_id,

                "name":
                    str(section_group_name).strip(),
            }
        )

        for section in section_group.get(
            "sections",
            [],
        ):
            self._add_section(
                section=section,
                containers=containers,
                section_ids=section_ids,
                parent_object_id=section_group_id,
            )

        child_groups_endpoint = (
            "/me/onenote/sectionGroups/"
            f"{section_group_id}/sectionGroups"
            "?$expand=sections"
        )

        child_groups = self._get_collection(
            child_groups_endpoint
        )

        for child_group in child_groups:

            self._add_section_group(
                section_group=child_group,
                containers=containers,
                section_ids=section_ids,
                section_group_ids=section_group_ids,
                parent_object_id=section_group_id,
            )