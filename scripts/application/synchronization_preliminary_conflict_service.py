"""
AlphaOmega Synchronization Preliminary Conflict Service

Purpose:
    Performs preliminary persisted conflict evaluation for an admitted
    synchronization request before Source-of-Truth validation and
    authoritative synchronization reservation.

Responsibilities:
    - Detect a running whole-Source Source Container Refresh.
    - Detect overlapping running synchronization scopes.
    - Reject synchronization when either persisted conflict exists.
    - Return a clear preliminary conflict result when execution may
      continue to later admission stages.

Does NOT:
    - Perform persisted synchronization identity admission.
    - Validate synchronization scope against a Source of Truth.
    - Guarantee conflict-free authoritative reservation.
    - Create or update Processing Jobs.
    - Create Synchronization Runs.
    - Reserve synchronization execution.
    - Execute synchronization.
"""


class SynchronizationPreliminaryConflictService:
    """
    Coordinate preliminary persisted conflict checks for an admitted
    synchronization request.
    """

    def __init__(
        self,
        *,
        refresh_status_repository,
        synchronization_conflict_service,
    ):
        if refresh_status_repository is None:
            raise ValueError(
                "refresh_status_repository is required."
            )

        if synchronization_conflict_service is None:
            raise ValueError(
                "synchronization_conflict_service is required."
            )

        self._refresh_status_repository = (
            refresh_status_repository
        )

        self._synchronization_conflict_service = (
            synchronization_conflict_service
        )

    def evaluate(
        self,
        *,
        source_id,
        source_container_id,
    ):
        """
        Evaluate persisted preliminary conflicts.

        Returns:
            dict:
                {
                    "allowed": bool,
                    "conflict_type": str | None,
                    "conflicting_source_container_ids": tuple
                }

        A whole-Source Refresh takes precedence because any active Refresh
        conflicts with every synchronization scope for that Source.

        This result is preliminary only. A later authoritative atomic
        reservation must repeat/enforce concurrency rules transactionally.
        """

        source_id = self._require_identifier(
            source_id,
            "source_id",
        )

        source_container_id = (
            self._require_identifier(
                source_container_id,
                "source_container_id",
            )
        )

        if (
            self._refresh_status_repository
            .has_active_refresh(
                source_id
            )
        ):
            return {
                "allowed":
                    False,

                "conflict_type":
                    "source_container_refresh",

                "conflicting_source_container_ids":
                    (),
            }

        conflicting_source_container_ids = (
            self._synchronization_conflict_service
            .find_conflicts(
                source_id=source_id,
                source_container_id=(
                    source_container_id
                ),
            )
        )

        if conflicting_source_container_ids:
            return {
                "allowed":
                    False,

                "conflict_type":
                    "synchronization_scope",

                "conflicting_source_container_ids":
                    tuple(
                        conflicting_source_container_ids
                    ),
            }

        return {
            "allowed":
                True,

            "conflict_type":
                None,

            "conflicting_source_container_ids":
                (),
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