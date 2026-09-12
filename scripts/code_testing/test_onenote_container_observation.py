from scripts.connectors.ms_graph.onenote_container_enumerator import (
    OneNoteContainerEnumerator,
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
        "AlphaOmega Live OneNote Container Observation Test"
    )
    print(
        "============================================================"
    )
    print()

    enumerator = (
        OneNoteContainerEnumerator()
    )

    validator = (
        SourceContainerObservationValidator()
    )

    print(
        "Enumerating live OneNote Containers..."
    )
    print()

    observation = (
        enumerator.enumerate()
    )

    containers = (
        observation["containers"]
    )

    print(
        "PASS: OneNote enumeration completed."
    )
    print(
        f"  Containers : {len(containers)}"
    )
    print(
        f"  Complete   : "
        f"{observation['enumeration_complete']}"
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
        "PASS: Live OneNote observation "
        "satisfies Source Container validation."
    )
    print(
        f"  Validated Containers : "
        f"{len(validated)}"
    )

    print()
    print(
        "LIVE ONENOTE CONTAINER OBSERVATION TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()