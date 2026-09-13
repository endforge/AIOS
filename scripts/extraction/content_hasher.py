"""
AlphaOmega Content Hasher

Purpose:
    Produces deterministic hashes for canonical extracted content.

Responsibilities:
    - Accept canonical content for hashing.
    - Produce the canonical SHA-256 content hash used by synchronization.
    - Provide deterministic hash results for equivalent canonical content.

Does NOT:
    - Retrieve source content.
    - Extract canonical text.
    - Determine synchronization state.
    - Persist Knowledge Objects.
"""

import hashlib


class ContentHasher:
    """
    Generate deterministic SHA-256 hashes for canonical content.
    """

    algorithm_name = "sha256"

    @staticmethod
    def generate(canonical_content):
        """
        Generate a SHA-256 hash for canonical content.

        Args:
            canonical_content:
                Canonical text content produced by Extraction.

        Returns:
            str:
                Lowercase hexadecimal SHA-256 digest.

        Raises:
            TypeError:
                If canonical_content is not a string.
        """

        if not isinstance(canonical_content, str):
            raise TypeError(
                "Canonical content must be a string."
            )

        content_bytes = canonical_content.encode(
            "utf-8"
        )

        return hashlib.sha256(
            content_bytes
        ).hexdigest()