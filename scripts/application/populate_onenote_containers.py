"""
Controlled initial population of the complete OneNote
Source Container catalog.

This Lab 8 bootstrap operation measures:

- Microsoft Graph enumeration time.
- Observation validation time.
- JSON persistence payload size.
- PostgreSQL persistence time.
- Database verification time.
- Total execution time.

The operation does not:

- Synchronize OneNote pages.
- Create Knowledge Objects.
- Perform Source Container Refresh reconciliation.
- Mark Source Containers inactive.
"""

import json

from datetime import datetime, timezone
from time import perf_counter

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.connectors.ms_graph.onenote_container_enumerator import (
    OneNoteContainerEnumerator,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)

from scripts.database.processing_job_repository import (
    ProcessingJobRepository,
)

from scripts.database.source_repository import (
    SourceRepository,
)

from scripts.sync.source_container_observation_validator import (
    SourceContainerObservationValidator,
)


SOURCE_NAME = "OneNote"


def format_duration(
    seconds,
):
    """
    Format elapsed seconds for readable console output.
    """

    if seconds < 60:
        return f"{seconds:.2f} seconds"

    minutes = int(
        seconds // 60
    )

    remaining_seconds = (
        seconds % 60
    )

    return (
        f"{minutes} minutes "
        f"{remaining_seconds:.2f} seconds"
    )


def format_bytes(
    byte_count,
):
    """
    Format a byte count using readable binary units.
    """

    if byte_count < 1024:
        return f"{byte_count} bytes"

    kilobytes = (
        byte_count / 1024
    )

    if kilobytes < 1024:
        return f"{kilobytes:.2f} KiB"

    megabytes = (
        kilobytes / 1024
    )

    return f"{megabytes:.2f} MiB"


