"""
OneDrive Source Container Validator

Purpose:
    Validates that a persisted OneDrive Source Container still exists
    in Microsoft Graph.

Responsibilities:
    - Retrieve one OneDrive driveItem directly by Microsoft Graph ID.
    - Confirm that the returned object matches the requested identity.
    - Confirm that the returned driveItem remains a folder.
    - Treat Microsoft Graph HTTP 404 as confirmed absence.
    - Preserve other Microsoft Graph failures as validation failures.

Does NOT:
    - Enumerate the complete OneDrive container structure.
    - Retrieve file content.
    - Perform persisted synchronization admission.
    - Determine synchronization conflicts.
    - Modify the Source Container Catalog.
    - Create Processing Jobs or Synchronization Runs.
    - Reserve or execute synchronization.
"""

import requests

from scripts.connectors.ms_graph.graph_connection import (
    graph_get,
)


class OneDriveContainerValidator:
    """
    Validate one persisted OneDrive folder against Microsoft Graph.
    """

    source_name = "onedrive"

    def validate(
        self,
        *,
        source_object_id,
    ):
        """
        Validate one OneDrive Source Container.

        Returns:
            dict:
                {
                    "exists": bool,
                    "source_name": "onedrive",
                    "source_object_id": str
                }

        Only Microsoft Graph HTTP 404 establishes confirmed absence.
        Other Source failures are raised.
        """

        source_object_id = (
            self._require_identifier(
                source_object_id,
                "source_object_id",
            )
        )

        endpoint = (
            "/me/drive/items/"
            f"{source_object_id}"
        )

        try:

            response = graph_get(
                endpoint
            )

        except requests.HTTPError as exception:

            response = exception.response

            if (
                response is not None
                and response.status_code == 404
            ):
                return self._build_result(
                    exists=False,
                    source_object_id=(
                        source_object_id
                    ),
                )

            raise

        response_data = response.json()

        if not isinstance(
            response_data,
            dict,
        ):
            raise RuntimeError(
                "OneDrive Source Container validation "
                "returned an invalid Microsoft Graph response."
            )

        returned_object_id = (
            response_data.get(
                "id"
            )
        )

        if not returned_object_id:
            raise RuntimeError(
                "OneDrive Source Container validation response "
                "did not contain a Microsoft Graph object ID."
            )

        if (
            str(
                returned_object_id
            ).strip()
            != source_object_id
        ):
            raise RuntimeError(
                "OneDrive Source Container validation returned "
                "a different Microsoft Graph object ID "
                "than requested."
            )

        exists = (
            "folder"
            in response_data
        )

        return self._build_result(
            exists=exists,
            source_object_id=(
                source_object_id
            ),
        )

    @staticmethod
    def _build_result(
        *,
        exists,
        source_object_id,
    ):
        """
        Build the OneDrive validation result.
        """

        return {
            "exists":
                exists,

            "source_name":
                "onedrive",

            "source_object_id":
                source_object_id,
        }

    @staticmethod
    def _require_identifier(
        value,
        field_name,
    ):
        """
        Require a non-empty identifier.
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