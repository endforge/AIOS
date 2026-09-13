"""
Find OneNote Page ID

Purpose:
    Locates a specific OneNote page and prints its Microsoft Graph page ID.

Verifies:
    - The configured notebook can be located.
    - The configured section can be located.
    - The configured page can be located.
    - Microsoft Graph returns the current page identity.

Does NOT:
    - Modify OneNote.
    - Write to the AlphaOmega database.
    - Execute synchronization.
    - Create Knowledge Objects.
"""

from scripts.connectors.ms_graph.graph_connection import (
    graph_get,
)


NOTEBOOK_NAME = "Mimic's Tavern"
SECTION_NAME = "Lingo"
PAGE_NAME = "Blacksmith Lingo"


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
    """
    Locate the requested OneNote page.
    """

    print(
        "\nLocating OneNote test page...\n"
    )

    # ================================================================
    # Find notebook
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
        f"Notebook found: {NOTEBOOK_NAME}"
    )

    # ================================================================
    # Find section inside notebook
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

    print(
        f"Section found:  {SECTION_NAME}"
    )

    # ================================================================
    # Find page inside section
    # ================================================================

    pages = get_collection(
        "/me/onenote/sections/"
        f"{section_id}/pages"
        "?$select=id,title"
    )

    page = find_named_object(
        objects=pages,
        expected_name=PAGE_NAME,
        name_field="title",
        object_type="page",
    )

    page_id = page.get(
        "id"
    )

    if not page_id:
        raise RuntimeError(
            "Matching page is missing its Graph ID."
        )

    print(
        f"Page found:     {PAGE_NAME}"
    )

    print(
        "\nMicrosoft Graph Page ID:"
    )

    print(
        page_id
    )

    print(
        "\nPASS: OneNote page located successfully.\n"
    )


if __name__ == "__main__":
    main()