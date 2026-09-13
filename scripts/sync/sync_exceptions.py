"""
AlphaOmega Synchronization Exceptions

Purpose:
    Defines the custom exception types used by the AlphaOmega
    Synchronization Framework.

Responsibilities:
    - Provide synchronization-specific exception types.
    - Distinguish stage, record, validation, configuration, connection,
      source, object-type, and section-lock failures.
    - Provide shared exception types that synchronization components can
      raise and handle consistently.

Does NOT:
    - Detect synchronization failures.
    - Handle or recover from raised exceptions.
    - Perform logging.
    - Execute synchronization processing.
"""


# ============================================================================
# Base Exceptions
# ============================================================================


class SynchronizationError(Exception):
    """
    Base class for all synchronization exceptions.
    """

    pass


class StageError(SynchronizationError):
    """
    Base exception for stage-level failures.

    Stage-level exceptions terminate the current stage and
    return control to the Synchronization Orchestrator.
    """

    pass


class RecordError(SynchronizationError):
    """
    Base exception for record-level failures.

    Record-level exceptions affect only a single record.
    Processing continues with remaining records.
    """

    pass


# ============================================================================
# Framework Exceptions
# ============================================================================


class SectionLockedError(StageError):
    """
    Raised when attempting to modify a synchronization
    section after it has been locked.
    """

    pass


class ValidationError(StageError):
    """
    Raised when a synchronization object fails validation.
    """

    pass


class ConfigurationError(StageError):
    """
    Raised when synchronization configuration is invalid
    or incomplete.
    """

    pass


# ============================================================================
# Connector Exceptions
# ============================================================================


class ConnectorError(StageError):
    """
    Base exception for Connector stage failures.
    """

    pass


class UnsupportedSourceError(ConnectorError):
    """
    Raised when a requested Source of Truth is unsupported.
    """

    pass


class ConnectionFailedError(ConnectorError):
    """
    Raised when a connection to a Source of Truth fails.
    """

    pass


# ============================================================================
# Translator Exceptions
# ============================================================================


class TranslatorError(StageError):
    """
    Base exception for Translator stage failures.
    """

    pass


class UnsupportedObjectTypeError(RecordError):
    """
    Raised when a source object cannot be translated into
    an AlphaOmega canonical object type.
    """

    def __init__(
        self,
        stage,
        source_name,
        object_type,
        object_id,
        object_name,
    ):

        self.stage = stage
        self.source_name = source_name
        self.object_type = object_type
        self.object_id = object_id
        self.object_name = object_name

        super().__init__(
            f"Unsupported object type '{object_type}' "
            f"for object '{object_name}' "
            f"({object_id}) "
            f"from source '{source_name}'."
        )


# ============================================================================
# Discovery Exceptions
# ============================================================================


class DiscoveryError(StageError):
    """
    Base exception for Discovery stage failures.
    """

    pass

class DiscoveryRecordError(RecordError):
    """
    Raised when Discovery cannot evaluate one source object
    but can safely continue processing remaining records.
    """

    pass

# ============================================================================
# Extraction Exceptions
# ============================================================================


class ExtractionError(StageError):
    """
    Base exception for Extraction stage failures.
    """

    pass


class ExtractionRecordError(RecordError):
    """
    Raised when Extraction cannot process one source object
    but can safely continue processing remaining records.
    """

    pass


# ============================================================================
# Load Exceptions
# ============================================================================


class LoadError(StageError):
    """
    Base exception for Load stage failures.
    """

    pass


# ============================================================================
# Synchronization Exceptions
# ============================================================================


class OrchestratorError(StageError):
    """
    Raised when the Synchronization Orchestrator
    encounters an unrecoverable error.
    """

    pass