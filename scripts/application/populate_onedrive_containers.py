"""
Controlled initial population of the OneDrive AlphaOmega
Source Container subtree.

This Lab 8 bootstrap operation measures:

- Complete OneDrive enumeration time.
- Observation validation time.
- Selected subtree size.
- JSON persistence payload size.
- PostgreSQL persistence time.
- Database verification time.
- Total execution time.

The operation does not:

- Persist the complete OneDrive Container catalog.
- Synchronize OneDrive content.
- Create Knowledge Objects.
- Mark Source Containers inactive.
- Perform normal Source Container Refresh reconciliation.
"""

import json

from datetime import datetime, timezone
from time import perf_counter

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.connectors.ms_graph.onedrive_container_enumerator import (
    OneDriveContainerEnumerator,
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


SOURCE_NAME = "OneDrive"

ALPHAOMEGA_ROOT_ID = (
    "70EE5AA1D6A4DA1F!"
    "s9c76b7e6703145539f4f257f446477f7"
)

ALPHAOMEGA_ROOT_NAME = "AlphaOmega"


def format_duration(
    seconds,
):
    """
    Format elapsed seconds for console output.
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
    Format a byte count using binary units.
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


def select_subtree(
    containers,
    root_source_object_id,
):
    """
    Return the selected root Container and every descendant.
    """

    containers_by_id = {
        container[
            "source_object_id"
        ]:
            container

        for container in containers
    }

    root = containers_by_id.get(
        root_source_object_id
    )

    if root is None:
        raise RuntimeError(
            "Approved AlphaOmega root is not present "
            "in the validated OneDrive observation."
        )

    containers_by_parent = {}

    for container in containers:

        parent_id = container.get(
            "parent_source_object_id"
        )

        containers_by_parent.setdefault(
            parent_id,
            [],
        ).append(
            container
        )

    subtree = []

    pending = [
        root_source_object_id
    ]

    visited = set()

    while pending:

        source_object_id = (
            pending.pop()
        )

        if source_object_id in visited:
            continue

        visited.add(
            source_object_id
        )

        container = containers_by_id.get(
            source_object_id
        )

        if container is None:
            raise RuntimeError(
                "Selected subtree references a Container "
                "that is not present in the validated "
                "OneDrive observation."
            )

        subtree.append(
            container
        )

        for child in containers_by_parent.get(
            source_object_id,
            [],
        ):
            pending.append(
                child[
                    "source_object_id"
                ]
            )

    return subtree


def main():

    total_started_at = (
        perf_counter()
    )

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega OneDrive Controlled Container Population"
    )
    print(
        "============================================================"
    )
    print()

    # ---------------------------------------------------------
    # Database connection and Source resolution
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
            "Registered OneDrive Source was not found."
        )

    print(
        "PASS: Registered OneDrive Source resolved."
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
            "SAFETY STOP: OneDrive already has "
            f"{len(existing_rows)} persisted Source Containers. "
            "No database write was attempted."
        )

    print(
        "PASS: OneDrive Source Container catalog is empty."
    )
    print()

    # ---------------------------------------------------------
    # Complete OneDrive enumeration
    # ---------------------------------------------------------

    enumeration_started_at = (
        perf_counter()
    )

    enumerator = (
        OneDriveContainerEnumerator()
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
            "OneDrive enumeration is not complete."
        )

    if not observation.get(
        "delta_link"
    ):
        raise RuntimeError(
            "OneDrive enumeration did not return "
            "the required delta link."
        )

    observed_containers = observation.get(
        "containers"
    )

    if not isinstance(
        observed_containers,
        list,
    ):
        raise RuntimeError(
            "OneDrive enumeration did not return "
            "a Container list."
        )

    observed_count = len(
        observed_containers
    )

    if observed_count == 0:
        raise RuntimeError(
            "SAFETY STOP: Complete OneDrive observation "
            "returned no Containers. "
            "No database write was attempted."
        )

    print(
        "PASS: Complete OneDrive observation received."
    )
    print(
        f"  Observed Containers : {observed_count}"
    )
    print(
        "  Delta Link Present  : True"
    )
    print(
        "  Enumeration Time    : "
        f"{format_duration(enumeration_seconds)}"
    )
    print()

    # ---------------------------------------------------------
    # Complete-observation validation
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

    print(
        "PASS: Complete OneDrive observation validated."
    )
    print(
        f"  Validated Containers : {validated_count}"
    )
    print(
        "  Validation Time      : "
        f"{format_duration(validation_seconds)}"
    )
    print()

    # ---------------------------------------------------------
    # Resolve the approved AlphaOmega root
    # ---------------------------------------------------------

    root_matches = [
        container

        for container in validated_containers

        if container[
            "source_object_id"
        ] == ALPHAOMEGA_ROOT_ID
    ]

    if len(root_matches) != 1:
        raise RuntimeError(
            "SAFETY STOP: Expected exactly one Container "
            "with the approved AlphaOmega root identity. "
            "No database write was attempted."
        )

    root = root_matches[0]

    if root[
        "name"
    ] != ALPHAOMEGA_ROOT_NAME:
        raise RuntimeError(
            "SAFETY STOP: Approved AlphaOmega root identity "
            "no longer has the expected name. "
            f"Expected '{ALPHAOMEGA_ROOT_NAME}', "
            f"received '{root['name']}'. "
            "No database write was attempted."
        )

    print(
        "PASS: Approved AlphaOmega root resolved."
    )
    print(
        f"  Root ID   : {ALPHAOMEGA_ROOT_ID}"
    )
    print(
        f"  Root Name : {root['name']}"
    )
    print()

    # ---------------------------------------------------------
    # Select only AlphaOmega and its descendants
    # ---------------------------------------------------------

    selection_started_at = (
        perf_counter()
    )

    subtree = (
        select_subtree(
            validated_containers,
            ALPHAOMEGA_ROOT_ID,
        )
    )

    selection_seconds = (
        perf_counter()
        - selection_started_at
    )

    subtree_count = len(
        subtree
    )

    if subtree_count == 0:
        raise RuntimeError(
            "SAFETY STOP: AlphaOmega subtree is empty. "
            "No database write was attempted."
        )

    if subtree[
        0
    ][
        "source_object_id"
    ] != ALPHAOMEGA_ROOT_ID:
        raise RuntimeError(
            "SAFETY STOP: Selected subtree does not begin "
            "with the approved AlphaOmega root. "
            "No database write was attempted."
        )

    print(
        "PASS: AlphaOmega subtree selected."
    )
    print(
        f"  Selected Containers : {subtree_count}"
    )
    print(
        "  Selection Time      : "
        f"{format_duration(selection_seconds)}"
    )
    print()

    # ---------------------------------------------------------
    # Measure exact persistence payload
    # ---------------------------------------------------------

    payload_bytes = len(
        json.dumps(
            subtree,
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
        f"  Container Count : {subtree_count}"
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
        "Beginning controlled AlphaOmega persistence."
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

                    "root_source_object_id":
                        ALPHAOMEGA_ROOT_ID,

                    "root_name":
                        ALPHAOMEGA_ROOT_NAME,

                    "observed_container_count":
                        validated_count,

                    "selected_container_count":
                        subtree_count,

                    "payload_bytes":
                        payload_bytes,

                    "enumeration_seconds":
                        enumeration_seconds,

                    "validation_seconds":
                        validation_seconds,

                    "selection_seconds":
                        selection_seconds,
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
        # Atomic subtree persistence
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
                        subtree,
                },
            )
            .execute()
        )

        persistence_seconds = (
            perf_counter()
            - persistence_started_at
        )

        if response.data != subtree_count:
            raise RuntimeError(
                "Persistence RPC did not report the selected "
                "number of Containers. "
                f"Expected {subtree_count}, "
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
        # Verify the persisted subtree
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

        if len(persisted_rows) != subtree_count:
            raise RuntimeError(
                "Persistence verification found "
                f"{len(persisted_rows)} OneDrive Containers, "
                f"expected {subtree_count} selected Containers."
            )

        persisted_by_identity = {
            row[
                "source_object_id"
            ]:
                row

            for row in persisted_rows
        }

        for observed in subtree:

            source_object_id = observed[
                "source_object_id"
            ]

            persisted = persisted_by_identity.get(
                source_object_id
            )

            if persisted is None:
                raise RuntimeError(
                    "Persisted AlphaOmega Container is missing: "
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
                    "Persisted AlphaOmega parent identity "
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
                    "Persisted AlphaOmega name does not match "
                    "the validated observation: "
                    f"{source_object_id}"
                )

            if persisted[
                "is_active"
            ] is not True:
                raise RuntimeError(
                    "Persisted AlphaOmega Container is inactive: "
                    f"{source_object_id}"
                )

            if (
                persisted[
                    "last_seen_processing_job_id"
                ]
                != processing_job_id
            ):
                raise RuntimeError(
                    "Persisted AlphaOmega Container does not "
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
            f"PASS: All {subtree_count} "
            "AlphaOmega Containers verified."
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
            "OneDrive AlphaOmega Population Measurements"
        )
        print(
            "============================================================"
        )
        print(
            "  OneDrive Observed : "
            f"{validated_count}"
        )
        print(
            "  AlphaOmega Subtree: "
            f"{subtree_count}"
        )
        print(
            "  Payload Size      : "
            f"{format_bytes(payload_bytes)}"
        )
        print(
            "  Enumeration Time  : "
            f"{format_duration(enumeration_seconds)}"
        )
        print(
            "  Validation Time   : "
            f"{format_duration(validation_seconds)}"
        )
        print(
            "  Selection Time    : "
            f"{format_duration(selection_seconds)}"
        )
        print(
            "  Persistence Time  : "
            f"{format_duration(persistence_seconds)}"
        )
        print(
            "  Verification Time : "
            f"{format_duration(verification_seconds)}"
        )
        print(
            "  Total Time        : "
            f"{format_duration(total_seconds)}"
        )
        print()

        print(
            "INITIAL ONEDRIVE ALPHAOMEGA "
            "CONTAINER POPULATION: PASS"
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