"""
AlphaOmega Synchronization Scope Connector

Purpose:
    Provides the generic Connector boundary for enumerating one selected
    synchronization scope.

Responsibilities:
    - Accept the canonical Source name and source-native Container identity.
    - Route the requested scope to the registered source-specific Connector.
    - Require source-specific Connectors to enumerate only the requested scope.
    - Preserve an extensible boundary for future Sources of Truth.

Does NOT:
    - Implement Microsoft Graph retrieval.
    - Determine synchronization scope from AlphaOmega database identity.
    - Perform persisted admission.
    - Perform conflict detection.
    - Reserve synchronization execution.
    - Create Processing Jobs or Synchronization Runs.
    - Execute Translator, Discovery, Extraction, or Load.
"""


class SynchronizationScopeConnector:
    """
    Route one selected synchronization scope to its source-specific Connector.
    """

    def __init__(
        self,
        connectors,
    ):
        """
        Initialize the source-specific Connector registry.

        Args:
            connectors:
                Iterable of source-specific Connector instances.

                Each Connector must expose:
                    source_name
                    run(source_object_id=...)
        """

        if connectors is None:
            raise ValueError(
                "connectors are required."
            )

        self._connectors = {}

        for connector in connectors:

            if connector is None:
                raise ValueError(
                    "Connector registry cannot contain None."
                )

            source_name = getattr(
                connector,
                "source_name",
                None,
            )

            if (
                source_name is None
                or not str(
                    source_name
                ).strip()
            ):
                raise ValueError(
                    "Registered Connector must define source_name."
                )

            normalized_source_name = (
                str(
                    source_name
                )
                .strip()
                .casefold()
            )

            if (
                normalized_source_name
                in self._connectors
            ):
                raise ValueError(
                    "Duplicate synchronization scope Connector "
                    f"for Source '{source_name}'."
                )

            run_method = getattr(
                connector,
                "run",
                None,
            )

            if not callable(
                run_method
            ):
                raise ValueError(
                    "Registered Connector must provide run()."
                )

            self._connectors[
                normalized_source_name
            ] = connector

    def run(
        self,
        *,
        source_name,
        source_object_id,
    ):
        """
        Completely enumerate one selected synchronization scope.

        The supplied source_object_id is the stable source-native identity
        of the Source Container selected during application admission.
        """

        source_name = self._require_text(
            source_name,
            "source_name",
        )

        source_object_id = self._require_text(
            source_object_id,
            "source_object_id",
        )

        normalized_source_name = (
            source_name.casefold()
        )

        connector = (
            self._connectors.get(
                normalized_source_name
            )
        )

        if connector is None:
            raise ValueError(
                "No synchronization scope Connector is registered "
                f"for Source '{source_name}'."
            )

        connector_section = (
            connector.run(
                source_object_id=(
                    source_object_id
                )
            )
        )

        if connector_section is None:
            raise RuntimeError(
                "Synchronization scope Connector returned no "
                "ConnectorSection."
            )

        return connector_section

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