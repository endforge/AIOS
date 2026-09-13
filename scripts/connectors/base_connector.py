"""
AlphaOmega Base Connector

Purpose:
    Defines the contract that all AlphaOmega connectors must follow.

Responsibilities:
    - Define the common Connector interface.
    - Require connectors to implement the run operation.
    - Establish ConnectorSection as the completed output of Connector
      processing.

Does NOT:
    - Connect to a specific Source of Truth.
    - Implement source-specific retrieval behavior.
    - Translate retrieved source objects.
    - Perform Discovery, Extraction, or Load processing.
"""


class BaseConnector:
    """
    Base class for all AlphaOmega connectors.
    """

    def run(self, source_name):
        """
        Execute the Connector stage.

        Parameters
        ----------
        source_name : str
            Name of the Source of Truth.

        Returns
        -------
        ConnectorSection
            A completed ConnectorSection.

        Raises
        ------
        NotImplementedError
            If the connector does not implement this method.
        """

        raise NotImplementedError(
            "All connectors must implement the 'run()' method."
        )