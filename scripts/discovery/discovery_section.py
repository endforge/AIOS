"""
AlphaOmega Discovery Section

Purpose:
    Stores the completed output produced by the Discovery stage during a
    synchronization run.

Responsibilities:
    - Store DiscoveryRecords produced by Discovery.
    - Store record-level Discovery errors.
    - Record whether Discovery completed successfully.
    - Provide completed Discovery output through the shared synchronization
      section contract.

Does NOT:
    - Execute Discovery itself.
    - Modify Translator-owned information.
    - Perform Extraction or Load.
    - Allow modification after the section is locked.
"""

from scripts.sync.sync_base_section import BaseSection


class DiscoverySection(BaseSection):
    """
    Contains the synchronization records and record-level
    errors produced by the Discovery stage.

    The Discovery stage owns this section.

    After the Discovery stage completes, the section is locked and
    becomes read-only for all downstream stages.
    """

    section_name = "discovery"

    def __init__(self):
        """
        Initialize an empty Discovery section.
        """

        super().__init__()

        self.discovery_records = []
        self.record_errors = []

        self.discovery_succeeded = False