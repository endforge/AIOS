"""
OneNote Change Diagnostic

Purpose:
    Diagnoses whether the parent OneNote Section provides a reliable
    modification signal when page body content changes.

Verifies:
    - Live OneNote page metadata can be inspected.
    - Parent Section modification metadata can be inspected.
    - Page and Section modification signals can be compared for diagnostic
      purposes.

Does NOT:
    - Modify OneNote.
    - Write to AlphaOmega.
    - Execute synchronization.
    - Change OneNote timestamp handling.
"""

import json

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)


# ============================================================================
# Controlled Targets
# ============================================================================


ONENOTE_SECTION_NAME = "Lingo"

ONENOTE_SECTION_ID = (
    "0-70EE5AA1D6A4DA1F!80852"
)

ONENOTE_PAGE_NAME = (
    "Blacksmith Lingo"
)

ONENOTE_PAGE_ID = (
    "0-c95a5657f28b44aca521bda1767279d9!"
    "1-70EE5AA1D6A4DA1F!80852"
)


# ============================================================================
# Helpers
# ============================================================================


def print_field(
    raw_object,
    field_name,
):
    exists = field_name in raw_object
    value = raw_object.get(field_name)

    print(
        f"{field_name:<24}: {value!r}"
    )

    print(
        f"{'':24}  present={exists}"
    )


# ============================================================================
# Main
# ============================================================================


def main():

    print()

    print(
        "============================================================"
    )

    print(
        "AlphaOmega OneNote Section Change Diagnostic"
    )

    print(
        "============================================================"
    )

    print()

    print("READ-ONLY TEST")
    print("No Discovery")
    print("No Extraction")
    print("No Load")
    print("No Processing Job")
    print("No database writes")

    print()

    connector = GraphConnector()

    # ========================================================================
    # Retrieve parent Section
    # ========================================================================

    print(
        "Retrieving Lingo Section metadata..."
    )

    section = connector._get_json(
        "/me/onenote/sections/"
        f"{ONENOTE_SECTION_ID}"
    )

    if not isinstance(
        section,
        dict,
    ):
        raise RuntimeError(
            "OneNote Section response was not "
            "a JSON object."
        )

    if (
        section.get("id")
        != ONENOTE_SECTION_ID
    ):
        raise RuntimeError(
            "Returned Section ID does not match "
            "the controlled Lingo Section."
        )

    if (
        section.get("displayName")
        != ONENOTE_SECTION_NAME
    ):
        raise RuntimeError(
            "Returned Section name does not match "
            "the controlled Lingo Section."
        )

    print(
        "PASS: Correct Lingo Section retrieved."
    )

    # ========================================================================
    # Retrieve controlled Page
    # ========================================================================

    print()

    print(
        "Retrieving Blacksmith Lingo page metadata..."
    )

    page = connector._get_json(
        "/me/onenote/pages/"
        f"{ONENOTE_PAGE_ID}"
    )

    if not isinstance(
        page,
        dict,
    ):
        raise RuntimeError(
            "OneNote page response was not "
            "a JSON object."
        )

    if (
        page.get("id")
        != ONENOTE_PAGE_ID
    ):
        raise RuntimeError(
            "Returned page ID does not match "
            "Blacksmith Lingo."
        )

    if (
        page.get("title")
        != ONENOTE_PAGE_NAME
    ):
        raise RuntimeError(
            "Returned page title does not match "
            "Blacksmith Lingo."
        )

    print(
        "PASS: Correct Blacksmith Lingo page retrieved."
    )

    # ========================================================================
    # Section fields
    # ========================================================================

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        "SECTION TIMESTAMP FIELDS"
    )

    print(
        "------------------------------------------------------------"
    )

    print()

    for field_name in (
        "createdDateTime",
        "lastModifiedDateTime",
        "createdTime",
        "lastModifiedTime",
    ):
        print_field(
            section,
            field_name,
        )

        print()

    # ========================================================================
    # Page fields
    # ========================================================================

    print(
        "------------------------------------------------------------"
    )

    print(
        "PAGE TIMESTAMP FIELDS"
    )

    print(
        "------------------------------------------------------------"
    )

    print()

    for field_name in (
        "createdDateTime",
        "lastModifiedDateTime",
        "createdTime",
        "lastModifiedTime",
    ):
        print_field(
            page,
            field_name,
        )

        print()

    # ========================================================================
    # Section modification identity
    # ========================================================================

    print(
        "------------------------------------------------------------"
    )

    print(
        "SECTION MODIFICATION INFORMATION"
    )

    print(
        "------------------------------------------------------------"
    )

    print()

    for field_name in (
        "lastModifiedBy",
        "createdBy",
    ):
        print_field(
            section,
            field_name,
        )

        print()

    # ========================================================================
    # All Section keys
    # ========================================================================

    print(
        "------------------------------------------------------------"
    )

    print(
        "ALL RETURNED SECTION KEYS"
    )

    print(
        "------------------------------------------------------------"
    )

    print()

    for key in sorted(
        section.keys()
    ):
        print(key)

    # ========================================================================
    # Raw Section response
    # ========================================================================

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        "RAW SECTION METADATA"
    )

    print(
        "------------------------------------------------------------"
    )

    print()

    print(
        json.dumps(
            section,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    # ========================================================================
    # Summary
    # ========================================================================

    print()

    print(
        "============================================================"
    )

    print(
        "DIAGNOSTIC SUMMARY"
    )

    print(
        "============================================================"
    )

    print()

    print(
        f"Section ID                 : "
        f"{section.get('id')}"
    )

    print(
        f"Section createdDateTime    : "
        f"{section.get('createdDateTime')}"
    )

    print(
        f"Section lastModifiedDateTime: "
        f"{section.get('lastModifiedDateTime')}"
    )

    print()

    print(
        f"Page ID                    : "
        f"{page.get('id')}"
    )

    print(
        f"Page createdDateTime       : "
        f"{page.get('createdDateTime')}"
    )

    print(
        f"Page lastModifiedDateTime  : "
        f"{page.get('lastModifiedDateTime')}"
    )

    print()

    print(
        "SECTION CHANGE DIAGNOSTIC COMPLETE."
    )

    print()


if __name__ == "__main__":
    main()