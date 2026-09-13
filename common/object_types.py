"""
AlphaOmega Synchronization Object Types

Purpose:
    Defines AlphaOmega's canonical synchronization object types.

Responsibilities:
    - Define the canonical CONTAINER object type.
    - Define the canonical CONTENT object type.
    - Provide shared object-type values that are independent of any
      individual synchronization stage.

Does NOT:
    - Determine the object type of a source object.
    - Perform synchronization processing.
    - Define source-specific object types.
"""

CONTAINER = "CONTAINER"
CONTENT = "CONTENT"