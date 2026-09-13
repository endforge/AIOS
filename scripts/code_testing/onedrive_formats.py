"""
OneDrive File Format Inventory

Purpose:
    Produces a read-only inventory of file formats present across the
    configured OneDrive Source of Truth.

Verifies:
    - The production GraphConnector can enumerate the configured OneDrive.
    - File extensions present in OneDrive can be identified and counted.
    - Supported and unsupported extraction formats can be inspected against
      the live source inventory.

Does NOT:
    - Modify OneDrive.
    - Write to the AlphaOmega database.
    - Extract or persist Knowledge Objects.
    - Change synchronization behavior.
"""

from collections import defaultdict
from pathlib import Path

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)

from scripts.extraction.text_extractor import (
    TextExtractor,
)


# ============================================================================
# Configuration
# ============================================================================

EXAMPLE_LIMIT = 5


# ============================================================================
# Helpers
# ============================================================================

def get_extension(file_name):
    """
    Return a normalized lowercase file extension.

    Files without an extension are represented explicitly so they
    are not silently lost from the inventory.
    """

    if not file_name:
        return "[NO NAME]"

    extension = (
        Path(file_name)
        .suffix
        .lower()
    )

    if not extension:
        return "[NO EXTENSION]"

    return extension


def get_display_path(raw_object):
    """
    Resolve the best available source path for inventory output.
    """

    connector_metadata = (
        raw_object.get(
            "connector_metadata"
        )
        or {}
    )

    object_path = (
        connector_metadata.get(
            "object_path"
        )
    )

    if object_path:
        return object_path

    source_path = (
        connector_metadata.get(
            "source_path"
        )
    )

    raw_graph_object = (
        raw_object.get(
            "raw_object"
        )
        or {}
    )

    name = (
        raw_graph_object.get(
            "name"
        )
        or "[UNNAMED]"
    )

    if source_path:
        return f"{source_path}/{name}"

    return name


# ============================================================================
# Inventory
# ============================================================================

def build_format_inventory(
    connector_section,
):
    """
    Build file-format counts and representative paths from the
    completed OneDrive Connector output.
    """

    format_counts = defaultdict(int)
    format_examples = defaultdict(list)

    container_count = 0
    content_count = 0

    for item in (
        connector_section.raw_objects
    ):

        source_object_type = (
            item.get(
                "source_object_type"
            )
        )

        raw_graph_object = (
            item.get(
                "raw_object"
            )
            or {}
        )

        # Microsoft Graph DriveItems identify folders with a
        # "folder" facet and files with a "file" facet.
        if (
            "folder"
            in raw_graph_object
        ):
            container_count += 1
            continue

        if (
            "file"
            not in raw_graph_object
        ):
            # Preserve visibility of unusual DriveItems rather than
            # accidentally classifying them as normal files.
            continue

        content_count += 1

        file_name = (
            raw_graph_object.get(
                "name"
            )
        )

        extension = (
            get_extension(
                file_name
            )
        )

        format_counts[
            extension
        ] += 1

        if (
            len(
                format_examples[
                    extension
                ]
            )
            < EXAMPLE_LIMIT
        ):
            format_examples[
                extension
            ].append(
                get_display_path(
                    item
                )
            )

    return {
        "format_counts":
            dict(
                format_counts
            ),

        "format_examples":
            dict(
                format_examples
            ),

        "container_count":
            container_count,

        "content_count":
            content_count,
    }


# ============================================================================
# Reporting
# ============================================================================

