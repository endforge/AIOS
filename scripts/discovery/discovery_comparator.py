"""
AlphaOmega Discovery Comparator

Purpose:
    Compares canonical translated source facts with persisted Knowledge Object
    facts to determine whether synchronization-relevant metadata has changed.

Responsibilities:
    - Compare the synchronization fields owned by Discovery.
    - Identify factual differences between translated source state and
      persisted Knowledge Object state.
    - Return comparison results used by Discovery to distinguish MODIFIED
      from UNCHANGED records.

Does NOT:
    - Determine whether a source object is NEW.
    - Retrieve Knowledge Objects.
    - Retrieve source content.
    - Perform Extraction or Load.
    - Persist synchronization results.
"""

from datetime import datetime


class DiscoveryComparator:
    """
    Compare the synchronization facts owned by Translator with the
    corresponding facts stored in the Canonical Knowledge Repository.

    Discovery compares exactly three facts:

    - name
    - source_parent_object_id
    - source_modified_at
    """

    @staticmethod
    def compare(translator_record, knowledge_object):
        """
        Compare a translated source object with an existing
        Knowledge Object.

        Args:
            translator_record:
                Trusted TranslatorRecord produced by Translator.

            knowledge_object:
                Existing Knowledge Object facts returned by the
                KnowledgeObjectRepository.

        Returns:
            list[str]:
                Human-readable reasons describing each detected change.

                An empty list means the object is unchanged.
        """

        reasons = []

        #
        # Name
        #
        if translator_record.name != knowledge_object["title"]:
            reasons.append("name changed")

        #
        # Parent identity
        #
        if (
            translator_record.source_parent_object_id
            != knowledge_object["source_parent_object_id"]
        ):
            reasons.append("source parent changed")

        #
        # Source modified timestamp
        #
        translator_modified_at = (
            DiscoveryComparator._normalize_datetime(
                translator_record.source_modified_at
            )
        )

        repository_modified_at = (
            DiscoveryComparator._normalize_datetime(
                knowledge_object["source_modified_at"]
            )
        )

        if translator_modified_at != repository_modified_at:
            reasons.append(
                "source modified timestamp changed"
            )

        return reasons

    @staticmethod
    def _normalize_datetime(value):
        """
        Normalize a synchronization timestamp for comparison.

        Accepts either a datetime object or an ISO-8601 string.

        Returns:
            datetime or None
        """

        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )
            except ValueError as error:
                raise ValueError(
                    f"Invalid synchronization timestamp: {value!r}"
                ) from error

        raise TypeError(
            "Synchronization timestamp must be a datetime, "
            "ISO-8601 string, or None."
        )