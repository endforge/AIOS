"""
AlphaOmega Source Container Root Service

Purpose:
    Adds the AlphaOmega-managed Source Root Container to a validated
    Source Container hierarchy.

Responsibilities:
    - Define the stable AlphaOmega Source Root identity.
    - Add one Source Root Container to a validated container hierarchy.
    - Attach source-native top-level containers to the Source Root.
    - Preserve all existing source-native parent relationships.

Does NOT:
    - Enumerate a Source of Truth.
    - Validate Source observations.
    - Access the database.
    - Reconcile catalog state.
    - Persist Source Containers.
    - Decide whether the Source Root is selectable for synchronization.
"""


class SourceContainerRootService:
    """
    Add the AlphaOmega-managed Source Root Container to a
    validated Source Container hierarchy.
    """

    ROOT_SOURCE_OBJECT_ID = (
        "alphaomega:source-root"
    )

    ROOT_NAME = "Entire Source"

    def add_root(
        self,
        *,
        containers,
    ):
        """
        Return the container hierarchy with one AlphaOmega-managed
        Source Root Container.

        Source-native containers without a parent become direct
        children of the Source Root.
        """

        if not isinstance(
            containers,
            list,
        ):
            raise ValueError(
                "containers must be a list."
            )

        rooted_containers = []

        source_object_ids = set()

        for container in containers:

            if not isinstance(
                container,
                dict,
            ):
                raise ValueError(
                    "Each Source Container must be a dictionary."
                )

            source_object_id = (
                container.get(
                    "source_object_id"
                )
            )

            if (
                source_object_id is None
                or not str(
                    source_object_id
                ).strip()
            ):
                raise ValueError(
                    "Source Container source_object_id is required."
                )

            source_object_id = (
                str(
                    source_object_id
                ).strip()
            )

            if (
                source_object_id
                == self.ROOT_SOURCE_OBJECT_ID
            ):
                raise ValueError(
                    "Source observation contains the reserved "
                    "AlphaOmega Source Root identity."
                )

            if (
                source_object_id
                in source_object_ids
            ):
                raise ValueError(
                    "Duplicate Source Container identity: "
                    f"{source_object_id}"
                )

            source_object_ids.add(
                source_object_id
            )

            parent_source_object_id = (
                container.get(
                    "parent_source_object_id"
                )
            )

            if parent_source_object_id is not None:
                parent_source_object_id = (
                    str(
                        parent_source_object_id
                    ).strip()
                )

                if not parent_source_object_id:
                    parent_source_object_id = None

            rooted_container = dict(
                container
            )

            rooted_container[
                "source_object_id"
            ] = source_object_id

            if parent_source_object_id is None:
                rooted_container[
                    "parent_source_object_id"
                ] = (
                    self.ROOT_SOURCE_OBJECT_ID
                )
            else:
                rooted_container[
                    "parent_source_object_id"
                ] = (
                    parent_source_object_id
                )

            rooted_containers.append(
                rooted_container
            )

        rooted_containers.insert(
            0,
            {
                "source_object_id":
                    self.ROOT_SOURCE_OBJECT_ID,

                "parent_source_object_id":
                    None,

                "name":
                    self.ROOT_NAME,
            },
        )

        return rooted_containers