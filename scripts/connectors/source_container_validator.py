"""
AlphaOmega Source Container Validator

Purpose:
    Routes Source Container validation to the validator responsible for
    the selected Source of Truth.

Responsibilities:
    - Accept Source Container validation requests through one stable
      Connector-layer interface.
    - Route validation to the registered source-specific validator.
    - Return source-specific validation results without interpreting them.
    - Provide an extensible registration point for future Sources of Truth.

Does NOT:
    - Communicate directly with any Source of Truth.
    - Contain Microsoft Graph-specific behavior.
    - Perform persisted synchronization admission.
    - Determine synchronization conflicts.
    - Modify the Source Container Catalog.
    - Create Processing Jobs or Synchronization Runs.
    - Reserve or execute synchronization.
"""


class SourceContainerValidator:
    """
    Route Source Container validation to source-specific validators.
    """

    def __init__(
        self,
        validators,
    ):
        if validators is None:
            raise ValueError(
                "validators is required."
            )

        self._validators = {}

        for source_name, validator in validators.items():

            normalized_source_name = (
                self._require_identifier(
                    source_name,
                    "source_name",
                ).lower()
            )

            if validator is None:
                raise ValueError(
                    "Source Container validator is required "
                    f"for Source '{normalized_source_name}'."
                )

            if (
                normalized_source_name
                in self._validators
            ):
                raise ValueError(
                    "Duplicate Source Container validator "
                    f"registration: '{normalized_source_name}'."
                )

            self._validators[
                normalized_source_name
            ] = validator

    def validate(
        self,
        *,
        source_name,
        source_object_id,
    ):
        """
        Validate one Source Container against its Source of Truth.

        Returns the result produced by the registered source-specific
        validator.
        """

        source_name = (
            self._require_identifier(
                source_name,
                "source_name",
            ).lower()
        )

        source_object_id = (
            self._require_identifier(
                source_object_id,
                "source_object_id",
            )
        )

        validator = self._validators.get(
            source_name
        )

        if validator is None:
            raise ValueError(
                "No Source Container validator is registered "
                f"for Source '{source_name}'."
            )

        return validator.validate(
            source_object_id=source_object_id
        )

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