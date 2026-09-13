"""
AlphaOmega Source Container Reconciler

Purpose:
    Compares a validated complete Source Container observation with persisted
    catalog state.

Responsibilities:
    - Identify newly observed Source Containers.
    - Identify existing Source Containers.
    - Identify previously inactive containers that have reappeared.
    - Identify persisted containers absent from the complete observation.
    - Produce reconciliation results required for atomic persistence.

Does NOT:
    - Enumerate Sources of Truth.
    - Validate observation completeness.
    - Persist reconciliation results.
    - Deactivate Source Containers itself.
    - Synchronize content.
"""

class SourceContainerReconciler:
    """
    Compare a validated complete Source Container observation
    with AlphaOmega's existing Source Container Catalog.

    This component determines required catalog changes.

    It does not:
        - enumerate a Source of Truth
        - validate the observation
        - access the database
        - write catalog changes
        - create Processing Jobs
    """

    def reconcile(
        self,
        *,
        observed_containers,
        existing_containers,
    ):

        if not isinstance(
            observed_containers,
            list,
        ):
            raise ValueError(
                "observed_containers must be a list"
            )

        if not isinstance(
            existing_containers,
            list,
        ):
            raise ValueError(
                "existing_containers must be a list"
            )

        existing_by_identity = {}

        for existing in existing_containers:

            source_object_id = (
                existing.get(
                    "source_object_id"
                )
            )

            if not source_object_id:
                raise ValueError(
                    "Existing Source Container is missing "
                    "source_object_id"
                )

            if (
                source_object_id
                in existing_by_identity
            ):
                raise ValueError(
                    "Duplicate existing Source Container "
                    f"identity: {source_object_id}"
                )

            existing_by_identity[
                source_object_id
            ] = existing

        observed_ids = set()

        new = []
        existing = []
        reappearing = []
        absent = []

        for observed in observed_containers:

            source_object_id = (
                observed.get(
                    "source_object_id"
                )
            )

            if not source_object_id:
                raise ValueError(
                    "Observed Source Container is missing "
                    "source_object_id"
                )

            if source_object_id in observed_ids:
                raise ValueError(
                    "Duplicate observed Source Container "
                    f"identity: {source_object_id}"
                )

            observed_ids.add(
                source_object_id
            )

            saved = (
                existing_by_identity.get(
                    source_object_id
                )
            )

            if saved is None:

                new.append(
                    {
                        "observed":
                            observed,
                    }
                )

                continue

            if (
                saved.get("is_active")
                is False
            ):

                reappearing.append(
                    {
                        "existing":
                            saved,

                        "observed":
                            observed,
                    }
                )

                continue

            existing.append(
                {
                    "existing":
                        saved,

                    "observed":
                        observed,
                }
            )

        for saved in existing_containers:

            source_object_id = (
                saved["source_object_id"]
            )

            if (
                source_object_id
                not in observed_ids
                and saved.get("is_active") is True
            ):

                absent.append(
                    {
                        "existing":
                            saved,
                    }
                )

        return {
            "new":
                new,

            "existing":
                existing,

            "reappearing":
                reappearing,

            "absent":
                absent,
        }