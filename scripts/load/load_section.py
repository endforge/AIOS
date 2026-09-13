"""
AlphaOmega Load Section

Purpose:
    Stores the completed output produced by the Load stage during a
    synchronization run.

Responsibilities:
    - Store LoadRecords produced by Load.
    - Store record-level Load errors.
    - Record whether Load completed successfully.
    - Provide completed Load output through the shared synchronization
      section contract.

Does NOT:
    - Execute Load itself.
    - Determine synchronization state.
    - Modify upstream stage records.
    - Allow modification after the section is locked.
"""

from scripts.sync.sync_base_section import BaseSection


class LoadSection(BaseSection):
    """
    Contains the record-level errors and completion status
    produced by the Load stage.

    Successful persistence is represented by the Canonical
    Knowledge Repository and synchronization history.

    The Load stage owns this section.

    After the Load stage completes, the section is locked and
    becomes read-only.
    """

    section_name = "load"

    def __init__(self):
        """
        Initialize an empty Load section.
        """

        super().__init__()

        self.record_errors = []
        self.load_succeeded = False