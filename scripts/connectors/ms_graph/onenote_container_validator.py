"""
OneNote Source Container Validator

Purpose:
    Validates that a persisted OneNote Source Container or the
    AlphaOmega Source Root is currently available through Microsoft Graph.

Responsibilities:
    - Obtain a complete current OneNote container observation.
    - Validate ordinary OneNote Containers by Microsoft Graph object ID.
    - Validate the AlphaOmega Source Root through successful complete
      OneNote enumeration.
    - Confirm absence of ordinary Containers only after complete
      enumeration succeeds.
    - Reuse the established OneNote container enumeration capability.

Does NOT:
    - Enumerate OneNote pages.
    - Retrieve OneNote page content.
    - Perform persisted synchronization admission.
    - Determine synchronization conflicts.
    - Modify the Source Container Catalog.
    - Create Processing Jobs or Synchronization Runs.
    - Reserve or execute synchronization.
"""

from scripts.connectors.ms_graph.onenote_container_enumerator import (
    OneNoteContainerEnumerator,
)
from scripts.sync.source_container_root_service import (
    SourceContainerRootService,
)


class OneNoteContainerValidator:
    """
    Validate one persisted OneNote synchronization scope
    against Microsoft Graph.
    """

    source_name = "onenote"

    def __init__(
        self,
        enumerator=None,
    ):
        if enumerator is None:
            enumerator = (
                OneNoteContainerEnumerator()
            )

        self._enumerator = enumerator

    def validate(
        self,
        *,
        source_object_id,
    ):
        """
        Validate one OneNote Source Container.

        For a normal Source Container:
            The requested Microsoft Graph identity must appear in a
            complete current OneNote container observation.

        For the AlphaOmega Source Root:
            Successful complete OneNote enumeration establishes that
            the complete OneNote Source is currently available.

        Absence is authoritative only when complete enumeration
        succeeds.
        """

        source_object_id = (
            self._require_identifier(
                source_object_id,
                "source_object_id",
            )
        )

        observation = (
            self._enumerator.enumerate()
        )

        if not isinstance(
            observation,
            dict,
        ):
            raise RuntimeError(
                "OneNote Source Container validation did not "
                "receive a valid enumeration result."
            )

        if (
            observation.get(
                "enumeration_complete"
            )
            is not True
        ):
            raise RuntimeError(
                "OneNote Source Container validation cannot "
                "complete because enumeration was incomplete."
            )

        containers = observation.get(
            "containers"
        )

        if not isinstance(
            containers,
            list,
        ):
            raise RuntimeError(
                "OneNote Source Container validation result "
                "did not contain a valid container collection."
            )

        # -------------------------------------------------
        # AlphaOmega Source Root
        #
        # The root does not correspond to a Microsoft Graph object.
        # A successful complete OneNote enumeration proves that the
        # complete Source is currently reachable.
        # -------------------------------------------------

        if (
            source_object_id
            == SourceContainerRootService
            .ROOT_SOURCE_OBJECT_ID
        ):
            return self._build_result(
                exists=True,
                source_object_id=(
                    source_object_id
                ),
                is_source_root=True,
            )

        # -------------------------------------------------
        # Source-native OneNote Container
        # -------------------------------------------------

        for container in containers:

            if not isinstance(
                container,
                dict,
            ):
                raise RuntimeError(
                    "OneNote container observation contains "
                    "an invalid container record."
                )

            observed_source_object_id = (
                container.get(
                    "source_object_id"
                )
            )

            if (
                observed_source_object_id is not None
                and str(
                    observed_source_object_id
                ).strip()
                == source_object_id
            ):
                return self._build_result(
                    exists=True,
                    source_object_id=(
                        source_object_id
                    ),
                    is_source_root=False,
                )

        return self._build_result(
            exists=False,
            source_object_id=(
                source_object_id
            ),
            is_source_root=False,
        )

    @staticmethod
    def _build_result(
        *,
        exists,
        source_object_id,
        is_source_root,
    ):
        """
        Build the OneNote validation result.
        """

        return {
            "exists":
                exists,

            "source_name":
                "onenote",

            "source_object_id":
                source_object_id,

            "is_source_root":
                is_source_root,
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