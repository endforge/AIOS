from scripts.connectors.ms_graph.onedrive_container_enumerator import (
    OneDriveContainerEnumerator,
)

from scripts.sync.source_container_observation_validator import (
    SourceContainerObservationValidator,
)


def main():

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega Live OneDrive Container Observation Test"
    )
    print(
        "============================================================"
    )
    print()

    enumerator = (
        OneDriveContainerEnumerator()
    )

    validator = (
        SourceContainerObservationValidator()
    )

    print(
        "Enumerating live OneDrive Containers..."
    )
    print()

    observation = (
        enumerator.enumerate()
    )

    containers = (
        observation["containers"]
    )

    print(
        "PASS: OneDrive enumeration completed."
    )
    print(
        f"  Containers : {len(containers)}"
    )
    print(
        f"  Complete   : "
        f"{observation['enumeration_complete']}"
    )
    print(
        f"  Delta link : "
        f"{bool(observation.get('delta_link'))}"
    )

    print()
    print(
        "Validating complete observation..."
    )
    print()

    validated = (
        validator.validate(
            observation
        )
    )

    if (
        len(validated)
        != len(containers)
    ):
        raise RuntimeError(
            "Validated Container count does not "
            "match enumerated Container count."
        )

    print(
        "PASS: Live OneDrive observation "
        "satisfies Source Container validation."
    )
    print(
        f"  Validated Containers : "
        f"{len(validated)}"
    )

    print()
    print(
        "LIVE ONEDRIVE CONTAINER OBSERVATION TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()