"""
AlphaOmega Synchronization Record

Purpose:
    Contains the completed sections for a single synchronization run.

Responsibilities:
    - Store completed synchronization sections.
    - Attach completed sections by section name.
    - Prevent duplicate section names from being attached.
    - Retrieve previously attached sections.
    - Report whether a section has been attached.
    - Return all attached sections.

Does NOT:
    - Populate stage-owned sections.
    - Determine when a section is complete.
    - Modify the contents of attached sections.
    - Execute synchronization stages.
"""

from scripts.sync.sync_base_section import BaseSection


class SyncRecord:
    """
    Stores the completed sections for a synchronization run.

    Sections are attached only after they have been
    populated, validated, and locked.
    """

    def __init__(self):
        """
        Initialize an empty synchronization record.
        """

        self._sections = {}

    def attach(self, section: BaseSection):
        """
        Attach a completed section to the synchronization record.

        Raises:
            ValueError:
                If a section with the same name has already
                been attached.
        """

        section_name = section.section_name

        if section_name in self._sections:
            raise ValueError(
                f"Section '{section_name}' has already been attached."
            )

        self._sections[section_name] = section

    def get(self, section_name):
        """
        Return a previously attached section.

        Raises:
            KeyError:
                If the requested section does not exist.
         """

        if section_name not in self._sections:
            raise KeyError(
                f"Section '{section_name}' does not exist."
            )

        return self._sections[section_name]

    def contains(self, section_name):
        """
        Determine whether a section has been attached.

        Returns:
            bool:
                True if the section exists.
                    False otherwise.
        """

        return section_name in self._sections

    def all_sections(self):
        """
        Return all attached sections.
        
        Returns:
            dict:
                Dictionary containing every attached section.
        """
        return self._sections