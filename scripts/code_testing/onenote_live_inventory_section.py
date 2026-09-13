"""
OneNote Live Section Inventory

Purpose:
    Performs a live read-only inventory of a selected OneNote section through
    Microsoft Graph.

Verifies:
    - The configured OneNote hierarchy can be queried through Microsoft Graph.
    - Pages within the selected section can be identified.
    - Live source inventory can be inspected without database persistence.

Does NOT:
    - Modify OneNote.
    - Write to the AlphaOmega database.
    - Execute the synchronization pipeline.
    - Create Knowledge Objects.
"""

from scripts.connectors.ms_graph.graph_connection import (
    graph_get,
)


NOTEBOOK_NAME = "Mimic's Tavern"
SECTION_NAME = "House Rules"


def get_collection(endpoint):
    """
    Retrieve a complete Microsoft Graph collection,
    following @odata.nextLink when necessary.
    """

    objects = []
    next_endpoint = endpoint

    while next_endpoint:

        response = graph_get(
            next_endpoint
        )

        data = response.json()

        page_objects = data.get(
            "value"
        )

        if page_objects is None:
            raise RuntimeError(
                "Microsoft Graph response did not contain "
                "the expected 'value' collection."
            )

        objects.extend(
            page_objects
        )

        next_endpoint = data.get(
            "@odata.nextLink"
        )

    return objects


def find_named_object(
    objects,
    expected_name,
    name_field,
    object_type,
):
    """
    Find exactly one object by case-insensitive name.
    """

    matches = []

    for item in objects:

        actual_name = item.get(
            name_field
        )

        if (
            actual_name
            and actual_name.strip().casefold()
            == expected_name.casefold()
        ):
            matches.append(
                item
            )

    if not matches:
        raise RuntimeError(
            f"{object_type} not found: "
            f"'{expected_name}'."
        )

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple {object_type} objects found "
            f"with the name '{expected_name}'."
        )

    return matches[0]


def main():

    print()

    print(
        "============================================================"
    )

    print(
        "AlphaOmega Live OneNote Section Inventory"
    )

    print(
        "============================================================"
    )

    print()

    print(
        f"Notebook : {NOTEBOOK_NAME}"
    )

    print(
        f"Section  : {SECTION_NAME}"
    )

    print()

    print(
        "READ ONLY: No AlphaOmega or OneNote writes will occur."
    )

    print()

    # ================================================================
    # Notebook
    # ================================================================

    notebooks = get_collection(
        "/me/onenote/notebooks"
    )

    notebook = find_named_object(
        objects=notebooks,
        expected_name=NOTEBOOK_NAME,
        name_field="displayName",
        object_type="notebook",
    )

    notebook_id = notebook.get(
        "id"
    )

    if not notebook_id:
        raise RuntimeError(
            "Matching notebook is missing its Graph ID."
        )

    print(
        "PASS: Notebook located."
    )

    print(
        f"  Name : {notebook.get('displayName')}"
    )

    print(
        f"  ID   : {notebook_id}"
    )

    print()

    # ================================================================
    # Section
    # ================================================================

    sections = get_collection(
        "/me/onenote/notebooks/"
        f"{notebook_id}/sections"
    )

    section = find_named_object(
        objects=sections,
        expected_name=SECTION_NAME,
        name_field="displayName",
        object_type="section",
    )

    section_id = section.get(
        "id"
    )

    if not section_id:
        raise RuntimeError(
            "Matching section is missing its Graph ID."
        )

    # Retrieve the Section directly so the timestamp is current.

    section_response = graph_get(
        "/me/onenote/sections/"
        f"{section_id}"
    )

    live_section = (
        section_response.json()
    )

    if not isinstance(
        live_section,
        dict,
    ):
        raise RuntimeError(
            "Unexpected OneNote Section response."
        )

    if (
        live_section.get("id")
        != section_id
    ):
        raise RuntimeError(
            "OneNote Section identity mismatch."
        )

    section_modified_at = (
        live_section.get(
            "lastModifiedDateTime"
        )
    )

    if not section_modified_at:
        raise RuntimeError(
            "OneNote Section is missing "
            "lastModifiedDateTime."
        )

    print(
        "PASS: Section located."
    )

    print(
        f"  Name          : "
        f"{live_section.get('displayName')}"
    )

    print(
        f"  ID            : "
        f"{section_id}"
    )

    print(
        f"  Last modified : "
        f"{section_modified_at}"
    )

    print()

    # ================================================================
    # Pages
    # ================================================================

    pages = get_collection(
        "/me/onenote/sections/"
        f"{section_id}/pages"
        "?$select=id,title,lastModifiedDateTime"
    )

    if not pages:
        raise RuntimeError(
            "Target OneNote Section contains no pages."
        )

    # Deterministic display order.
    pages = sorted(
        pages,
        key=lambda item: (
            item.get("title")
            or ""
        ).casefold(),
    )

    print(
        "PASS: Section page enumeration completed."
    )

    print(
        f"  Pages retrieved : {len(pages)}"
    )

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        "PAGE INVENTORY"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, page in enumerate(
        pages,
        start=1,
    ):

        page_id = page.get(
            "id"
        )

        title = page.get(
            "title"
        )

        page_modified_at = (
            page.get(
                "lastModifiedDateTime"
            )
        )

        if not page_id:
            raise RuntimeError(
                f"Page {index} is missing its Graph ID."
            )

        if not title:
            raise RuntimeError(
                f"Page {index} is missing its title."
            )

        print()

        print(
            f"[{index}] {title}"
        )

        print(
            f"    Page ID          : {page_id}"
        )

        print(
            f"    Page modified    : {page_modified_at}"
        )

        print(
            f"    Section modified : {section_modified_at}"
        )

    print()

    print(
        "============================================================"
    )

    print(
        "INVENTORY SUMMARY"
    )

    print(
        "============================================================"
    )

    print()

    print(
        f"Notebook       : {NOTEBOOK_NAME}"
    )

    print(
        f"Section        : {SECTION_NAME}"
    )

    print(
        f"Section ID     : {section_id}"
    )

    print(
        f"Section modified: {section_modified_at}"
    )

    print(
        f"Pages          : {len(pages)}"
    )

    print()

    print(
        "LIVE ONENOTE SECTION INVENTORY PASSED."
    )

    print()


if __name__ == "__main__":
    main()