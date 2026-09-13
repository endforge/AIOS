"""
AlphaOmega Source Browsing Service

Purpose:
    Provides the application-facing capability for browsing registered
    Sources and their persisted Source Container hierarchy.

Responsibilities:
    - List enabled registered Sources.
    - Validate that a requested Source exists and is enabled.
    - Retrieve active persisted Source Containers for a Source.
    - Construct the application-facing Source Container hierarchy.
    - Expose AlphaOmega Source and Source Container identities to callers.

Does NOT:
    - Access the database directly.
    - Communicate with a Source of Truth.
    - Enumerate or refresh Source Containers.
    - Synchronize content.
    - Create Processing Jobs or Synchronization Runs.
    - Perform UI presentation.
"""


class SourceBrowsingService:
    """
    Provide Source and Source Container browsing to application clients.
    """

    def __init__(
        self,
        *,
        source_repository,
        source_container_repository,
    ):
        """
        Initialize Source browsing dependencies.
        """

        if source_repository is None:
            raise ValueError(
                "source_repository is required."
            )

        if source_container_repository is None:
            raise ValueError(
                "source_container_repository is required."
            )

        self._source_repository = (
            source_repository
        )

        self._source_container_repository = (
            source_container_repository
        )

    def list_sources(
        self,
    ):
        """
        Return enabled registered Sources available for browsing.

        Only application-facing Source data is returned.
        """

        sources = (
            self._source_repository
            .find_enabled()
        )

        return tuple(
            {
                "source_id":
                    source[
                        "id"
                    ],

                "name":
                    source[
                        "name"
                    ],

                "source_type":
                    source.get(
                        "source_type"
                    ),

                "description":
                    source.get(
                        "description"
                    ),
            }
            for source
            in sources
        )

    def browse_source(
        self,
        source_id,
    ):
        """
        Return the active persisted Source Container hierarchy
        for one registered enabled Source.

        Source-native identifiers are used internally to reconstruct
        hierarchy.

        They are not exposed through the returned application model.

        The AlphaOmega Source Container UUID is the application-facing
        Container identity.
        """

        if (
            source_id is None
            or not str(
                source_id
            ).strip()
        ):
            raise ValueError(
                "source_id is required."
            )

        source_id = (
            str(
                source_id
            ).strip()
        )

        source = (
            self._source_repository
            .find_by_id(
                source_id
            )
        )

        if source is None:
            raise ValueError(
                "Source does not exist."
            )

        if (
            source.get(
                "is_enabled"
            )
            is not True
        ):
            raise ValueError(
                "Source is not enabled."
            )

        containers = (
            self
            ._source_container_repository
            .find_active_by_source(
                source_id
            )
        )

        roots = (
            self._build_hierarchy(
                containers
            )
        )

        return {
            "source": {
                "source_id":
                    source[
                        "id"
                    ],

                "name":
                    source[
                        "name"
                    ],

                "source_type":
                    source.get(
                        "source_type"
                    ),

                "description":
                    source.get(
                        "description"
                    ),
            },

            "container_count":
                len(
                    containers
                ),

            "roots":
                roots,
        }

    @staticmethod
    def _build_hierarchy(
        containers,
    ):
        """
        Convert the flat persisted Source Container catalog into
        application-facing hierarchical data.

        Source-native identity is used only while reconstructing
        parent-child relationships.
        """

        source_object_map = {}

        for container in containers:

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
                raise RuntimeError(
                    "Source Container is missing source_object_id."
                )

            source_object_id = (
                str(
                    source_object_id
                ).strip()
            )

            if (
                source_object_id
                in source_object_map
            ):
                raise RuntimeError(
                    "Duplicate Source Container source identity."
                )

            source_object_map[
                source_object_id
            ] = {
                "record":
                    container,

                "node": {
                    "source_container_id":
                        container[
                            "id"
                        ],

                    "name":
                        container[
                            "name"
                        ],

                    "children":
                        [],
                },
            }

        roots = []

        for entry in (
            source_object_map.values()
        ):

            record = (
                entry[
                    "record"
                ]
            )

            node = (
                entry[
                    "node"
                ]
            )

            parent_source_object_id = (
                record.get(
                    "parent_source_object_id"
                )
            )

            if (
                parent_source_object_id
                is None
                or not str(
                    parent_source_object_id
                ).strip()
            ):
                roots.append(
                    node
                )

                continue

            parent_source_object_id = (
                str(
                    parent_source_object_id
                ).strip()
            )

            parent_entry = (
                source_object_map.get(
                    parent_source_object_id
                )
            )

            if parent_entry is None:
                raise RuntimeError(
                    "Active Source Container references "
                    "a parent that is not present in the "
                    "active Source Container catalog."
                )

            parent_entry[
                "node"
            ][
                "children"
            ].append(
                node
            )

        SourceBrowsingService._sort_hierarchy(
            roots
        )

        return tuple(
            roots
        )

    @staticmethod
    def _sort_hierarchy(
        nodes,
    ):
        """
        Sort one hierarchy level and all descendants by name.
        """

        nodes.sort(
            key=lambda node:
                str(
                    node[
                        "name"
                    ]
                ).casefold()
        )

        for node in nodes:

            SourceBrowsingService._sort_hierarchy(
                node[
                    "children"
                ]
            )

            node[
                "children"
            ] = tuple(
                node[
                    "children"
                ]
            )