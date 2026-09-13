"""
AlphaOmega Base Translator

Purpose:
    Defines the common interface that AlphaOmega Translator implementations
    must follow.

Responsibilities:
    - Define the shared Translator contract.
    - Require Translator implementations to process TranslationInput.
    - Establish TranslatorSection as the completed output of Translation.

Does NOT:
    - Implement source-specific translation.
    - Retrieve source objects.
    - Generate orchestration correlation identity.
    - Perform Discovery, Extraction, or Load.
"""


class BaseTranslator:
    """
    Base class for all AlphaOmega translators.
    """

    def run(self, connector_section):
        """
        Execute the Translator stage.

        Parameters
        ----------
        connector_section : ConnectorSection
            Locked ConnectorSection produced by the Connector stage.

        Returns
        -------
        TranslatorSection
            A completed TranslatorSection.

        Raises
        ------
        NotImplementedError
            If the translator does not implement this method.
        """

        raise NotImplementedError(
            "All translators must implement the 'run()' method."
        )