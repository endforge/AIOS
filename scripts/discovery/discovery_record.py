"""
AlphaOmega Discovery Record

Purpose:
    Represents the synchronization decision produced by Discovery for one
    translated source object.

Responsibilities:
    - Preserve orchestration correlation identity.
    - Store resolved Knowledge Object identity when one exists.
    - Store the Discovery synchronization state.
    - Store the factual reason for the comparison result.
    - Preserve the previous content hash when applicable.
    - Indicate whether downstream Extraction is required.

Does NOT:
    - Copy or reinterpret Translator-owned source facts.
    - Retrieve source content.
    - Perform Extraction or Load.
    - Persist Knowledge Objects.
"""


class DiscoveryRecord:
    """
    Stores Discovery-owned synchronization information for one object.

    The correlation_id is orchestration-owned execution metadata.
    Discovery propagates it but does not generate, modify, or
    interpret it.

    Translator-owned information remains in the TranslatorRecord.
    Discovery does not copy, modify, or reinterpret upstream fields.
    """

    def __init__(self):
        """
        Initialize an empty DiscoveryRecord.
        """

        #
        # Orchestration correlation identity
        #
        self.correlation_id = None

        #
        # Resolved AlphaOmega identity
        #
        self.knowledge_object_id = None

        #
        # Discovery synchronization decision
        #
        self.sync_state = None
        self.comparison_reason = None
        self.previous_content_hash = None
        self.requires_extraction = None