"""
AlphaOmega Synchronization Association

Purpose:
    Maintains cross-stage record association for one source object
    during a synchronization run.

Responsibilities:
    - Maintain the Translator, Discovery, and Extraction records associated
      with one source object.
    - Attach each stage record to the association as processing progresses.
    - Preserve the relationship between records representing the same source
      object across synchronization stages.

Does NOT:
    - Execute synchronization stages.
    - Create stage records.
    - Determine synchronization state.
    - Persist synchronization data.
"""


class SynchronizationAssociation:
    """
    Stores references to stage-owned records belonging to the same
    synchronization object.

    Synchronization Orchestration owns this association.

    Stage-owned information is referenced rather than copied.
    """

    def __init__(
        self,
        correlation_id,
    ):
        """
        Initialize one synchronization association.

        Args:
            correlation_id:
                Run-scoped correlation UUID assigned by
                Synchronization Orchestration.
        """

        if (
            correlation_id is None
            or not str(correlation_id).strip()
        ):
            raise ValueError(
                "correlation_id is required."
            )

        self.correlation_id = str(
            correlation_id
        )

        self.translator_record = None
        self.discovery_record = None
        self.extraction_record = None

    def attach_translator(
        self,
        translator_record,
    ):
        """
        Attach the Translator-owned record.
        """

        if translator_record is None:
            raise ValueError(
                "TranslatorRecord is required."
            )

        if self.translator_record is not None:
            raise ValueError(
                "TranslatorRecord has already been attached."
            )

        if (
            translator_record.correlation_id
            != self.correlation_id
        ):
            raise ValueError(
                "TranslatorRecord correlation_id does not "
                "match the synchronization association."
            )

        self.translator_record = (
            translator_record
        )

    def attach_discovery(
        self,
        discovery_record,
    ):
        """
        Attach the Discovery-owned record.
        """

        if discovery_record is None:
            raise ValueError(
                "DiscoveryRecord is required."
            )

        if self.discovery_record is not None:
            raise ValueError(
                "DiscoveryRecord has already been attached."
            )

        if (
            discovery_record.correlation_id
            != self.correlation_id
        ):
            raise ValueError(
                "DiscoveryRecord correlation_id does not "
                "match the synchronization association."
            )

        self.discovery_record = (
            discovery_record
        )

    def attach_extraction(
        self,
        extraction_record,
    ):
        """
        Attach the Extraction-owned record.
        """

        if extraction_record is None:
            raise ValueError(
                "ExtractionRecord is required."
            )

        if self.extraction_record is not None:
            raise ValueError(
                "ExtractionRecord has already been attached."
            )

        if (
            extraction_record.correlation_id
            != self.correlation_id
        ):
            raise ValueError(
                "ExtractionRecord correlation_id does not "
                "match the synchronization association."
            )

        self.extraction_record = (
            extraction_record
        )