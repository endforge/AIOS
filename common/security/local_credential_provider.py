"""
AlphaOmega Local Credential Provider

Purpose:
    Retrieves AlphaOmega secrets from operating-system protected
    credential storage through the common CredentialProvider interface.

Responsibilities:
    - Retrieve credentials from the local protected credential store.
    - Validate logical credential names before retrieval.
    - Use the AlphaOmega service name when accessing local credentials.
    - Return stored secrets through the common CredentialProvider contract.
    - Convert provider retrieval failures into controlled runtime errors.

Does NOT:
    - Store or modify credentials.
    - Expose provider-generated exception details.
    - Define credential consumers.
    - Require consuming components to depend directly on keyring.
"""

import keyring

from common.security.credential_provider import CredentialProvider


class LocalCredentialProvider(CredentialProvider):
    """Retrieve AlphaOmega secrets from local protected credential storage."""

    SERVICE_NAME = "AlphaOmega"

    def get(self, credential_name: str) -> str:
        """
        Retrieve a credential from protected local storage.

        Args:
            credential_name: Logical AlphaOmega credential name.

        Returns:
            The stored secret.

        Raises:
            ValueError: If the credential name is invalid.
            RuntimeError: If the credential cannot be retrieved.
        """

        if not isinstance(credential_name, str):
            raise ValueError("Credential name must be a string.")

        credential_name = credential_name.strip()

        if not credential_name:
            raise ValueError("Credential name cannot be empty.")

        try:
            credential = keyring.get_password(
                self.SERVICE_NAME,
                credential_name,
            )
        except Exception as error:
            # Do not expose provider-generated exception details because
            # provider messages cannot be assumed safe for logging.
            raise RuntimeError(
                f"Unable to retrieve credential '{credential_name}'."
            ) from error

        if credential is None:
            raise RuntimeError(
                f"Credential '{credential_name}' was not found."
            )

        return credential