"""
AlphaOmega Translation Input

Purpose:
    Creates the orchestration-owned Translator input produced from a
    completed Connector Section.

Responsibilities:
    - Preserve completed Connector output for Translator processing.
    - Assign one run-scoped correlation UUID to each source object before
      Translator processing begins.
    - Provide the Translator with source objects and their correlation
      identities without modifying Connector output.

Does NOT:
    - Modify completed Connector output.
    - Translate source objects.
    - Determine canonical object types.
    - Perform Discovery, Extraction, or Load processing.
"""

from types import MappingProxyType
from uuid import uuid4


class TranslationInput:
    """
    Represents the orchestration-owned input to the Translator stage.

    Correlation identity belongs to Synchronization Orchestration.

    Connector-owned raw source information remains unchanged.
    """

    def __init__(
        self,
        connector_section,
    ):
        """
        Build Translator input from a completed ConnectorSection.

        Args:
            connector_section:
                Completed and locked ConnectorSection produced by
                the Connector stage.
        """

        if connector_section is None:
            raise ValueError(
                "ConnectorSection is required."
            )

        if not connector_section.is_locked:
            raise ValueError(
                "ConnectorSection must be locked before "
                "TranslationInput is created."
            )

        self.source_name = (
            connector_section.source_name
        )

        correlated_objects = []

        for connector_object in (
            connector_section.raw_objects
        ):
            correlation_id = str(
                uuid4()
            )

            correlated_object = {
                "correlation_id": correlation_id,
                "source_object_type": (
                    connector_object[
                        "source_object_type"
                    ]
                ),
                "raw_object": (
                    connector_object[
                        "raw_object"
                    ]
                ),
                "connector_metadata": (
                    connector_object.get(
                        "connector_metadata",
                        {},
                    )
                ),
            }

            correlated_objects.append(
                MappingProxyType(
                    correlated_object
                )
            )

        self.raw_objects = tuple(
            correlated_objects
        )