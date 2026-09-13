"""
AlphaOmega Synchronization Execution Service

Purpose:
    Coordinates an admitted synchronization request from atomic
    reservation through Connector execution and the existing
    synchronization pipeline.

Responsibilities:
    - Validate the admitted synchronization scope.
    - Recognize an AlphaOmega Source Root Container as an entire-Source scope.
    - Enforce Source-specific synchronization scope rules.
    - Reserve the synchronization scope atomically.
    - Execute the correct Source-specific Connector path.
    - Pass the reserved Processing Job and completed ConnectorSection
      to the Synchronization Orchestrator.
    - Fail a reserved Processing Job if execution fails before the
      Orchestrator assumes lifecycle responsibility.
    - Return the completed synchronization result.

Does NOT:
    - Perform persisted synchronization admission.
    - Perform preliminary conflict detection.
    - Determine hierarchy conflicts.
    - Implement Source-specific Connector behavior.
    - Create Processing Jobs independently.
    - Create Synchronization Runs independently.
    - Duplicate synchronization pipeline logic.
"""

from scripts.sync.source_container_root_service import (
    SourceContainerRootService,
)


class SynchronizationExecutionService:
    """
    Execute one admitted synchronization scope.
    """

    def __init__(
        self,
        *,
        reservation_repository,
        processing_job_repository,
        connector_service,
        orchestrator,
        pipeline_version,
    ):
        dependencies = {
            "reservation_repository":
                reservation_repository,

            "processing_job_repository":
                processing_job_repository,

            "connector_service":
                connector_service,

            "orchestrator":
                orchestrator,
        }

        for name, dependency in dependencies.items():

            if dependency is None:
                raise ValueError(
                    f"{name} is required."
                )

        if (
            pipeline_version is None
            or not str(
                pipeline_version
            ).strip()
        ):
            raise ValueError(
                "pipeline_version is required."
            )

        self._reservation_repository = (
            reservation_repository
        )

        self._processing_job_repository = (
            processing_job_repository
        )

        self._connector_service = (
            connector_service
        )

        self._orchestrator = orchestrator

        self._pipeline_version = (
            str(
                pipeline_version
            ).strip()
        )

    def execute(
        self,
        *,
        source_name,
        source_id,
        source_container_id,
        source_object_id,
        metadata=None,
    ):
        """
        Reserve and execute one admitted synchronization scope.

        The AlphaOmega Source Root Container represents an
        entire-Source synchronization request.

        OneDrive:
            Source Root synchronization is not permitted through
            the normal application path.

        OneNote:
            Source Root synchronization means Entire OneNote.
        """

        source_name = self._require_text(
            source_name,
            "source_name",
        )

        source_id = self._require_text(
            source_id,
            "source_id",
        )

        source_container_id = self._require_text(
            source_container_id,
            "source_container_id",
        )

        source_object_id = self._require_text(
            source_object_id,
            "source_object_id",
        )

        normalized_source_name = (
            source_name.casefold()
        )

        if normalized_source_name not in (
            "onedrive",
            "onenote",
        ):
            raise ValueError(
                "Unsupported synchronization Source: "
                f"{source_name}"
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

        is_source_root = (
            source_object_id
            == SourceContainerRootService
            .ROOT_SOURCE_OBJECT_ID
        )

        # -------------------------------------------------
        # Enforce Source-specific scope rules
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
        # Build reservation metadata
        # -------------------------------------------------

        reservation_metadata = dict(
            metadata
        )

        reservation_metadata.update(
            {
                "source_name":
                    source_name,

                "source_object_id":
                    source_object_id,

                "is_source_root":
                    is_source_root,
            }
        )

        # -------------------------------------------------
        # Atomically reserve synchronization scope
        # -------------------------------------------------

        reservation = (
            self
            ._reservation_repository
            .reserve(
                source_id=source_id,

                source_container_id=(
                    source_container_id
                ),

                pipeline_version=(
                    self._pipeline_version
                ),

                metadata=(
                    reservation_metadata
                ),
            )
        )

        processing_job_id = (
            reservation[
                "processing_job_id"
            ]
        )

        sync_run_id = (
            reservation[
                "sync_run_id"
            ]
        )

        orchestrator_started = False

        try:

            # -------------------------------------------------
            # Resolve Connector execution scope
            # -------------------------------------------------

            connector_source_object_id = (
                None
                if is_source_root
                else source_object_id
            )

            # -------------------------------------------------
            # Execute the correct Connector path
            # -------------------------------------------------

            connector_section = (
                self
                ._connector_service
                .execute(
                    source_name=source_name,

                    source_object_id=(
                        connector_source_object_id
                    ),
                )
            )

            # -------------------------------------------------
            # Hand lifecycle ownership to the Orchestrator
            # -------------------------------------------------

            orchestrator_started = True

            result = (
                self
                ._orchestrator
                .run_reserved(
                    processing_job_id=(
                        processing_job_id
                    ),

                    connector_section=(
                        connector_section
                    ),
                )
            )

            # -------------------------------------------------
            # Verify reserved Processing Job identity
            # -------------------------------------------------

            returned_processing_job_id = (
                result.get(
                    "processing_job_id"
                )
                if isinstance(
                    result,
                    dict,
                )
                else None
            )

            if (
                returned_processing_job_id is None
                or str(
                    returned_processing_job_id
                ).strip()
                != processing_job_id
            ):
                raise RuntimeError(
                    "Synchronization Orchestrator returned "
                    "an unexpected Processing Job identity."
                )

            # -------------------------------------------------
            # Return application execution result
            # -------------------------------------------------

            return {
                "processing_job_id":
                    processing_job_id,

                "sync_run_id":
                    sync_run_id,

                "source_id":
                    reservation[
                        "source_id"
                    ],

                "source_container_id":
                    reservation[
                        "source_container_id"
                    ],

                "source_object_id":
                    source_object_id,

                "is_source_root":
                    is_source_root,

                "result":
                    result,
            }

        except Exception as error:

            # Before run_reserved() begins, this service owns
            # the reserved Processing Job.
            #
            # After run_reserved() begins, the Orchestrator owns
            # Processing Job completion and failure handling.

            if not orchestrator_started:

                try:

                    self._processing_job_repository.fail(
                        processing_job_id,
                        error,
                    )

                except Exception as job_error:

                    raise RuntimeError(
                        "Synchronization execution failed and "
                        "the reserved Processing Job could not "
                        "be marked failed."
                    ) from job_error

            raise

    @staticmethod
    def _require_text(
        value,
        field_name,
    ):
        """
        Require and normalize one non-empty text value.
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