def main():

    total_started_at = (
        perf_counter()
    )

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega OneNote Initial Container Population"
    )
    print(
        "============================================================"
    )
    print()

    # ---------------------------------------------------------
    # Database connection and registered Source resolution
    # ---------------------------------------------------------

    credential_provider = (
        LocalCredentialProvider()
    )

    database_connection = (
        DatabaseConnection(
            credential_provider
        )
    )

    client = (
        database_connection.connect()
    )

    source_repository = (
        SourceRepository(
            client
        )
    )

    source_id = (
        source_repository.find_id_by_name(
            SOURCE_NAME
        )
    )

    if source_id is None:
        raise RuntimeError(
            "Registered OneNote Source was not found."
        )

    print(
        "PASS: Registered OneNote Source resolved."
    )
    print(
        f"  Source ID : {source_id}"
    )
    print()

    # ---------------------------------------------------------
    # Initial-population guardrail
    # ---------------------------------------------------------

    existing_rows = (
        client
        .table(
            "source_containers"
        )
        .select(
            "id"
        )
        .eq(
            "source_id",
            source_id,
        )
        .execute()
        .data
        or []
    )

    if existing_rows:
        raise RuntimeError(
            "SAFETY STOP: OneNote already has "
            f"{len(existing_rows)} persisted Source Containers. "
            "No database write was attempted."
        )

    print(
        "PASS: OneNote Source Container catalog is empty."
    )
    print()

    # ---------------------------------------------------------
    # Complete OneNote enumeration
    # ---------------------------------------------------------

    enumeration_started_at = (
        perf_counter()
    )

    enumerator = (
        OneNoteContainerEnumerator()
    )

    observation = (
        enumerator.enumerate()
    )

    enumeration_seconds = (
        perf_counter()
        - enumeration_started_at
    )

    if (
        observation.get(
            "enumeration_complete"
        )
        is not True
    ):
        raise RuntimeError(
            "OneNote enumeration is not complete."
        )

    containers = observation.get(
        "containers"
    )

    if not isinstance(
        containers,
        list,
    ):
        raise RuntimeError(
            "OneNote enumeration did not return "
            "a Container list."
        )

    observed_count = len(
        containers
    )

    if observed_count == 0:
        raise RuntimeError(
            "SAFETY STOP: Complete OneNote observation "
            "returned no Containers. "
            "No database write was attempted."
        )

    print(
        "PASS: Complete OneNote observation received."
    )
    print(
        f"  Observed Containers : {observed_count}"
    )
    print(
        "  Enumeration Time    : "
        f"{format_duration(enumeration_seconds)}"
    )
    print()

    # ---------------------------------------------------------
    # Observation validation
    # ---------------------------------------------------------

    validation_started_at = (
        perf_counter()
    )

    validator = (
        SourceContainerObservationValidator()
    )

    validated_containers = (
        validator.validate(
            observation
        )
    )

    validation_seconds = (
        perf_counter()
        - validation_started_at
    )

    validated_count = len(
        validated_containers
    )

    if validated_count != observed_count:
        raise RuntimeError(
            "SAFETY STOP: Validated Container count "
            "does not match the complete observation. "
            f"Observed {observed_count}, "
            f"validated {validated_count}. "
            "No database write was attempted."
        )

    root_count = sum(
        1
        for container in validated_containers
        if container[
            "parent_source_object_id"
        ] is None
    )

    if root_count == 0:
        raise RuntimeError(
            "SAFETY STOP: Validated OneNote observation "
            "contains no root Containers. "
            "No database write was attempted."
        )

    print(
        "PASS: Complete OneNote observation validated."
    )
    print(
        f"  Validated Containers : {validated_count}"
    )
    print(
        f"  Root Containers      : {root_count}"
    )
    print(
        "  Validation Time      : "
        f"{format_duration(validation_seconds)}"
    )
    print()

    # ---------------------------------------------------------
    # Measure the exact database payload
    # ---------------------------------------------------------

    payload_bytes = len(
        json.dumps(
            validated_containers,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )
    )

    print(
        "PASS: Persistence payload prepared."
    )
    print(
        f"  Container Count : {validated_count}"
    )
    print(
        "  Payload Size    : "
        f"{format_bytes(payload_bytes)}"
    )
    print()

    print(
        "All pre-write safety checks passed."
    )
    print(
        "Beginning controlled OneNote persistence."
    )
    print()

    # ---------------------------------------------------------
    # Processing Job
    # ---------------------------------------------------------

    processing_job_repository = (
        ProcessingJobRepository(
            client
        )
    )

    processing_job_id = None

    try:

        processing_job_id = (
            processing_job_repository.create(
                process_type=(
                    "source_container_refresh"
                ),
                pipeline_version=(
                    "lab8-initial-population"
                ),
                metadata={
                    "operation":
                        "controlled_initial_population",

                    "source":
                        SOURCE_NAME,

                    "container_count":
                        validated_count,

                    "root_container_count":
                        root_count,

                    "payload_bytes":
                        payload_bytes,

                    "enumeration_seconds":
                        enumeration_seconds,

                    "validation_seconds":
                        validation_seconds,
                },
            )
        )

        print(
            "PASS: Processing Job created."
        )
        print(
            f"  Processing Job ID : "
            f"{processing_job_id}"
        )
        print()

        # -----------------------------------------------------
        # Atomic persistence
        # -----------------------------------------------------

        observed_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        persistence_started_at = (
            perf_counter()
        )

        response = (
            client
            .rpc(
                "upsert_source_containers",
                {
                    "p_source_id":
                        source_id,

                    "p_processing_job_id":
                        processing_job_id,

                    "p_observed_at":
                        observed_at,

                    "p_containers":
                        validated_containers,
                },
            )
            .execute()
        )

        persistence_seconds = (
            perf_counter()
            - persistence_started_at
        )

        if response.data != validated_count:
            raise RuntimeError(
                "Persistence RPC did not report the "
                "validated number of Containers. "
                f"Expected {validated_count}, "
                f"received {response.data}."
            )

        print(
            "PASS: Atomic persistence completed."
        )
        print(
            f"  RPC Processed    : {response.data}"
        )
        print(
            "  Persistence Time : "
            f"{format_duration(persistence_seconds)}"
        )
        print()

        # -----------------------------------------------------
        # Verify the persisted OneNote catalog
        # -----------------------------------------------------

        verification_started_at = (
            perf_counter()
        )

        persisted_rows = (
            client
            .table(
                "source_containers"
            )
            .select(
                "id,"
                "source_object_id,"
                "parent_source_object_id,"
                "name,"
                "last_seen_processing_job_id,"
                "is_active"
            )
            .eq(
                "source_id",
                source_id,
            )
            .execute()
            .data
            or []
        )

        if len(persisted_rows) != validated_count:
            raise RuntimeError(
                "Persistence verification found "
                f"{len(persisted_rows)} OneNote Containers, "
                f"expected {validated_count}."
            )

        persisted_by_identity = {
            row[
                "source_object_id"
            ]:
                row

            for row in persisted_rows
        }

        for observed in validated_containers:

            source_object_id = observed[
                "source_object_id"
            ]

            persisted = persisted_by_identity.get(
                source_object_id
            )

            if persisted is None:
                raise RuntimeError(
                    "Persisted OneNote Container is missing: "
                    f"{source_object_id}"
                )

            if (
                persisted[
                    "parent_source_object_id"
                ]
                != observed[
                    "parent_source_object_id"
                ]
            ):
                raise RuntimeError(
                    "Persisted OneNote parent identity "
                    "does not match the validated observation: "
                    f"{source_object_id}"
                )

            if (
                persisted[
                    "name"
                ]
                != observed[
                    "name"
                ]
            ):
                raise RuntimeError(
                    "Persisted OneNote name does not match "
                    "the validated observation: "
                    f"{source_object_id}"
                )

            if persisted[
                "is_active"
            ] is not True:
                raise RuntimeError(
                    "Persisted OneNote Container is inactive: "
                    f"{source_object_id}"
                )

            if (
                persisted[
                    "last_seen_processing_job_id"
                ]
                != processing_job_id
            ):
                raise RuntimeError(
                    "Persisted OneNote Container does not "
                    "reference the population Processing Job: "
                    f"{source_object_id}"
                )

        verification_seconds = (
            perf_counter()
            - verification_started_at
        )

        # -----------------------------------------------------
        # Complete Processing Job
        # -----------------------------------------------------

        processing_job_repository.complete(
            processing_job_id
        )

        total_seconds = (
            perf_counter()
            - total_started_at
        )

        print(
            f"PASS: All {validated_count} "
            "OneNote Containers verified."
        )
        print(
            "PASS: All persisted Containers are active."
        )
        print(
            "PASS: Processing Job completed."
        )
        print()

        print(
            "============================================================"
        )
        print(
            "OneNote Population Measurements"
        )
        print(
            "============================================================"
        )
        print(
            "  Containers       : "
            f"{validated_count}"
        )
        print(
            "  Payload Size     : "
            f"{format_bytes(payload_bytes)}"
        )
        print(
            "  Enumeration Time : "
            f"{format_duration(enumeration_seconds)}"
        )
        print(
            "  Validation Time  : "
            f"{format_duration(validation_seconds)}"
        )
        print(
            "  Persistence Time : "
            f"{format_duration(persistence_seconds)}"
        )
        print(
            "  Verification Time: "
            f"{format_duration(verification_seconds)}"
        )
        print(
            "  Total Time       : "
            f"{format_duration(total_seconds)}"
        )
        print()

        print(
            "INITIAL ONENOTE CONTAINER POPULATION: PASS"
        )
        print()

    except Exception as error:

        if processing_job_id is not None:

            try:

                processing_job_repository.fail(
                    processing_job_id,
                    error,
                )

            except Exception as job_error:

                print(
                    "WARNING: Unable to mark Processing "
                    "Job failed:"
                )
                print(
                    job_error
                )

        raise


if __name__ == "__main__":
    main()