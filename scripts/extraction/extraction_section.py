"""
AlphaOmega Extraction Section

Purpose:
    Stores the completed output produced by the Extraction stage during a
    synchronization run.

Responsibilities:
    - Store ExtractionRecords produced by Extraction.
    - Store record-level Extraction errors.
    - Record whether Extraction completed successfully.
    - Provide completed Extraction output through the shared synchronization
      section contract.

Does NOT:
    - Execute Extraction itself.
    - Determine synchronization state.
    - Perform Load.
    - Allow modification after the section is locked.
"""

from scripts.sync.sync_base_section import BaseSection


class ExtractionSection(BaseSection):
    """
    Contains the extraction records and record-level
    errors produced by the Extraction stage.

    The Extraction stage owns this section.

    After the Extraction stage completes, the section is locked and
    becomes read-only for all downstream stages.
    """

    section_name = "extraction"

    def __init__(self):
        """
        Initialize an empty Extraction section.
        """

        super().__init__()

        self.extraction_records = []
        self.record_errors = []

        self.extraction_succeeded = False