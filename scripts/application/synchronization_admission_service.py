"""
File:
    synchronization_admission_service.py

Purpose:
    Validate one AlphaOmega SynchronizationRequest against the
    persisted Source and Source Container catalogs.

The SynchronizationAdmissionService owns:
    - Validating that the requested Source exists.
    - Validating that the requested Source is enabled.
    - Validating that the requested Source Container exists.
    - Validating that the Source Container is active.
    - Validating that the Source Container belongs to the
      requested Source.

The SynchronizationAdmissionService does NOT:
    - Communicate with a Source of Truth.
    - Refresh Source Containers.
    - Detect synchronization overlap.
    - Reserve synchronization execution.
    - Create Processing Jobs.
    - Create Synchronization Runs.
    - Invoke the SynchronizationOrchestrator.
    - Execute synchronization.

Those responsibilities belong to later production application
capabilities.
"""


class SynchronizationAdmissionService:
    """
    Validate persisted synchronization request identity and scope.
    """

    def __init__(
        self,
        *,
        source_repository,
        source_container_repository,
    ):
        """
        Initialize synchronization admission dependencies.
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

    def validate(
        self,
        request,
    ):
        """
        Validate one SynchronizationRequest against persisted
        AlphaOmega Source and Source Container state.

        Returns an application-owned admitted request description.

        This method performs no database writes.
        """

        if request is None:
            raise ValueError(
                "request is required."
            )

        source_id = getattr(
            request,
            "source_id",
            None,
        )

        source_container_id = getattr(
            request,
            "source_container_id",
            None,
        )

        if (
            source_id is None
            or not str(
                source_id
            ).strip()
        ):
            raise ValueError(
                "request.source_id is required."
            )

        if (
            source_container_id is None
            or not str(
                source_container_id
            ).strip()
        ):
            raise ValueError(
                "request.source_container_id is required."
            )

        source_id = (
            str(
                source_id
            ).strip()
        )

        source_container_id = (
            str(
                source_container_id
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
                "Requested Source does not exist."
            )

        if (
            source.get(
                "is_enabled"
            )
            is not True
        ):
            raise ValueError(
                "Requested Source is not enabled."
            )

        source_container = (
            self
            ._source_container_repository
            .find_by_id(
                source_container_id
            )
        )

        if source_container is None:
            raise ValueError(
                "Requested Source Container does not exist."
            )

        container_source_id = (
            source_container.get(
                "source_id"
            )
        )

        if (
            container_source_id is None
            or str(
                container_source_id
            ).strip()
            != source_id
        ):
            raise ValueError(
                "Requested Source Container does not belong "
                "to the requested Source."
            )

        if (
            source_container.get(
                "is_active"
            )
            is not True
        ):
            raise ValueError(
                "Requested Source Container is not active."
            )

        return {
            "source_id":
                source_id,

            "source_container_id":
                source_container_id,

            "source_name":
                source[
                    "name"
                ],

            "source_object_id":
                source_container[
                    "source_object_id"
                ],

            "container_name":
                source_container[
                    "name"
                ],
        }