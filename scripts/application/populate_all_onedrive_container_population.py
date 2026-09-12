"""
Controlled full OneDrive Source Container population test.

This script:

- Enumerates the complete current OneDrive folder structure.
- Validates the complete observation.
- Measures the complete persistence payload.
- Applies safety limits before writing.
- Upserts every observed OneDrive Container atomically.
- Retrieves the complete catalog using paginated repository access.
- Verifies exact identities, hierarchy, names, active state, and
  Processing Job attribution.

This is a persistent database operation.

It does not synchronize file content.
It does not deactivate Containers absent from the observation.
It does not modify OneNote Source Containers.
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
from scripts.database.source_container_repository import (
    SourceContainerRepository,
)
from scripts.database.source_repository import (
    SourceRepository,
)
from scripts.sync.source_container_observation_validator import (
    SourceContainerObservationValidator,
)


SOURCE_NAME = "OneDrive"

MAX_CONTAINER_COUNT = 10000
MAX_PAYLOAD_BYTES = 5 * 1024 * 1024


class ExistingDatabaseConnection:
    """
    Provide an existing authenticated database client to repositories
    that accept a DatabaseConnection-style dependency.
    """

    def __init__(self, client):
        self._client = client

    def connect(self):
        return self._client


def format_duration(seconds):
    """
    Return a readable elapsed-time value.
    """

    if seconds < 60:
        return f"{seconds:.2f} seconds"

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    return (
        f"{minutes} minutes "
        f"{remaining_seconds:.2f} seconds"
    )


def format_bytes(byte_count):
    """
    Return a readable payload-size value.
    """

    if byte_count < 1024:
        return f"{byte_count} bytes"

    kibibytes = byte_count / 1024

    if kibibytes < 1024:
        return f"{kibibytes:.2f} KiB"

    mebibytes = kibibytes / 1024

    return f"{mebibytes:.2f} MiB"


def main():

    total_started_at = perf_counter()

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega Full OneDrive Container Population Test"
    )
    print(
        "============================================================"
    )
    print()

    # ---------------------------------------------------------
    # Database connection and registered Source
    # ---------------------------------------------------------

    credential_provider = (
        LocalCredentialProvider()
    )

    database_connection = (
        DatabaseConnection(
            credential_provider
        )
    )

    client = database_connection.connect()

    source_repository = (
        SourceRepository(client)
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

    source_container_repository = (
        SourceContainerRepository(
            ExistingDatabaseConnection(client)
        )
    )

    # ---------------------------------------------------------
    # Read the existing OneDrive catalog using pagination
    # ---------------------------------------------------------

    existing_rows = (
        source_container_repository.find_by_source(
            source_id
        )
    )

    existing_by_identity = {
        row["source_object_id"]: row
        for row in existing_rows
    }

    print(
        "PASS: Existing OneDrive catalog retrieved."
    )
    print(
        f"  Existing Containers : {len(existing_rows)}"
    )
    print()

    # ---------------------------------------------------------
    # Complete OneDrive enumeration
    # ---------------------------------------------------------

    enumeration_started_at = perf_counter()

    enumerator = (
        OneDriveContainerEnumerator()
    )

    observation = enumerator.enumerate()

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

    if not observation.get("delta_link"):
        raise RuntimeError(
            "OneDrive enumeration did not return a delta link."
        )

    observed_count = len(
        observation.get(
            "containers",
            [],
        )
    )

    if observed_count == 0:
        raise RuntimeError(
            "SAFETY STOP: Complete OneDrive observation "
            "contained no Containers."
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
    # Validate complete observation
    # ---------------------------------------------------------

    validation_started_at = perf_counter()

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
            "Validated Container count does not match "
            "the observed Container count."
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
    # Compare current observation with existing catalog
    # ---------------------------------------------------------

    observed_by_identity = {
        container["source_object_id"]:
            container
        for container in validated_containers
    }

    stale_existing_identities = (
        set(existing_by_identity)
        - set(observed_by_identity)
    )

    if stale_existing_identities:
        raise RuntimeError(
            "SAFETY STOP: The existing OneDrive catalog "
            f"contains {len(stale_existing_identities)} "
            "Containers not present in the current observation. "
            "This population test does not deactivate absent "
            "Containers."
        )

    new_container_count = len(
        set(observed_by_identity)
        - set(existing_by_identity)
    )

    existing_container_count = len(
        set(observed_by_identity)
        & set(existing_by_identity)
    )

    print(
        "PASS: Existing catalog is compatible with "
        "the complete observation."
    )
    print(
        f"  Existing Matches : {existing_container_count}"
    )
    print(
        f"  New Containers   : {new_container_count}"
    )
    print()

    # ---------------------------------------------------------
    # Prepare and measure persistence payload
    # ---------------------------------------------------------

    payload_json = json.dumps(
        validated_containers,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    payload_size_bytes = len(
        payload_json.encode("utf-8")
    )

    print(
        "PASS: Full persistence payload prepared."
    )
    print(
        f"  Container Count : {validated_count}"
    )
    print(
        "  Payload Size    : "
        f"{format_bytes(payload_size_bytes)}"
    )
    print()

    # ---------------------------------------------------------
    # Pre-write safety limits
    # ---------------------------------------------------------

    if validated_count > MAX_CONTAINER_COUNT:
        raise RuntimeError(
            "SAFETY STOP: Validated OneDrive Container "
            f"count is {validated_count}, exceeding the "
            f"safety limit of {MAX_CONTAINER_COUNT}. "
            "No database write was attempted."
        )

    if payload_size_bytes > MAX_PAYLOAD_BYTES:
        raise RuntimeError(
            "SAFETY STOP: OneDrive persistence payload "
            f"is {format_bytes(payload_size_bytes)}, exceeding "
            f"the safety limit of "
            f"{format_bytes(MAX_PAYLOAD_BYTES)}. "
            "No database write was attempted."
        )

    print(
        "All pre-write safety checks passed."
    )
    print(
        "Beginning controlled full OneDrive persistence."
    )
    print()

    # ---------------------------------------------------------
    # Processing Job and atomic persistence
    # ---------------------------------------------------------

    processing_job_repository = (
        ProcessingJobRepository(client)
    )

    processing_job_id = None

    try:

        processing_job_id = (
            processing_job_repository.create(
                process_type=(
                    "source_container_refresh"
                ),
                pipeline_version=(
                    "lab8-full-onedrive-test"
                ),
                metadata={
                    "operation":
                        "full_onedrive_population_test",

                    "source":
                        SOURCE_NAME,

                    "observed_container_count":
                        observed_count,

                    "existing_container_count":
                        existing_container_count,

                    "new_container_count":
                        new_container_count,

                    "payload_size_bytes":
                        payload_size_bytes,
                },
            )
        )

        print(
            "PASS: Processing Job created."
        )
        print(
            "  Processing Job ID : "
            f"{processing_job_id}"
        )
        print()

        observed_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        persistence_started_at = perf_counter()

        response = (
            client.rpc(
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
            ).execute()
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
        # Verify the complete persisted OneDrive catalog
        # -----------------------------------------------------

        verification_started_at = perf_counter()

        persisted_rows = (
            source_container_repository.find_by_source(
                source_id
            )
        )

        persisted_by_identity = {
            row["source_object_id"]:
                row
            for row in persisted_rows
        }

        if len(persisted_rows) != validated_count:
            raise RuntimeError(
                "Full catalog verification failed. "
                f"Expected {validated_count} persisted "
                "OneDrive Containers, found "
                f"{len(persisted_rows)}."
            )

        missing_identities = (
            set(observed_by_identity)
            - set(persisted_by_identity)
        )

        unexpected_identities = (
            set(persisted_by_identity)
            - set(observed_by_identity)
        )

        if missing_identities:
            raise RuntimeError(
                "Full catalog verification failed. "
                f"{len(missing_identities)} observed "
                "Containers are missing from the database."
            )

        if unexpected_identities:
            raise RuntimeError(
                "Full catalog verification failed. "
                f"{len(unexpected_identities)} unexpected "
                "OneDrive Containers are present."
            )

        hierarchy_mismatches = []
        name_mismatches = []
        inactive_containers = []
        job_mismatches = []

        for source_object_id, observed in (
            observed_by_identity.items()
        ):

            persisted = persisted_by_identity[
                source_object_id
            ]

            if (
                persisted.get(
                    "parent_source_object_id"
                )
                != observed.get(
                    "parent_source_object_id"
                )
            ):
                hierarchy_mismatches.append(
                    source_object_id
                )

            if (
                persisted.get("name")
                != observed.get("name")
            ):
                name_mismatches.append(
                    source_object_id
                )

            if persisted.get("is_active") is not True:
                inactive_containers.append(
                    source_object_id
                )

            if (
                str(
                    persisted.get(
                        "last_seen_processing_job_id"
                    )
                )
                != str(processing_job_id)
            ):
                job_mismatches.append(
                    source_object_id
                )

        if hierarchy_mismatches:
            raise RuntimeError(
                "Full catalog verification failed. "
                f"{len(hierarchy_mismatches)} Containers "
                "have incorrect parent identities."
            )

        if name_mismatches:
            raise RuntimeError(
                "Full catalog verification failed. "
                f"{len(name_mismatches)} Containers "
                "have incorrect names."
            )

        if inactive_containers:
            raise RuntimeError(
                "Full catalog verification failed. "
                f"{len(inactive_containers)} Containers "
                "are inactive."
            )

        if job_mismatches:
            raise RuntimeError(
                "Full catalog verification failed. "
                f"{len(job_mismatches)} Containers "
                "have incorrect Processing Job attribution."
            )

        verification_seconds = (
            perf_counter()
            - verification_started_at
        )

        processing_job_repository.complete(
            processing_job_id
        )

        total_seconds = (
            perf_counter()
            - total_started_at
        )

        print(
            f"PASS: All {validated_count} OneDrive "
            "Containers verified."
        )
        print(
            "PASS: All persisted Containers are active."
        )
        print(
            "PASS: All Containers reference the current "
            "Processing Job."
        )
        print(
            "PASS: Processing Job completed."
        )
        print()

        print(
            "============================================================"
        )
        print(
            "Full OneDrive Population Measurements"
        )
        print(
            "============================================================"
        )
        print(
            f"  Containers       : {validated_count}"
        )
        print(
            f"  Previously Saved : {existing_container_count}"
        )
        print(
            f"  Newly Inserted   : {new_container_count}"
        )
        print(
            "  Payload Size     : "
            f"{format_bytes(payload_size_bytes)}"
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
            "FULL ONEDRIVE CONTAINER POPULATION TEST: PASS"
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