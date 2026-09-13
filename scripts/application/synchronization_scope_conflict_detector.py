"""
AlphaOmega Synchronization Scope Conflict Detector

Purpose:
    Determines whether a requested synchronization scope overlaps one or
    more other synchronization scopes within the same Source hierarchy.

Responsibilities:
    - Resolve Source Containers from the supplied persisted catalog.
    - Detect same-Container synchronization conflicts.
    - Detect ancestor and descendant synchronization conflicts.
    - Allow sibling and otherwise disjoint synchronization scopes.
    - Keep synchronization conflict evaluation isolated by Source.

Does NOT:
    - Access the database.
    - Determine which synchronization operations are currently active.
    - Detect Source Container Refresh conflicts.
    - Reserve synchronization execution.
    - Create Processing Jobs or Synchronization Runs.
    - Execute synchronization.
"""


class SynchronizationScopeConflictDetector:
    """
    Evaluate synchronization scope overlap using persisted
    Source Container hierarchy.
    """

    def find_conflicts(
        self,
        *,
        requested_source_container_id,
        active_source_container_ids,
        source_containers,
    ):
        """
        Return active Source Container IDs that conflict with the
        requested synchronization scope.

        A conflict exists when an active synchronization scope:

            - is the requested Container
            - is an ancestor of the requested Container
            - is a descendant of the requested Container

        Sibling and otherwise disjoint Containers do not conflict.

        Containers belonging to another Source do not conflict.
        """

        requested_source_container_id = (
            self._require_identifier(
                requested_source_container_id,
                "requested_source_container_id",
            )
        )

        if active_source_container_ids is None:
            raise ValueError(
                "active_source_container_ids is required."
            )

        if source_containers is None:
            raise ValueError(
                "source_containers is required."
            )

        containers = list(
            source_containers
        )

        container_by_id = (
            self._build_container_id_map(
                containers
            )
        )

        requested_container = (
            container_by_id.get(
                requested_source_container_id
            )
        )

        if requested_container is None:
            raise ValueError(
                "Requested Source Container was not found "
                "in the supplied catalog."
            )

        requested_source_id = (
            self._require_record_identifier(
                requested_container,
                "source_id",
            )
        )

        requested_source_object_id = (
            self._require_record_identifier(
                requested_container,
                "source_object_id",
            )
        )

        parent_by_source_object_id = (
            self._build_parent_map(
                containers=containers,
                source_id=requested_source_id,
            )
        )

        conflicts = []

        seen_active_ids = set()

        for active_source_container_id in (
            active_source_container_ids
        ):

            active_source_container_id = (
                self._require_identifier(
                    active_source_container_id,
                    "active_source_container_id",
                )
            )

            if (
                active_source_container_id
                in seen_active_ids
            ):
                continue

            seen_active_ids.add(
                active_source_container_id
            )

            active_container = (
                container_by_id.get(
                    active_source_container_id
                )
            )

            if active_container is None:
                raise ValueError(
                    "Active Source Container was not found "
                    "in the supplied catalog: "
                    f"{active_source_container_id}"
                )

            active_source_id = (
                self._require_record_identifier(
                    active_container,
                    "source_id",
                )
            )

            if (
                active_source_id
                != requested_source_id
            ):
                continue

            active_source_object_id = (
                self._require_record_identifier(
                    active_container,
                    "source_object_id",
                )
            )

            if (
                active_source_container_id
                == requested_source_container_id
            ):
                conflicts.append(
                    active_source_container_id
                )
                continue

            active_is_ancestor = (
                self._is_ancestor(
                    ancestor_source_object_id=(
                        active_source_object_id
                    ),
                    descendant_source_object_id=(
                        requested_source_object_id
                    ),
                    parent_by_source_object_id=(
                        parent_by_source_object_id
                    ),
                )
            )

            if active_is_ancestor:
                conflicts.append(
                    active_source_container_id
                )
                continue

            active_is_descendant = (
                self._is_ancestor(
                    ancestor_source_object_id=(
                        requested_source_object_id
                    ),
                    descendant_source_object_id=(
                        active_source_object_id
                    ),
                    parent_by_source_object_id=(
                        parent_by_source_object_id
                    ),
                )
            )

            if active_is_descendant:
                conflicts.append(
                    active_source_container_id
                )

        return tuple(
            conflicts
        )

    @staticmethod
    def _build_container_id_map(
        containers,
    ):
        """
        Build an AlphaOmega Source Container UUID lookup.
        """

        container_by_id = {}

        for container in containers:

            source_container_id = (
                SynchronizationScopeConflictDetector
                ._require_record_identifier(
                    container,
                    "id",
                )
            )

            if (
                source_container_id
                in container_by_id
            ):
                raise RuntimeError(
                    "Duplicate Source Container ID "
                    "in supplied catalog: "
                    f"{source_container_id}"
                )

            container_by_id[
                source_container_id
            ] = container

        return container_by_id

    @staticmethod
    def _build_parent_map(
        *,
        containers,
        source_id,
    ):
        """
        Build Source-native hierarchy for one Source.
        """

        parent_by_source_object_id = {}

        for container in containers:

            container_source_id = (
                SynchronizationScopeConflictDetector
                ._require_record_identifier(
                    container,
                    "source_id",
                )
            )

            if container_source_id != source_id:
                continue

            source_object_id = (
                SynchronizationScopeConflictDetector
                ._require_record_identifier(
                    container,
                    "source_object_id",
                )
            )

            if (
                source_object_id
                in parent_by_source_object_id
            ):
                raise RuntimeError(
                    "Duplicate Source-native Container identity "
                    "in supplied catalog: "
                    f"{source_object_id}"
                )

            parent_source_object_id = (
                container.get(
                    "parent_source_object_id"
                )
            )

            if (
                parent_source_object_id is not None
                and str(
                    parent_source_object_id
                ).strip()
            ):
                parent_source_object_id = str(
                    parent_source_object_id
                ).strip()

            else:
                parent_source_object_id = None

            parent_by_source_object_id[
                source_object_id
            ] = parent_source_object_id

        return parent_by_source_object_id

    @staticmethod
    def _is_ancestor(
        *,
        ancestor_source_object_id,
        descendant_source_object_id,
        parent_by_source_object_id,
    ):
        """
        Determine whether one Source-native Container identity
        is an ancestor of another.
        """

        current_source_object_id = (
            descendant_source_object_id
        )

        visited = set()

        while True:

            if (
                current_source_object_id
                in visited
            ):
                raise RuntimeError(
                    "Cycle detected in Source Container hierarchy."
                )

            visited.add(
                current_source_object_id
            )

            if (
                current_source_object_id
                not in parent_by_source_object_id
            ):
                raise RuntimeError(
                    "Source Container hierarchy references "
                    "an unknown Container: "
                    f"{current_source_object_id}"
                )

            parent_source_object_id = (
                parent_by_source_object_id[
                    current_source_object_id
                ]
            )

            if parent_source_object_id is None:
                return False

            if (
                parent_source_object_id
                == ancestor_source_object_id
            ):
                return True

            current_source_object_id = (
                parent_source_object_id
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

    @staticmethod
    def _require_record_identifier(
        record,
        field_name,
    ):
        """
        Require one identifier from a Source Container record.
        """

        if not isinstance(
            record,
            dict,
        ):
            raise ValueError(
                "Source Container records must be dictionaries."
            )

        return (
            SynchronizationScopeConflictDetector
            ._require_identifier(
                record.get(
                    field_name
                ),
                field_name,
            )
        )