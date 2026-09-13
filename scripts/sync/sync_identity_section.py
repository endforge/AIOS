"""
AlphaOmega Synchronization Identity Section

Purpose:
    Stores stable identity information associated with a synchronization
    record.

Responsibilities:
    - Store synchronization correlation identity.
    - Store stable source identity for the synchronized object.
    - Store canonical synchronization identity information shared across
      synchronization processing.
    - Provide identity information through the shared synchronization
      section contract.

Does NOT:
    - Generate source-native identities.
    - Retrieve source objects.
    - Determine synchronization state.
    - Execute synchronization stages.
"""


from scripts.sync.sync_base_section import SyncBaseSection


class SyncIdentitySection(SyncBaseSection):
    """
    Identifies a synchronization run.
    """

    @property
    def section_name(self) -> str:
        return "identity"

    def __init__(self):
        super().__init__()

        self.sync_run_id = None
        self.start_time = None