"""
AlphaOmega Source Container Repository

Purpose:
    Provides database access to persisted AlphaOmega Source Containers.

Responsibilities:
    - Find a Source Container by AlphaOmega identity.
    - Find a Source Container by Source and source-native identity.
    - Retrieve Source Containers belonging to a Source.
    - Retrieve active Source Containers belonging to a Source.
    - Own ordinary database access to the source_containers table.

Does NOT:
    - Enumerate Sources of Truth.
    - Perform Source Container Refresh reconciliation.
    - Decide synchronization scope.
    - Build application presentation structures.
"""


class SourceContainerRepository:
    """
    Database access for persisted AlphaOmega Source Containers.

    This repository owns ordinary source_containers table access.

    It does not:
        - enumerate Sources of Truth
        - perform Source Container Refresh reconciliation
        - decide synchronization scope
        - build application presentation structures
    """

    def __init__(
        self,
        database_connection,
    ):
        if database_connection is None:
            raise ValueError(
                "database_connection is required"
            )

        self._client = (
            database_connection.connect()
        )

    def find_by_id(
        self,
        source_container_id,
    ):
        """
        Find one Source Container by its AlphaOmega UUID.
        """

        if not source_container_id:
            raise ValueError(
                "source_container_id is required"
            )

        response = (
            self._client
            .table(
                "source_containers"
            )
            .select(
                "*"
            )
            .eq(
                "id",
                str(
                    source_container_id
                ),
            )
            .execute()
        )

        rows = (
            response.data
            or []
        )

        if not rows:
            return None

        if len(rows) != 1:
            raise RuntimeError(
                "Expected one source_container for id "
                f"{source_container_id}, "
                f"found {len(rows)}"
            )

        return rows[0]

    def find_by_source_identity(
        self,
        source_id,
        source_object_id,
    ):
        """
        Find one Source Container using its Source-of-Truth identity.
        """

        if not source_id:
            raise ValueError(
                "source_id is required"
            )

        if not source_object_id:
            raise ValueError(
                "source_object_id is required"
            )

        response = (
            self._client
            .table(
                "source_containers"
            )
            .select(
                "*"
            )
            .eq(
                "source_id",
                str(
                    source_id
                ),
            )
            .eq(
                "source_object_id",
                str(
                    source_object_id
                ),
            )
            .execute()
        )

        rows = (
            response.data
            or []
        )

        if not rows:
            return None

        if len(rows) != 1:
            raise RuntimeError(
                "Expected one source_container for "
                f"source_id={source_id}, "
                f"source_object_id={source_object_id}, "
                f"found {len(rows)}"
            )

        return rows[0]

    def find_by_source(
        self,
        source_id,
    ):
        """
        Return every persisted Source Container for one Source.

        Active and inactive Containers are both returned because
        Source Container identity must survive inactivity and
        reappearance.

        Results are retrieved in stable UUID order using explicit
        pagination so Sources containing more than the Supabase
        response limit are returned completely.
        """

        if not source_id:
            raise ValueError(
                "source_id is required"
            )

        page_size = 1000
        start_index = 0
        containers = []

        while True:

            end_index = (
                start_index
                + page_size
                - 1
            )

            response = (
                self._client
                .table(
                    "source_containers"
                )
                .select(
                    "*"
                )
                .eq(
                    "source_id",
                    str(
                        source_id
                    ),
                )
                .order(
                    "id"
                )
                .range(
                    start_index,
                    end_index,
                )
                .execute()
            )

            page = (
                response.data
                or []
            )

            containers.extend(
                page
            )

            if len(page) < page_size:
                break

            start_index += (
                page_size
            )

        return containers

    def find_active_by_source(
        self,
        source_id,
    ):
        """
        Return every active persisted Source Container for one Source.

        This read supports application-facing Source browsing.

        Only fields required to construct the application browsing
        hierarchy are retrieved.

        Results use explicit pagination so complete catalogs larger
        than the Supabase response limit are returned.
        """

        if not source_id:
            raise ValueError(
                "source_id is required"
            )

        page_size = 1000
        start_index = 0
        containers = []

        while True:

            end_index = (
                start_index
                + page_size
                - 1
            )

            response = (
                self._client
                .table(
                    "source_containers"
                )
                .select(
                    "id,"
                    "source_id,"
                    "source_object_id,"
                    "parent_source_object_id,"
                    "name"
                )
                .eq(
                    "source_id",
                    str(
                        source_id
                    ),
                )
                .eq(
                    "is_active",
                    True,
                )
                .order(
                    "id"
                )
                .range(
                    start_index,
                    end_index,
                )
                .execute()
            )

            page = (
                response.data
                or []
            )

            containers.extend(
                page
            )

            if len(page) < page_size:
                break

            start_index += (
                page_size
            )

        return containers