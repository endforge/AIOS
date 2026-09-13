"""
AlphaOmega Source Container Refresh Service

Purpose:
    Coordinates one complete production Source Container Refresh.

Responsibilities:
    - Reserve the Source for Refresh and create its Processing Job atomically.
    - Invoke the injected Source-specific container enumerator.
    - Validate the complete Source Container observation.
    - Add the AlphaOmega-managed Source Root Container.
    - Retrieve persisted Source Container state.
    - Reconcile observed and persisted containers.
    - Apply reconciliation results through the atomic Refresh database
      operation.
    - Complete or fail the Processing Job.
    - Measure and return Refresh operational results.

Does NOT:
    - Implement Source-specific enumeration.
    - Synchronize source content.
    - Create Knowledge Objects.
    - Treat incomplete enumeration as proof of absence.
    - Combine separate Sources into one Processing Job.
"""

import json

from time import perf_counter


class SourceContainerRefreshService:

    def __init__(
        self,
        *,
        enumerator,
        observation_validator,
        source_container_root_service,
        source_container_repository,
        reconciler,
        refresh_reservation_repository,
        processing_job_repository,
        database_client,
        process_type,
        pipeline_version,
    ):
        dependencies = {
            "enumerator":
                enumerator,

            "observation_validator":
                observation_validator,

            "source_container_root_service":
                source_container_root_service,

            "source_container_repository":
                source_container_repository,

            "reconciler":
                reconciler,

            "refresh_reservation_repository":
                refresh_reservation_repository,

            "processing_job_repository":
                processing_job_repository,

            "database_client":
                database_client,
        }

        for name, dependency in dependencies.items():

            if dependency is None:
                raise ValueError(
                    f"{name} is required."
                )

        if (
            process_type is None
            or not str(
                process_type
            ).strip()
        ):
            raise ValueError(
                "process_type is required."
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

        self._enumerator = enumerator

        self._observation_validator = (
            observation_validator
        )

        self._source_container_root_service = (
            source_container_root_service
        )

        self._source_container_repository = (
            source_container_repository
        )

        self._reconciler = reconciler

        self._refresh_reservation_repository = (
            refresh_reservation_repository
        )

        self._processing_job_repository = (
            processing_job_repository
        )

        self._database_client = (
            database_client
        )

        self._process_type = (
            str(
                process_type
            ).strip()
        )

        self._pipeline_version = (
            str(
                pipeline_version
            ).strip()
        )

    def refresh(
        self,
        *,
        source_id,
        job_metadata=None,
    ):
        """
        Refresh the complete Source Container Catalog for one Source.

        Returns reconciliation results, persistence results, and
        operational measurements for the completed Refresh.
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

        if job_metadata is None:
            job_metadata = {}

        if not isinstance(
            job_metadata,
            dict,
        ):
            raise ValueError(
                "job_metadata must be a dictionary."
            )

        processing_job_id = None

        total_started_at = perf_counter()

        try:

            # -------------------------------------------------
            # Reserve the Source and create its Processing Job
            # -------------------------------------------------

            reservation_started_at = (
                perf_counter()
            )

            processing_job_id = (
                self
                ._refresh_reservation_repository
                .reserve(
                    source_id=source_id,

                    process_type=(
                        self._process_type
                    ),

                    pipeline_version=(
                        self._pipeline_version
                    ),

                    metadata=job_metadata,
                )
            )

            reservation_seconds = (
                perf_counter()
                - reservation_started_at
            )

            # -------------------------------------------------
            # Complete Source enumeration
            # -------------------------------------------------

            enumeration_started_at = (
                perf_counter()
            )

            observation = (
                self._enumerator.enumerate()
            )

            enumeration_seconds = (
                perf_counter()
                - enumeration_started_at
            )

            # -------------------------------------------------
            # Validate complete Source observation
            # -------------------------------------------------

            validation_started_at = (
                perf_counter()
            )

            observed_containers = (
                self
                ._observation_validator
                .validate(
                    observation
                )
            )

            validation_seconds = (
                perf_counter()
                - validation_started_at
            )

            source_observed_count = len(
                observed_containers
            )

            # -------------------------------------------------
            # Add AlphaOmega Source Root Container
            # -------------------------------------------------

            observed_containers = (
                self
                ._source_container_root_service
                .add_root(
                    containers=(
                        observed_containers
                    )
                )
            )

            # -------------------------------------------------
            # Retrieve complete persisted catalog
            # -------------------------------------------------

            catalog_read_started_at = (
                perf_counter()
            )

            existing_containers = (
                self
                ._source_container_repository
                .find_by_source(
                    source_id
                )
            )

            catalog_read_seconds = (
                perf_counter()
                - catalog_read_started_at
            )

            # -------------------------------------------------
            # Reconcile catalog hierarchy and persisted catalog
            # -------------------------------------------------

            reconciliation_started_at = (
                perf_counter()
            )

            reconciliation = (
                self._reconciler.reconcile(
                    observed_containers=(
                        observed_containers
                    ),

                    existing_containers=(
                        existing_containers
                    ),
                )
            )

            upsert_containers = []

            for category in (
                "new",
                "existing",
                "reappearing",
            ):
                upsert_containers.extend(
                    item["observed"]
                    for item
                    in reconciliation[category]
                )

            absent_source_object_ids = [
                item[
                    "existing"
                ][
                    "source_object_id"
                ]
                for item
                in reconciliation["absent"]
            ]

            reconciliation_seconds = (
                perf_counter()
                - reconciliation_started_at
            )

            # -------------------------------------------------
            # Measure persistence payload
            # -------------------------------------------------

            persistence_payload = {
                "upsert_containers":
                    upsert_containers,

                "absent_source_object_ids":
                    absent_source_object_ids,
            }

            payload_json = json.dumps(
                persistence_payload,
                separators=(",", ":"),
                ensure_ascii=False,
            )

            payload_size_bytes = len(
                payload_json.encode(
                    "utf-8"
                )
            )

            # -------------------------------------------------
            # Apply one atomic catalog transaction
            # -------------------------------------------------

            persistence_started_at = (
                perf_counter()
            )

            response = (
                self._database_client.rpc(
                    "apply_source_container_refresh",
                    {
                        "p_source_id":
                            source_id,

                        "p_processing_job_id":
                            processing_job_id,

                        "p_observation_complete":
                            True,

                        "p_upsert_containers":
                            upsert_containers,

                        "p_absent_source_object_ids":
                            absent_source_object_ids,
                    },
                ).execute()
            )

            persistence_seconds = (
                perf_counter()
                - persistence_started_at
            )

            if response.data is None:
                raise RuntimeError(
                    "Source Container Refresh transaction "
                    "returned no result."
                )

            # -------------------------------------------------
            # Complete Processing Job
            # -------------------------------------------------

            completion_started_at = (
                perf_counter()
            )

            self._processing_job_repository.complete(
                processing_job_id
            )

            completion_seconds = (
                perf_counter()
                - completion_started_at
            )

            total_seconds = (
                perf_counter()
                - total_started_at
            )

            return {
                "processing_job_id":
                    processing_job_id,

                "source_id":
                    source_id,

                "source_observed":
                    source_observed_count,

                "catalog_containers":
                    len(
                        observed_containers
                    ),

                "observed":
                    len(
                        observed_containers
                    ),

                "new":
                    len(
                        reconciliation["new"]
                    ),

                "existing":
                    len(
                        reconciliation["existing"]
                    ),

                "reappearing":
                    len(
                        reconciliation["reappearing"]
                    ),

                "absent":
                    len(
                        reconciliation["absent"]
                    ),

                "persistence":
                    response.data,

                "measurements": {
                    "payload_size_bytes":
                        payload_size_bytes,

                    "reservation_seconds":
                        reservation_seconds,

                    "enumeration_seconds":
                        enumeration_seconds,

                    "validation_seconds":
                        validation_seconds,

                    "catalog_read_seconds":
                        catalog_read_seconds,

                    "reconciliation_seconds":
                        reconciliation_seconds,

                    "persistence_seconds":
                        persistence_seconds,

                    "completion_seconds":
                        completion_seconds,

                    "total_seconds":
                        total_seconds,
                },
            }

        except Exception as error:

            if processing_job_id is not None:

                try:
                    (
                        self
                        ._processing_job_repository
                        .fail(
                            processing_job_id,
                            error,
                        )
                    )

                except Exception as job_error:
                    raise RuntimeError(
                        "Source Container Refresh failed and "
                        "the Processing Job could not be "
                        "marked failed."
                    ) from job_error

            raise