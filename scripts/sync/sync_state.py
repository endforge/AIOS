"""
AlphaOmega Synchronization State

Purpose:
    Defines the synchronization states assigned by Discovery.

Responsibilities:
    - Define the canonical synchronization state values used to describe
      Discovery results.
    - Provide a shared synchronization-state type for downstream processing.

Does NOT:
    - Determine which synchronization state applies to an object.
    - Compare source objects with persisted Knowledge Objects.
    - Perform Discovery processing.
    - Execute synchronization.
"""

from enum import Enum


class SyncState(Enum):
    """
    Represents the synchronization state of a source object
    relative to the Canonical Knowledge Repository.
    """

    NEW = "NEW"
    MODIFIED = "MODIFIED"
    UNCHANGED = "UNCHANGED"