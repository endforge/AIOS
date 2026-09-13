"""
AlphaOmega Source Container Observation Validator

Purpose:
    Validates Source Container observations before reconciliation or
    persistence decisions are allowed.

Responsibilities:
    - Require complete observations where completeness is necessary.
    - Validate required Source Container identity fields.
    - Reject duplicate source-native container identities.
    - Validate parent relationships within the observed hierarchy.
    - Reject structurally invalid Source Container observations.

Does NOT:
    - Enumerate Sources of Truth.
    - Compare observations with persisted catalog state.
    - Persist Source Containers.
    - Infer absence from incomplete observations.
    - Synchronize content.
"""

class SourceContainerObservationValidator:
    """
    Validate a complete Source Container observation before it may
    be used for Source Container Catalog reconciliation.

    This component does not:
        - Communicate with a Source of Truth.
        - Read or write the database.
        - Reconcile Source Containers.
        - Create Processing Jobs.
    """

    def validate(self, observation):
        """
        Validate one complete Source Container observation.

        Returns:
            list:
                The validated Container records.

        Raises:
            ValueError:
                If the observation is incomplete or invalid.
        """

        if not isinstance(observation, dict):
            raise ValueError(
                "Source Container observation must be a dictionary."
            )

        if observation.get("enumeration_complete") is not True:
            raise ValueError(
                "Source Container enumeration is not complete."
            )

        containers = observation.get("containers")

        if not isinstance(containers, list):
            raise ValueError(
                "Source Container observation must contain a container list."
            )

        containers_by_id = {}

        # -----------------------------------------------------
        # Validate individual records and unique identities.
        # -----------------------------------------------------

        for container in containers:

            if not isinstance(container, dict):
                raise ValueError(
                    "Each Source Container observation must be a dictionary."
                )

            source_object_id = container.get(
                "source_object_id"
            )

            if (
                source_object_id is None
                or not str(source_object_id).strip()
            ):
                raise ValueError(
                    "Source Container source_object_id is required."
                )

            source_object_id = str(
                source_object_id
            ).strip()

            if source_object_id in containers_by_id:
                raise ValueError(
                    "Duplicate Source Container source_object_id: "
                    f"{source_object_id}"
                )

            parent_source_object_id = container.get(
                "parent_source_object_id"
            )

            if parent_source_object_id is not None:
                parent_source_object_id = str(
                    parent_source_object_id
                ).strip()

                if not parent_source_object_id:
                    parent_source_object_id = None

            name = container.get("name")

            if (
                name is None
                or not str(name).strip()
            ):
                raise ValueError(
                    "Source Container name is required."
                )

            if (
                parent_source_object_id is not None
                and parent_source_object_id == source_object_id
            ):
                raise ValueError(
                    "Source Container cannot identify itself "
                    f"as its parent: {source_object_id}"
                )

            containers_by_id[source_object_id] = {
                "source_object_id":
                    source_object_id,

                "parent_source_object_id":
                    parent_source_object_id,

                "name":
                    str(name).strip(),
            }

        # -----------------------------------------------------
        # Validate represented parent relationships.
        # -----------------------------------------------------

        for container in containers_by_id.values():

            parent_id = container[
                "parent_source_object_id"
            ]

            if (
                parent_id is not None
                and parent_id not in containers_by_id
            ):
                raise ValueError(
                    "Source Container parent is not present "
                    "in the complete observation: "
                    f"{parent_id}"
                )

        # -----------------------------------------------------
        # Validate hierarchy for cycles.
        # -----------------------------------------------------

        for source_object_id in containers_by_id:

            visited = set()
            current_id = source_object_id

            while current_id is not None:

                if current_id in visited:
                    raise ValueError(
                        "Source Container hierarchy contains a cycle "
                        f"involving: {current_id}"
                    )

                visited.add(current_id)

                current = containers_by_id.get(
                    current_id
                )

                if current is None:
                    break

                current_id = current[
                    "parent_source_object_id"
                ]

        return list(
            containers_by_id.values()
        )