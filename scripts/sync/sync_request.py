"""
File:
    synchronization_request.py

Purpose:
    Represents one production synchronization request submitted to
    the AlphaOmega application layer.

A SynchronizationRequest identifies:
    - The registered AlphaOmega Source.
    - The registered AlphaOmega Source Container selected for
      synchronization.

The request does NOT:
    - Validate that the Source exists.
    - Validate that the Source Container exists.
    - Validate that the Source Container belongs to the Source.
    - Determine whether the Source Container is active.
    - Check the Source of Truth.
    - Detect synchronization conflicts.
    - Create Processing Jobs.
    - Create Synchronization Runs.
    - Execute synchronization.

Those responsibilities belong to the application capability that
processes the request.

Production synchronization request identity is:
    source_id + source_container_id
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