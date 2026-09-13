"""
AlphaOmega Synchronization Request

Purpose:
    Represents one production synchronization request submitted to the
    AlphaOmega application layer.

Responsibilities:
    - Identify the registered AlphaOmega Source requested for synchronization.
    - Identify the registered AlphaOmega Source Container selected for
      synchronization.
    - Require non-empty source_id and source_container_id values.
    - Preserve source_id plus source_container_id as the production
      synchronization request identity.

Does NOT:
    - Validate that the Source or Source Container exists.
    - Validate that the Source Container belongs to the Source.
    - Determine whether the Source Container is active.
    - Check the Source of Truth.
    - Detect synchronization conflicts.
    - Create Processing Jobs or Synchronization Runs.
    - Execute synchronization.
"""


class SynchronizationRequest:
    """
    Represent one requested production synchronization scope.
    """

    def __init__(
        self,
        *,
        source_id,
        source_container_id,
    ):
        """
        Initialize the synchronization request.
        """

        self.source_id = self._require_identifier(
            source_id,
            "source_id",
        )

        self.source_container_id = self._require_identifier(
            source_container_id,
            "source_container_id",
        )

    @staticmethod
    def _require_identifier(
        value,
        field_name,
    ):
        """
        Require a non-empty identifier value.

        Database existence and relationship validation intentionally
        occur later at the application capability boundary.
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