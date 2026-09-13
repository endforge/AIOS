"""
OneNote Page Hierarchy Diagnostic

Purpose:
    Diagnoses raw Microsoft Graph OneNote page hierarchy information.

Verifies:
    - A target notebook can be located.
    - A target Section can be located.
    - Raw page hierarchy information can be retrieved.
    - Parent and child page information can be inspected for known targets.

Does NOT:
    - Modify OneNote.
    - Translate OneNote hierarchy into canonical records.
    - Write to AlphaOmega.
    - Execute synchronization.
"""

from scripts.connectors.ms_graph.graph_connector import GraphConnector


NOTEBOOK_NAME = "Mimic's Tavern"
SECTION_NAME = "Homebrew"

TARGET_PAGE_NAMES = {
    "Selune Armor",
    "Armor",
}


# ============================================================================
# Helpers
# ============================================================================

def find_notebook(
    connector,
):
    """
    Find the exact OneNote notebook.
    """

    notebooks = connector._get_collection(
        "/me/onenote/notebooks"
    )

    matches = [
        notebook
        for notebook in notebooks
        if notebook.get("displayName")
        == NOTEBOOK_NAME
    ]

    if not matches:

        raise RuntimeError(
            f"Notebook '{NOTEBOOK_NAME}' "
            "was not found."
        )

    if len(matches) > 1:

        raise RuntimeError(
            f"Multiple notebooks named "
            f"'{NOTEBOOK_NAME}' were found."
        )

    return matches[0]


def find_section(
    connector,
    notebook,
):
    """
    Find the exact Homebrew section inside the selected notebook.
    """

    notebook_id = notebook.get("id")

    if not notebook_id:

        raise RuntimeError(
            "Notebook is missing its ID."
        )

    sections = connector._get_collection(
        f"/me/onenote/notebooks/"
        f"{notebook_id}/sections"
    )

    matches = [
        section
        for section in sections
        if section.get("displayName")
        == SECTION_NAME
    ]

    if not matches:

        raise RuntimeError(
            f"Section '{SECTION_NAME}' "
            f"was not found in notebook "
            f"'{NOTEBOOK_NAME}'."
        )

    if len(matches) > 1:

        raise RuntimeError(
            f"Multiple sections named "
            f"'{SECTION_NAME}' were found "
            f"in notebook '{NOTEBOOK_NAME}'."
        )

    return matches[0]


def get_pages(
    connector,
    section,
):
    """
    Retrieve all pages exactly as Graph returns them with page-level
    information enabled.
    """

    section_id = section.get("id")

    if not section_id:

        raise RuntimeError(
            "Section is missing its ID."
        )

    endpoint = (
        f"/me/onenote/sections/"
        f"{section_id}/pages"
        "?$top=100"
        "&pagelevel=true"
    )

    return connector._get_collection(
        endpoint
    )


# ============================================================================
# Reporting
# ============================================================================

def print_page(
    index,
    page,
):
    """
    Print one raw Graph page hierarchy record.
    """

    title = page.get("title")

    if (
        title is None
        or not str(title).strip()
    ):
        title = "Untitled"

    marker = ""

    if title in TARGET_PAGE_NAMES:
        marker = "   <===== TARGET"

    print(
        f"{index:>4} | "
        f"level={str(page.get('level')):<4} | "
        f"order={str(page.get('order')):<8} | "
        f"{title}"
        f"{marker}"
    )

    if title in TARGET_PAGE_NAMES:

        print(
            f"       ID: {page.get('id')}"
        )

        print(
            f"       parentSection.id: "
            f"{(page.get('parentSection') or {}).get('id')}"
        )


def print_target_details(
    pages,
):
    """
    Print complete raw Graph data for the two pages under investigation.
    """

    print()
    print("=" * 100)
    print("TARGET PAGE RAW GRAPH DATA")
    print("=" * 100)

    found = set()

    for page in pages:

        title = page.get("title")

        if title not in TARGET_PAGE_NAMES:
            continue

        found.add(title)

        print()
        print("-" * 100)
        print(f"PAGE: {title}")
        print("-" * 100)

        for key, value in page.items():

            print(
                f"{key}: {value}"
            )

    missing = (
        TARGET_PAGE_NAMES
        - found
    )

    if missing:

        print()
        print(
            "WARNING: These target pages "
            "were not found:"
        )

        for title in sorted(missing):

            print(
                f"  {title}"
            )


# ============================================================================
# Main
# ============================================================================

def main():

    print()
    print("=" * 100)
    print("ONENOTE PAGE HIERARCHY DIAGNOSTIC")
    print("=" * 100)

    print()
    print(
        f"Notebook : {NOTEBOOK_NAME}"
    )

    print(
        f"Section  : {SECTION_NAME}"
    )

    connector = GraphConnector()

    # ------------------------------------------------------------------------
    # Notebook
    # ------------------------------------------------------------------------

    print()
    print("Finding notebook...")

    notebook = find_notebook(
        connector
    )

    print(
        f"Found notebook: "
        f"{notebook.get('displayName')}"
    )

    print(
        f"Notebook ID   : "
        f"{notebook.get('id')}"
    )

    # ------------------------------------------------------------------------
    # Section
    # ------------------------------------------------------------------------

    print()
    print("Finding section...")

    section = find_section(
        connector,
        notebook,
    )

    print(
        f"Found section : "
        f"{section.get('displayName')}"
    )

    print(
        f"Section ID    : "
        f"{section.get('id')}"
    )

    # ------------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------------

    print()
    print(
        "Retrieving raw pages with "
        "pagelevel=true..."
    )

    pages = get_pages(
        connector,
        section,
    )

    print(
        f"Pages retrieved: "
        f"{len(pages)}"
    )

    # ------------------------------------------------------------------------
    # Exact Graph sequence
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("EXACT PAGE SEQUENCE RETURNED BY MICROSOFT GRAPH")
    print("=" * 100)

    print()
    print(
        " IDX | LEVEL      | ORDER          | TITLE"
    )

    print(
        "-" * 100
    )

    for index, page in enumerate(
        pages,
        start=1,
    ):

        print_page(
            index,
            page,
        )

    # ------------------------------------------------------------------------
    # Target neighborhood
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("TARGET PAGE NEIGHBORHOOD")
    print("=" * 100)

    target_indexes = []

    for index, page in enumerate(
        pages
    ):

        if (
            page.get("title")
            in TARGET_PAGE_NAMES
        ):

            target_indexes.append(
                index
            )

    neighborhood_indexes = set()

    for index in target_indexes:

        start = max(
            0,
            index - 5,
        )

        end = min(
            len(pages),
            index + 6,
        )

        neighborhood_indexes.update(
            range(
                start,
                end,
            )
        )

    if neighborhood_indexes:

        print()
        print(
            " IDX | LEVEL      | ORDER          | TITLE"
        )

        print(
            "-" * 100
        )

        for index in sorted(
            neighborhood_indexes
        ):

            print_page(
                index + 1,
                pages[index],
            )

    else:

        print()
        print(
            "Neither target page was found."
        )

    # ------------------------------------------------------------------------
    # Raw target records
    # ------------------------------------------------------------------------

    print_target_details(
        pages
    )

    print()
    print("=" * 100)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 100)
    print()


if __name__ == "__main__":
    main()