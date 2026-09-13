"""
OneDrive Synchronization Scope Connector

Purpose:
    Completely enumerates one selected OneDrive folder synchronization scope.

Responsibilities:
    - Begin from one selected OneDrive folder ID.
    - Retrieve the selected folder.
    - Recursively enumerate every descendant folder and file.
    - Preserve raw Microsoft Graph driveItem objects.
    - Follow Microsoft Graph paging through the existing Graph Connector
      retrieval behavior.
    - Return Connector output only after the selected scope has been
      completely enumerated.

Does NOT:
    - Enumerate the complete OneDrive Source.
    - Use the OneDrive root delta endpoint.
    - Retrieve file content.
    - Determine synchronization state.
    - Create Processing Jobs or Synchronization Runs.
    - Execute Translator, Discovery, Extraction, or Load.
"""

from scripts.connectors.connector_section import (
    ConnectorSection,
)

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)


class OneDriveSynchronizationScopeConnector(
    GraphConnector
):
    """
    Enumerate one selected OneDrive folder subtree.
    """

    source_name = "onedrive"

    def run(
        self,
        *,
        source_object_id,
    ):
        """
        Completely enumerate one selected OneDrive folder subtree.
        """

        source_object_id = self._require_text(
            source_object_id,
            "source_object_id",
        )

        selected_folder = self._get_json(
            "/me/drive/items/"
            f"{source_object_id}"
        )

        self._validate_selected_folder(
            selected_folder=selected_folder,
            requested_source_object_id=(
                source_object_id
            ),
        )

        raw_objects = [
            self._wrap_object(
                "driveItem",
                selected_folder,
            )
        ]

        pending_folder_ids = [
            source_object_id
        ]

        visited_folder_ids = set()

        folders_enumerated = 0

        while pending_folder_ids:

            folder_id = (
                pending_folder_ids.pop()
            )

            if (
                folder_id
                in visited_folder_ids
            ):
                raise RuntimeError(
                    "OneDrive folder hierarchy returned "
                    "a repeated folder identity. "
                    "Complete selected-scope enumeration "
                    "cannot be proven."
                )

            visited_folder_ids.add(
                folder_id
            )

            folders_enumerated += 1

            children = self._get_collection(
                "/me/drive/items/"
                f"{folder_id}/children"
            )

            for child in children:

                child_id = (
                    child.get(
                        "id"
                    )
                )

                if not child_id:

                    raise RuntimeError(
                        "OneDrive driveItem is missing "
                        "its source object ID."
                    )

                parent_reference = (
                    child.get(
                        "parentReference"
                    )
                    or {}
                )

                returned_parent_id = (
                    parent_reference.get(
                        "id"
                    )
                )

                if (
                    returned_parent_id
                    != folder_id
                ):
                    raise RuntimeError(
                        "Microsoft Graph returned a OneDrive "
                        "child whose parent identity does not "
                        "match the folder being enumerated."
                    )

                raw_objects.append(
                    self._wrap_object(
                        "driveItem",
                        child,
                    )
                )

                if "folder" in child:

                    pending_folder_ids.append(
                        child_id
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
                "selected_folder_subtree",

            "scope_source_object_id":
                source_object_id,

            "objects_retrieved":
                len(raw_objects),

            "folders_enumerated":
                folders_enumerated,
        }

        connector_section.connection_succeeded = (
            True
        )

        self._validate_scope_section(
            connector_section
        )

        connector_section.lock()

        return connector_section

    @staticmethod
    def _validate_selected_folder(
        *,
        selected_folder,
        requested_source_object_id,
    ):
        """
        Require the requested Graph object to be the exact selected folder.
        """

        if not isinstance(
            selected_folder,
            dict,
        ):
            raise RuntimeError(
                "Microsoft Graph returned an invalid "
                "selected OneDrive object."
            )

        returned_id = (
            selected_folder.get(
                "id"
            )
        )

        if not returned_id:

            raise RuntimeError(
                "Selected OneDrive object is missing "
                "its source object ID."
            )

        if (
            str(returned_id)
            != str(
                requested_source_object_id
            )
        ):
            raise RuntimeError(
                "Microsoft Graph returned a different "
                "OneDrive object than the requested scope."
            )

        if "folder" not in selected_folder:

            raise RuntimeError(
                "Selected OneDrive synchronization scope "
                "is not a folder."
            )

    @staticmethod
    def _validate_scope_section(
        connector_section,
    ):
        """
        Validate completed bounded OneDrive Connector output.

        The existing GraphConnector OneDrive validator requires a deltaLink
        because whole-Source enumeration uses delta. A bounded folder subtree
        does not use delta, so its completion contract is validated here.
        """

        if (
            connector_section
            .connection_succeeded
            is not True
        ):
            raise RuntimeError(
                "OneDrive synchronization scope Connector "
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
                "Selected OneDrive synchronization scope "
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
                "Completed selected OneDrive scope "
                "is missing its scope identity."
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