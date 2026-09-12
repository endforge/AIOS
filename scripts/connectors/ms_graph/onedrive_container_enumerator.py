"""
File:
    onedrive_container_enumerator.py

Purpose:
    Completely enumerates the current OneDrive container structure.

Responsibilities:
    - Enumerate OneDrive using Microsoft Graph delta.
    - Follow Microsoft Graph paging until enumeration is complete.
    - Require a final deltaLink as proof of complete enumeration.
    - Preserve each folder's Microsoft Graph source object ID.
    - Preserve its immediate parent source object ID when available.
    - Preserve its human-readable name.
    - Return containers only.

This module does NOT:
    - Retrieve file content.
    - Synchronize content.
    - Translate AlphaOmega Knowledge Objects.
    - Determine synchronization state.
    - Create Processing Jobs.
    - Persist Source Containers.
    - Reconcile the Source Container Catalog.
"""

from scripts.connectors.ms_graph.graph_connection import graph_get


ONEDRIVE_DELTA_ENDPOINT = "/me/drive/root/delta"


class OneDriveContainerEnumerator:
    """
    Enumerate the complete current OneDrive folder structure.
    """

    source_name = "onedrive"

    def enumerate(self):
        """
        Return the complete current OneDrive container observation.

        Returns:
            dict:
                {
                    "containers": [...],
                    "enumeration_complete": True,
                    "delta_link": "..."
                }

        Raises:
            RuntimeError:
                If Microsoft Graph does not return a complete,
                trustworthy enumeration.
        """

        containers_by_id = {}

        next_endpoint = ONEDRIVE_DELTA_ENDPOINT
        delta_link = None

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
                    "OneDrive delta response did not contain "
                    "the expected 'value' field."
                )

            for item in page_objects:

                item_id = item.get(
                    "id"
                )

                if not item_id:
                    raise RuntimeError(
                        "OneDrive driveItem is missing "
                        "its source object ID."
                    )

                # A deleted item is not part of the current observation.
                if "deleted" in item:

                    containers_by_id.pop(
                        item_id,
                        None,
                    )

                    continue

                # Files are not Source Containers.
                if "folder" not in item:
                    continue

                parent_reference = (
                    item.get("parentReference")
                    or {}
                )

                containers_by_id[item_id] = {
                    "source_object_id":
                        item_id,

                    "parent_source_object_id":
                        parent_reference.get(
                            "id"
                        ),

                    "name":
                        item.get(
                            "name"
                        ),
                }

            next_link = response_data.get(
                "@odata.nextLink"
            )

            if next_link is not None:

                next_endpoint = next_link
                continue

            delta_link = response_data.get(
                "@odata.deltaLink"
            )

            if delta_link is None:
                raise RuntimeError(
                    "OneDrive delta enumeration ended "
                    "without returning @odata.deltaLink. "
                    "Complete container enumeration "
                    "cannot be proven."
                )

            next_endpoint = None

        return {
            "containers":
                list(
                    containers_by_id.values()
                ),

            "enumeration_complete":
                True,

            "delta_link":
                delta_link,
        }