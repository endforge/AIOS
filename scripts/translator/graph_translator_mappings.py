"""
AlphaOmega Microsoft Graph Translator Mappings

Purpose:
    Defines the source-specific mapping rules used to translate supported
    Microsoft Graph object types into canonical AlphaOmega object types.

Responsibilities:
    - Define supported Microsoft Graph source object mappings.
    - Map supported source structures to canonical CONTENT or CONTAINER
      object types.
    - Provide centralized mapping rules used by GraphTranslator.

Does NOT:
    - Execute Translation.
    - Retrieve Microsoft Graph objects.
    - Generate orchestration correlation identity.
    - Determine synchronization state.
    - Persist Knowledge Objects.
"""

from collections.abc import Mapping

from common.object_types import CONTAINER, CONTENT


# ============================================================================
# Microsoft Graph Source Object Types
# ============================================================================

GRAPH_NOTEBOOK = "notebook"
GRAPH_SECTION_GROUP = "sectionGroup"
GRAPH_ONENOTE_SECTION = "section"
GRAPH_ONENOTE_PAGE = "page"
GRAPH_DRIVE_ROOT = "driveRoot"
GRAPH_DRIVE_ITEM = "driveItem"


# ============================================================================
# Microsoft Graph Object Type Mappings
# ============================================================================

GRAPH_OBJECT_TYPE_MAPPING = {
    GRAPH_NOTEBOOK: CONTAINER,
    GRAPH_SECTION_GROUP: CONTAINER,
    GRAPH_ONENOTE_SECTION: CONTAINER,
    GRAPH_ONENOTE_PAGE: CONTENT,

    GRAPH_DRIVE_ROOT: CONTAINER,
    GRAPH_DRIVE_ITEM: CONTENT,
}


# ============================================================================
# Canonical Field Mappings
# ============================================================================

GRAPH_FIELD_MAPPING = {
    "id": "source_object_id",

    # Microsoft Graph uses different fields for object names depending
    # on the source object type.
    "displayName": "name",
    "name": "name",
    "title": "name",

    "createdDateTime": "source_created_at",
    "lastModifiedDateTime": "source_modified_at",
    "webUrl": "source_url",

    # OneDrive hierarchy
    "parentReference.id": "source_parent_object_id",
    "parentReference.path": "source_path",

    # OneNote section relationship.
    #
    # Connector may override this for nested OneNote pages after
    # page-level hierarchy has been proven.
    "parentSection.id": "source_parent_object_id",
}


# ============================================================================
# Reserved Microsoft Graph Fields
# ============================================================================

RESERVED_GRAPH_FIELDS = {
    "id",
    "@odata.type",
    "displayName",
    "name",
    "title",
    "createdDateTime",
    "lastModifiedDateTime",
    "webUrl",
    "parentReference",
    "parentSection",
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_canonical_object_type(source_object_type):
    """
    Determine the AlphaOmega canonical object type for a
    Microsoft Graph source object.

    Returns None if the object type is unsupported.
    """

    return GRAPH_OBJECT_TYPE_MAPPING.get(
        source_object_type
    )


def get_nested_value(
    raw_object,
    field_path,
):
    """
    Retrieve a value from a Microsoft Graph object using dot notation.

    Examples:
        parentReference.id
        parentReference.path
        parentSection.id
    """

    value = raw_object

    for field_name in (
        field_path.split(".")
    ):

        if not isinstance(
            value,
            Mapping,
        ):

            return None

        value = value.get(
            field_name
        )

        if value is None:

            return None

    return value