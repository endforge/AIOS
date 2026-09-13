"""
AlphaOmega Connector Section

Purpose:
    Stores the completed raw output produced by the Connector stage
    during a synchronization run.

Responsibilities:
    - Store raw source objects produced by the Connector stage.
    - Store Connector-stage record errors.
    - Record whether Connector processing succeeded.
    - Provide completed Connector output through the shared synchronization
      section contract.

Does NOT:
    - Connect to a Source of Truth.
    - Retrieve source objects itself.
    - Translate raw source objects.
    - Modify Connector output after the section is locked.
"""

from scripts.sync.sync_base_section import BaseSection


class ConnectorSection(BaseSection):
    """
    Contains raw information retrieved from a Source of Truth.

    The Connector stage owns this section.

    The section remains mutable while Connector is executing.
    It is locked only after Connector completely enumerates and
    validates the requested synchronization scope.

    No partial ConnectorSection is passed downstream.
    """

    section_name = "connector"

    def __init__(self, source_name):
        """
        Initialize an empty Connector section for a source.
        """

        super().__init__()

        self.source_name = source_name

        self.connection_succeeded = False

        # Each item contains:
        #
        # {
        #     "source_object_type": "...",
        #     "raw_object": {...}
        # }
        #
        # raw_object remains exactly as received from the Source of Truth.
        self.raw_objects = []

        self.raw_metadata = {}