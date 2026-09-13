"""
AlphaOmega Synchronization Base Section

Purpose:
    Defines the common base behavior for synchronization record sections.

Responsibilities:
    - Provide the shared foundation for stage-owned synchronization sections.
    - Allow an owning stage to populate its section while the section is unlocked.
    - Lock completed sections against further modification.
    - Freeze supported mutable values when a section is locked.
    - Report whether a section is locked.

Does NOT:
    - Define stage-specific synchronization data.
    - Determine when a synchronization stage has completed successfully.
    - Unlock a section after it has been locked.
    - Execute synchronization processing.
"""

from types import MappingProxyType
from typing import Any

from scripts.sync.sync_exceptions import SectionLockedError


class BaseSection:
    """
    Provides one-way locking for synchronization record sections.

    A section begins unlocked. Once lock() is called:

    - Existing attributes cannot be changed.
    - New attributes cannot be added.
    - Lists are converted to tuples.
    - Dictionaries are converted to read-only mappings.
    - Sets are converted to frozensets.
    - The section cannot be unlocked.
    """

    def __init__(self) -> None:
        """
        Initialize the section in an unlocked state.

        object.__setattr__ is used intentionally so initialization does not
        pass through the locking check in __setattr__.
        """
        object.__setattr__(self, "_locked", False)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Set an attribute only while the section is unlocked.

        This blocks both changes to existing attributes and creation of new
        attributes after the section has been locked.
        """
        if self.is_locked:
            raise SectionLockedError(
                f"{self.__class__.__name__} is locked and cannot modify "
                f"attribute '{name}'."
            )

        object.__setattr__(self, name, value)

    @property
    def is_locked(self) -> bool:
        """
        Return True when the section has been permanently locked.
        """
        return self._locked

    def lock(self) -> None:
        """
        Permanently lock the section.

        Mutable built-in containers are converted into immutable equivalents
        before the section is marked as locked. Calling lock() on an already
        locked section has no effect.
        """
        if self.is_locked:
            return

        for attribute_name, attribute_value in vars(self).items():
            if attribute_name == "_locked":
                continue

            frozen_value = self._freeze_value(attribute_value)
            object.__setattr__(self, attribute_name, frozen_value)

        object.__setattr__(self, "_locked", True)

    @classmethod
    def _freeze_value(cls, value: Any) -> Any:
        """
        Recursively convert common mutable containers into immutable forms.

        Conversions:

        - list -> tuple
        - dict -> MappingProxyType
        - set -> frozenset
        - tuple -> recursively frozen tuple

        Primitive values and unsupported object types are returned unchanged.
        """
        if isinstance(value, list):
            return tuple(cls._freeze_value(item) for item in value)

        if isinstance(value, dict):
            frozen_dictionary = {
                key: cls._freeze_value(item)
                for key, item in value.items()
            }
            return MappingProxyType(frozen_dictionary)

        if isinstance(value, set):
            return frozenset(cls._freeze_value(item) for item in value)

        if isinstance(value, tuple):
            return tuple(cls._freeze_value(item) for item in value)

        return value