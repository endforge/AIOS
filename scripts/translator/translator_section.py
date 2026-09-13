"""
AlphaOmega Translator Section

Purpose:
    Stores the completed output produced by the Translator stage during a
    synchronization run.

Responsibilities:
    - Store TranslatorRecords produced by Translation.
    - Store record-level Translator errors.
    - Record whether Translation completed successfully.
    - Provide completed Translator output through the shared synchronization
      section contract.

Does NOT:
    - Translate source objects itself.
    - Retrieve source data.
    - Perform Discovery, Extraction, or Load.
    - Allow modification after the section is locked.
"""

from scripts.sync.sync_base_section import BaseSection


class TranslatorSection(BaseSection):
    """
    Contains the canonical synchronization records and record-level
    errors produced by the Translator stage.

    The Translator stage owns this section.

    After the Translator stage completes, the section is locked and
    becomes read-only for all downstream stages.
    """

    section_name = "translator"

    def __init__(self):
        """
        Initialize an empty Translator section.
        """

        super().__init__()

        self.translated_records = []
        self.record_errors = []

        self.translation_succeeded = False