def print_summary(
    inventory,
):
    """
    Print the complete extension inventory.
    """

    format_counts = (
        inventory[
            "format_counts"
        ]
    )

    format_examples = (
        inventory[
            "format_examples"
        ]
    )

    supported_extensions = {
        extension.lower()
        for extension
        in TextExtractor.supported_extensions
    }

    print()

    print(
        "=" * 100
    )

    print(
        "ONEDRIVE FILE FORMAT INVENTORY"
    )

    print(
        "=" * 100
    )

    print()

    print(
        f"CONTAINER objects : "
        f"{inventory['container_count']}"
    )

    print(
        f"CONTENT objects   : "
        f"{inventory['content_count']}"
    )

    print(
        f"Unique extensions : "
        f"{len(format_counts)}"
    )

    print()

    print(
        "-" * 100
    )

    print(
        f"{'EXTENSION':<20}"
        f"{'COUNT':>10}   "
        f"{'ALPHAOMEGA EXTRACTION':<30}"
    )

    print(
        "-" * 100
    )

    sorted_formats = sorted(
        format_counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    supported_file_count = 0
    unsupported_file_count = 0

    supported_format_count = 0
    unsupported_format_count = 0

    for (
        extension,
        count,
    ) in sorted_formats:

        is_supported = (
            extension
            in supported_extensions
        )

        if is_supported:
            status = "SUPPORTED"
            supported_file_count += count
            supported_format_count += 1

        else:
            status = "UNSUPPORTED"
            unsupported_file_count += count
            unsupported_format_count += 1

        print(
            f"{extension:<20}"
            f"{count:>10}   "
            f"{status:<30}"
        )

    print()

    print(
        "=" * 100
    )

    print(
        "EXTRACTION COVERAGE"
    )

    print(
        "=" * 100
    )

    print()

    print(
        f"Supported extensions   : "
        f"{supported_format_count}"
    )

    print(
        f"Unsupported extensions : "
        f"{unsupported_format_count}"
    )

    print()

    print(
        f"Files currently supported   : "
        f"{supported_file_count}"
    )

    print(
        f"Files currently unsupported : "
        f"{unsupported_file_count}"
    )

    total_files = (
        supported_file_count
        + unsupported_file_count
    )

    if total_files:

        coverage = (
            supported_file_count
            / total_files
            * 100
        )

        print(
            f"Current extraction coverage : "
            f"{coverage:.2f}%"
        )

    # ========================================================================
    # Unsupported Formats
    # ========================================================================

    print()

    print(
        "=" * 100
    )

    print(
        "UNSUPPORTED FORMAT EXAMPLES"
    )

    print(
        "=" * 100
    )

    unsupported_found = False

    for (
        extension,
        count,
    ) in sorted_formats:

        if (
            extension
            in supported_extensions
        ):
            continue

        unsupported_found = True

        print()

        print(
            f"{extension} "
            f"({count} files)"
        )

        examples = (
            format_examples.get(
                extension,
                []
            )
        )

        for path in examples:

            print(
                f"  {path}"
            )

    if not unsupported_found:

        print()

        print(
            "No unsupported file formats found."
        )

    # ========================================================================
    # Supported Formats
    # ========================================================================

    print()

    print(
        "=" * 100
    )

    print(
        "SUPPORTED FORMAT EXAMPLES"
    )

    print(
        "=" * 100
    )

    for (
        extension,
        count,
    ) in sorted_formats:

        if (
            extension
            not in supported_extensions
        ):
            continue

        print()

        print(
            f"{extension} "
            f"({count} files)"
        )

        examples = (
            format_examples.get(
                extension,
                []
            )
        )

        for path in examples:

            print(
                f"  {path}"
            )


# ============================================================================
# Main
# ============================================================================

def main():

    print()

    print(
        "=" * 100
    )

    print(
        "AlphaOmega OneDrive File Format Inventory"
    )

    print(
        "=" * 100
    )

    print()

    print(
        "READ-ONLY ANALYSIS"
    )

    print(
        "No file content will be retrieved."
    )

    print(
        "No AlphaOmega database writes will occur."
    )

    print()

    print(
        "Enumerating complete OneDrive..."
    )

    connector = (
        GraphConnector()
    )

    connector_section = (
        connector.run(
            "OneDrive"
        )
    )

    if not (
        connector_section.is_locked
    ):
        raise RuntimeError(
            "OneDrive ConnectorSection "
            "was not locked."
        )

    print(
        "PASS: Production OneDrive Connector "
        "enumeration completed."
    )

    print()

    print(
        "Building format inventory..."
    )

    inventory = (
        build_format_inventory(
            connector_section
        )
    )

    print_summary(
        inventory
    )

    print()

    print(
        "=" * 100
    )

    print(
        "FINAL RESULT"
    )

    print(
        "=" * 100
    )

    print()

    print(
        "PASS: OneDrive format inventory completed."
    )

    print(
        "No AlphaOmega database writes were performed."
    )

    print()


if __name__ == "__main__":
    main()