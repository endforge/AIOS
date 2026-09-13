"""
AlphaOmega Credential Provider Interface

Purpose:
    Defines the stable interface used by AlphaOmega infrastructure to
    retrieve credentials without depending on a specific credential-storage
    technology.

Responsibilities:
    - Define the common CredentialProvider interface.
    - Require credential providers to retrieve secrets by logical
      AlphaOmega credential name.
    - Preserve a storage-independent credential retrieval boundary.

Does NOT:
    - Store credentials.
    - Select a credential-storage technology.
    - Implement credential retrieval from a specific provider.
    - Expose provider-specific retrieval behavior to consumers.
"""

from abc import ABC, abstractmethod


class CredentialProvider(ABC):
    """Base interface for AlphaOmega credential providers."""

    @abstractmethod
    def get(self, credential_name: str) -> str:
        """
        Retrieve a credential using its logical AlphaOmega name.

        Args:
            credential_name: Logical name of the requested credential.

        Returns:
            The requested secret.

        Raises:
            ValueError: If the credential name is invalid.
            RuntimeError: If the credential cannot be retrieved.
        """
        raise NotImplementedError