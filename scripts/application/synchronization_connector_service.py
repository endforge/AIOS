"""
AlphaOmega Synchronization Connector Service

Purpose:
    Executes the Connector stage for an already-admitted synchronization
    request using the synchronization scope authorized by the application.

Responsibilities:
    - Enforce Source-specific synchronization scope rules.
    - Require a selected Container for OneDrive synchronization.
    - Permit either Entire Source or selected-Container synchronization
      for OneNote.
    - Route selected scopes through SynchronizationScopeConnector.
    - Route Entire Source OneNote through the existing GraphConnector.
    - Return the completed ConnectorSection for downstream pipeline stages.

Does NOT:
    - Browse or select Source Containers.
    - Validate persisted Source or Source Container identity.
    - Perform preliminary conflict detection.
    - Validate the selected Container against the Source of Truth.
    - Reserve synchronization.
    - Create Processing Jobs or Synchronization Runs.
    - Execute Translator, Discovery, Extraction, or Load.
    - Permit normal whole-Source OneDrive synchronization.
"""

from scripts.connectors.synchronization_scope_connector import (
    SynchronizationScopeConnector,
)

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)

from scripts.connectors.ms_graph.onedrive_synchronization_scope_connector import (
    OneDriveSynchronizationScopeConnector,
)

from scripts.connectors.ms_graph.onenote_synchronization_scope_connector import (
    OneNoteSynchronizationScopeConnector,
)


ONEDRIVE = "onedrive"
ONENOTE = "onenote"


class SynchronizationConnectorService:
    """
    Execute the correct Connector path for one synchronization scope.
    """

    def __init__(
        self,
        *,
        whole_source_connector=None,
        scope_connector=None,
    ):
        """
        Initialize Connector execution dependencies.

        Optional dependency injection allows isolated testing without
        Microsoft Graph access.
        """

        if whole_source_connector is None:

            whole_source_connector = (
                GraphConnector()
            )

        if scope_connector is None:

            scope_connector = (
                SynchronizationScopeConnector(
                    [
                        OneDriveSynchronizationScopeConnector(),
                        OneNoteSynchronizationScopeConnector(),
                    ]
                )
            )

        self._whole_source_connector = (
            whole_source_connector
        )

        self._scope_connector = (
            scope_connector
        )

    def execute(
        self,
        *,
        source_name,
        source_object_id=None,
    ):
        """
        Execute the Connector stage for one authorized synchronization scope.

        Scope rules:

            OneDrive:
                source_object_id is required.
                Whole-Source execution is rejected.

            OneNote:
                source_object_id provided:
                    execute selected Container scope.

                source_object_id omitted:
                    execute Entire Source using the existing GraphConnector.
        """

        source_name = self._require_text(
            source_name,
            "source_name",
        )

        normalized_source_name = (
            source_name.casefold()
        )

        # ================================================================
        # OneDrive
        # ================================================================

        if normalized_source_name == ONEDRIVE:

            source_object_id = (
                self._require_text(
                    source_object_id,
                    "source_object_id",
                )
            )

            return self._scope_connector.run(
                source_name=ONEDRIVE,
                source_object_id=(
                    source_object_id
                ),
            )

        # ================================================================
        # OneNote
        # ================================================================

        if normalized_source_name == ONENOTE:

            if (
                source_object_id is None
                or not str(
                    source_object_id
                ).strip()
            ):

                return (
                    self._whole_source_connector.run(
                        ONENOTE
                    )
                )

            return self._scope_connector.run(
                source_name=ONENOTE,
                source_object_id=(
                    str(
                        source_object_id
                    ).strip()
                ),
            )

        # ================================================================
        # Unsupported Source
        # ================================================================

        raise ValueError(
            "Unsupported synchronization Source: "
            f"'{source_name}'."
        )

    @staticmethod
    def _require_text(
        value,
        field_name,
    ):
        """
        Require and normalize one non-empty text value.
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