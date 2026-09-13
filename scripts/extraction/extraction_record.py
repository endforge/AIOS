"""
AlphaOmega Extraction Record

Purpose:
    Represents the canonical knowledge produced by Extraction for one source
    object requiring extraction.

Responsibilities:
    - Preserve orchestration correlation identity.
    - Store canonical extracted content.
    - Store the canonical content hash.
    - Store Extraction-owned canonical metadata.
    - Store extractor identity and extraction timestamp.
    - Validate required Extraction output.

Does NOT:
    - Generate or interpret correlation identity.
    - Copy or reinterpret Translator or Discovery fields.
    - Retrieve source content.
    - Determine synchronization state.
    - Persist Knowledge Objects.
"""


class ExtractionRecord:
    """
    Stores Extraction-owned canonical knowledge for one object.

    The correlation_id is orchestration-owned execution metadata.
    Extraction propagates it but does not generate, modify, or
    interpret it.

    Translator-owned and Discovery-owned information remains in their
    respective records. Extraction does not copy, modify, or reinterpret
    upstream fields.
    """

    def __init__(self):
        """
        Initialize an empty ExtractionRecord.
        """

        #
        # Orchestration correlation identity
        #
        self.correlation_id = None

        #
        # Canonical knowledge
        #
        self.canonical_content = None
        self.content_hash = None
        self.canonical_metadata = {}

        #
        # Extraction information
        #
        self.extractor_name = None
        self.extraction_timestamp = None

    def validate(self):
        """
        Validate that the ExtractionRecord satisfies the
        required Extraction output contract.

        Required:
            - canonical_content must be a non-empty string.
            - content_hash must be a valid SHA-256 hexadecimal digest.

        Raises:
            ValueError:
                If the ExtractionRecord is incomplete or invalid.
        """

        if not isinstance(
            self.canonical_content,
            str,
        ):
            raise ValueError(
                "canonical_content must be a string."
            )

        if not self.canonical_content.strip():
            raise ValueError(
                "canonical_content cannot be empty."
            )

        if not isinstance(
            self.content_hash,
            str,
        ):
            raise ValueError(
                "content_hash must be a string."
            )

        if len(self.content_hash) != 64:
            raise ValueError(
                "content_hash must be a 64-character "
                "SHA-256 hexadecimal digest."
            )

        try:
            int(
                self.content_hash,
                16,
            )

        except ValueError as error:
            raise ValueError(
                "content_hash must contain only "
                "hexadecimal characters."
            ) from error

        return True