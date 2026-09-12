from scripts.sync.source_container_reconciler import (
    SourceContainerReconciler,
)


def main():

    print()
    print(
        "============================================================"
    )
    print(
        "AlphaOmega Source Container Reconciler Test"
    )
    print(
        "============================================================"
    )
    print()

    reconciler = (
        SourceContainerReconciler()
    )

    existing_containers = [
        {
            "id": "AO-A",
            "source_object_id": "A",
            "name": "Existing",
            "parent_source_object_id": None,
            "is_active": True,
        },
        {
            "id": "AO-B",
            "source_object_id": "B",
            "name": "Old Name",
            "parent_source_object_id": "A",
            "is_active": True,
        },
        {
            "id": "AO-C",
            "source_object_id": "C",
            "name": "Inactive",
            "parent_source_object_id": "A",
            "is_active": False,
        },
        {
            "id": "AO-D",
            "source_object_id": "D",
            "name": "Will Disappear",
            "parent_source_object_id": "A",
            "is_active": True,
        },
    ]

    observed_containers = [
        {
            "source_object_id": "A",
            "name": "Existing",
            "parent_source_object_id": None,
        },
        {
            "source_object_id": "B",
            "name": "Renamed",
            "parent_source_object_id": "A",
        },
        {
            "source_object_id": "C",
            "name": "Inactive Returns",
            "parent_source_object_id": "A",
        },
        {
            "source_object_id": "E",
            "name": "Brand New",
            "parent_source_object_id": "A",
        },
    ]

    result = (
        reconciler.reconcile(
            observed_containers=(
                observed_containers
            ),
            existing_containers=(
                existing_containers
            ),
        )
    )

    if len(result["new"]) != 1:
        raise RuntimeError(
            "Expected exactly 1 NEW Container."
        )

    if (
        result["new"][0]["observed"]
        ["source_object_id"]
        != "E"
    ):
        raise RuntimeError(
            "Wrong Container classified NEW."
        )

    print(
        "PASS: NEW Container classified correctly."
    )

    if len(result["existing"]) != 2:
        raise RuntimeError(
            "Expected exactly 2 existing Containers."
        )

    existing_ids = {
        item["existing"]["source_object_id"]
        for item in result["existing"]
    }

    if existing_ids != {"A", "B"}:
        raise RuntimeError(
            "Existing Containers classified incorrectly."
        )

    print(
        "PASS: Existing Containers classified correctly."
    )

    renamed = next(
        item
        for item in result["existing"]
        if (
            item["existing"]["source_object_id"]
            == "B"
        )
    )

    if (
        renamed["existing"]["id"]
        != "AO-B"
    ):
        raise RuntimeError(
            "Existing AlphaOmega identity was not preserved."
        )

    if (
        renamed["observed"]["name"]
        != "Renamed"
    ):
        raise RuntimeError(
            "Current observed name was not preserved."
        )

    print(
        "PASS: Rename preserves Source Container identity."
    )

    if len(result["reappearing"]) != 1:
        raise RuntimeError(
            "Expected exactly 1 reappearing Container."
        )

    reappearing = (
        result["reappearing"][0]
    )

    if (
        reappearing["existing"]["source_object_id"]
        != "C"
    ):
        raise RuntimeError(
            "Wrong Container classified reappearing."
        )

    if (
        reappearing["existing"]["id"]
        != "AO-C"
    ):
        raise RuntimeError(
            "Reappearing Container lost "
            "its AlphaOmega identity."
        )

    print(
        "PASS: Reappearing Container classified correctly."
    )

    if len(result["absent"]) != 1:
        raise RuntimeError(
            "Expected exactly 1 absent Container."
        )

    if (
        result["absent"][0]["existing"]
        ["source_object_id"]
        != "D"
    ):
        raise RuntimeError(
            "Wrong Container classified absent."
        )

    print(
        "PASS: Absent active Container classified correctly."
    )

    print()
    print(
        "RECONCILIATION RESULT"
    )
    print(
        f"  NEW         : {len(result['new'])}"
    )
    print(
        f"  EXISTING    : {len(result['existing'])}"
    )
    print(
        f"  REAPPEARING : {len(result['reappearing'])}"
    )
    print(
        f"  ABSENT      : {len(result['absent'])}"
    )

    print()
    print(
        "SOURCE CONTAINER RECONCILER TEST: PASS"
    )
    print()


if __name__ == "__main__":
    main()