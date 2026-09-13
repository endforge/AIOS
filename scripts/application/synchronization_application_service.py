"""
AlphaOmega Synchronization Application Service

Purpose:
    Provides the production application capability for processing one
    SynchronizationRequest from persisted admission through synchronization
    execution.

Responsibilities:
    - Validate the requested Source and Source Container against persisted
      AlphaOmega state.
    - Enforce application-level Source scope rules.
    - Perform preliminary persisted conflict evaluation.
    - Validate the admitted synchronization scope against its Source of Truth.
    - Invoke authoritative synchronization reservation and execution.
    - Return one application-facing operational result.

Does NOT:
    - Access the database directly.
    - Communicate directly with a Source of Truth.
    - Determine synchronization hierarchy conflicts itself.
    - Create Processing Jobs or Synchronization Runs itself.
    - Implement Source-specific Connector behavior.
    - Duplicate synchronization pipeline logic.
    - Perform UI presentation.
"""

from scripts.sync.source_container_root_service import (
    SourceContainerRootService,
)


class SynchronizationApplicationService:
    """
    Process one production SynchronizationRequest through the
    complete application-layer synchronization path.
    """

    def __init__(
        self,
        *,
        admission_service,
        preliminary_conflict_service,
        source_container_validator,
        execution_service,
    ):
        dependencies = {
            "admission_service":
                admission_service,

            "preliminary_conflict_service":
                preliminary_conflict_service,

            "source_container_validator":
                source_container_validator,

            "execution_service":
                execution_service,
        }

        for name, dependency in dependencies.items():

            if dependency is None:
                raise ValueError(
                    f"{name} is required."
                )

        self._admission_service = (
            admission_service
        )

        self._preliminary_conflict_service = (
            preliminary_conflict_service
        )

        self._source_container_validator = (
            source_container_validator
        )

        self._execution_service = (
            execution_service
        )

    def execute(
        self,
        request,
        *,
        metadata=None,
    ):
        """
        Process one production synchronization request.

        Execution order:

            Persisted admission
                ->
            Application scope policy
                ->
            Preliminary conflict evaluation
                ->
            Source-of-Truth validation
                ->
            Authoritative reservation and execution
        """

        if request is None:
            raise ValueError(
                "request is required."
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise ValueError(
                "metadata must be a dictionary."
            )

        # -------------------------------------------------
        # Persisted synchronization admission
        # -------------------------------------------------

        admitted = (
            self
            ._admission_service
            .validate(
                request
            )
        )

        if not isinstance(
            admitted,
            dict,
        ):
            raise RuntimeError(
                "Synchronization admission returned "
                "an invalid result."
            )

        source_name = self._require_result_text(
            admitted,
            "source_name",
        )

        source_id = self._require_result_text(
            admitted,
            "source_id",
        )

        source_container_id = (
            self._require_result_text(
                admitted,
                "source_container_id",
            )
        )

        source_object_id = (
            self._require_result_text(
                admitted,
                "source_object_id",
            )
        )

        container_name = (
            self._require_result_text(
                admitted,
                "container_name",
            )
        )

        normalized_source_name = (
            source_name.casefold()
        )

        is_source_root = (
            source_object_id
            == SourceContainerRootService
            .ROOT_SOURCE_OBJECT_ID
        )

        # -------------------------------------------------
        # Application scope policy
        # -------------------------------------------------

        if (
            normalized_source_name
            == "onedrive"
            and is_source_root
        ):
            raise ValueError(
                "Entire OneDrive synchronization is not "
                "permitted through the normal application path."
            )

        # -------------------------------------------------
        # Preliminary persisted conflict evaluation
        # -------------------------------------------------

        conflict_result = (
            self
            ._preliminary_conflict_service
            .evaluate(
                source_id=source_id,

                source_container_id=(
                    source_container_id
                ),
            )
        )

        if not isinstance(
            conflict_result,
            dict,
        ):
            raise RuntimeError(
                "Preliminary synchronization conflict "
                "evaluation returned an invalid result."
            )

        if (
            conflict_result.get(
                "allowed"
            )
            is not True
        ):
            conflict_type = (
                conflict_result.get(
                    "conflict_type"
                )
                or "unknown"
            )

            conflicting_ids = (
                conflict_result.get(
                    "conflicting_source_container_ids"
                )
                or ()
            )

            if conflicting_ids:
                conflict_detail = (
                    ", ".join(
                        str(value)
                        for value
                        in conflicting_ids
                    )
                )

                raise RuntimeError(
                    "Synchronization cannot proceed because "
                    f"of a {conflict_type} conflict with "
                    f"Source Container(s): {conflict_detail}"
                )

            raise RuntimeError(
                "Synchronization cannot proceed because "
                f"of a {conflict_type} conflict."
            )

        # -------------------------------------------------
        # Source-of-Truth validation
        # -------------------------------------------------

        source_validation = (
            self
            ._source_container_validator
            .validate(
                source_name=source_name,

                source_object_id=(
                    source_object_id
                ),
            )
        )

        if not isinstance(
            source_validation,
            dict,
        ):
            raise RuntimeError(
                "Source Container validation returned "
                "an invalid result."
            )

        if (
            source_validation.get(
                "exists"
            )
            is not True
        ):
            raise RuntimeError(
                "The selected Source Container no longer "
                "exists in the Source of Truth."
            )

        # -------------------------------------------------
        # Authoritative reservation and execution
        # -------------------------------------------------

        execution_metadata = dict(
            metadata
        )

        execution_metadata.update(
            {
                "container_name":
                    container_name,

                "application_service":
                    "synchronization_application_service",
            }
        )

        execution_result = (
            self
            ._execution_service
            .execute(
                source_name=source_name,

                source_id=source_id,

                source_container_id=(
                    source_container_id
                ),

                source_object_id=(
                    source_object_id
                ),

                metadata=(
                    execution_metadata
                ),
            )
        )

        if not isinstance(
            execution_result,
            dict,
        ):
            raise RuntimeError(
                "Synchronization execution returned "
                "an invalid result."
            )

        # -------------------------------------------------
        # Application-facing operational result
        # -------------------------------------------------

        return {
            "source_name":
                source_name,

            "source_id":
                source_id,

            "source_container_id":
                source_container_id,

            "source_object_id":
                source_object_id,

            "container_name":
                container_name,

            "is_source_root":
                is_source_root,

            "admission":
                admitted,

            "preliminary_conflict":
                conflict_result,

            "source_validation":
                source_validation,

            "execution":
                execution_result,
        }

    @staticmethod
    def _require_result_text(
        result,
        field_name,
    ):
        """
        Require one non-empty field from an application result.
        """

        value = result.get(
            field_name
        )

        if (
            value is None
            or not str(
                value
            ).strip()
        ):
            raise RuntimeError(
                "Synchronization admission result is "
                f"missing {field_name}."
            )

        return str(
            value
        ).strip()