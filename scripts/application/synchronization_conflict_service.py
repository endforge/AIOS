"""
AlphaOmega Synchronization Conflict Service

Purpose:
    Evaluates whether a requested synchronization scope conflicts with
    synchronization operations already running for the same Source.

Responsibilities:
    - Read active synchronization scopes from persisted Synchronization Runs.
    - Read the active persisted Source Container catalog for the Source.
    - Evaluate same-Container, ancestor, and descendant scope conflicts.
    - Return the conflicting active Source Container identities.
    - Keep synchronization conflict evaluation within the application layer.

Does NOT:
    - Perform persisted synchronization admission.
    - Detect Source Container Refresh conflicts.
    - Create or update Processing Jobs.
    - Create Synchronization Runs.
    - Reserve synchronization execution.
    - Access a Source of Truth.
    - Execute synchronization.
"""


class SynchronizationConflictService:
    """
    Coordinate persisted active synchronization state with
    synchronization hierarchy conflict detection.
    """

    def __init__(
        self,
        *,
        sync_run_repository,
        source_container_repository,
        scope_conflict_detector,
    ):
        if sync_run_repository is None:
            raise ValueError(
                "sync_run_repository is required."
            )

        if source_container_repository is None:
            raise ValueError(
                "source_container_repository is required."
            )

        if scope_conflict_detector is None:
            raise ValueError(
                "scope_conflict_detector is required."
            )

        self._sync_run_repository = (
            sync_run_repository
        )

        self._source_container_repository = (
            source_container_repository
        )

        self._scope_conflict_detector = (
            scope_conflict_detector
        )

    def find_conflicts(
        self,
        *,
        source_id,
        source_container_id,
    ):
        """
        Return active synchronization scopes that conflict with the
        requested Source Container.

        The supplied identities are expected to have already passed
        persisted synchronization admission.
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

        active_source_container_ids = (
            self._sync_run_repository
            .find_active_source_container_ids_by_source(
                source_id
            )
        )

        if not active_source_container_ids:
            return ()

        source_containers = (
            self._source_container_repository
            .find_active_by_source(
                source_id
            )
        )

        return (
            self._scope_conflict_detector
            .find_conflicts(
                requested_source_container_id=(
                    source_container_id
                ),
                active_source_container_ids=(
                    active_source_container_ids
                ),
                source_containers=(
                    source_containers
                ),
            )
        )

    def has_conflict(
        self,
        *,
        source_id,
        source_container_id,
    ):
        """
        Return True when the requested synchronization scope overlaps
        at least one synchronization currently running for the Source.
        """

        return bool(
            self.find_conflicts(
                source_id=source_id,
                source_container_id=(
                    source_container_id
                ),
            )
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