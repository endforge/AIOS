"""
AlphaOmega Translator Record

Purpose:
    Represents the canonical source facts produced by Translation for one
    source object.

Responsibilities:
    - Preserve orchestration correlation identity.
    - Store canonical Source of Truth identity.
    - Store source-native object and parent identities.
    - Store canonical object type.
    - Store normalized name and hierarchy path.
    - Store source-created and source-modified timestamps.
    - Store Translator-owned factual source metadata.

Does NOT:
    - Generate correlation identity.
    - Determine synchronization state.
    - Retrieve source content.
    - Store Discovery or Extraction decisions.
    - Persist Knowledge Objects.
"""


class TranslatorRecord:
    """
    Represents one translated synchronization object.

    The correlation_id is orchestration-owned execution metadata.
    Translator propagates it but does not generate, modify, or
    interpret it.

    Translator-owned fields remain separate from orchestration
    correlation identity.
    """

    def __init__(self):
        """
        Initialize an empty TranslatorRecord.
        """

        #
        # Orchestration correlation identity
        #
        self.correlation_id = None

        #
        # Stable source identity
        #
        self.source_name = None
        self.source_object_id = None
        self.source_parent_object_id = None

        #
        # Canonical synchronization information
        #
        self.object_type = None
        self.name = None
        self.source_path = None

        #
        # Source metadata
        #
        self.source_created_at = None
        self.source_modified_at = None
        self.source_url = None

        #
        # Repository-independent metadata
        #
        self.metadata = {}