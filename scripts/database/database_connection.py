"""
AlphaOmega Database Connection

Purpose:
    Establishes authenticated access to the AlphaOmega Supabase database.

Responsibilities:
    - Retrieve required database credentials through the configured
      CredentialProvider.
    - Create the Supabase database client.
    - Provide the established client to database repositories and services.
    - Keep credential retrieval behind the credential-provider boundary.

Does NOT:
    - Store credentials.
    - Implement repository operations.
    - Determine synchronization behavior.
    - Execute synchronization stages.
    - Own database schema definitions.
"""

import os

from supabase import Client, create_client

from common.security.credential_provider import CredentialProvider


class DatabaseConnection:
    """
    Establish authenticated access to the AlphaOmega Supabase database.
    """

    SUPABASE_URL_VARIABLE = "SUPABASE_URL"
    SUPABASE_KEY_VARIABLE = "SUPABASE_PUBLISHABLE_KEY"
    SUPABASE_EMAIL_VARIABLE = "SUPABASE_ALPHAOMEGA_EMAIL"

    SUPABASE_CREDENTIAL_NAME = "supabase.alphaomega"

    def __init__(self, credential_provider: CredentialProvider):
        """
        Initialize the database connection.

        Args:
            credential_provider:
                AlphaOmega Credential Provider used to obtain the
                Supabase service identity secret.
        """

        if credential_provider is None:
            raise ValueError(
                "Credential Provider is required."
            )

        self._credential_provider = credential_provider

    def connect(self) -> Client:
        """
        Create and authenticate a Supabase client.

        Returns:
            Client:
                Authenticated Supabase client constrained by RLS.

        Raises:
            RuntimeError:
                If required configuration is unavailable or
                authentication cannot be established.
        """

        supabase_url = self._get_configuration(
            self.SUPABASE_URL_VARIABLE
        )

        supabase_key = self._get_configuration(
            self.SUPABASE_KEY_VARIABLE
        )

        supabase_email = self._get_configuration(
            self.SUPABASE_EMAIL_VARIABLE
        )

        try:
            supabase_password = self._credential_provider.get(
                self.SUPABASE_CREDENTIAL_NAME
            )
        except Exception as error:
            raise RuntimeError(
                "Unable to obtain the Supabase service identity credential."
            ) from error

        try:
            client = create_client(
                supabase_url,
                supabase_key,
            )
        except Exception as error:
            raise RuntimeError(
                "Unable to create the Supabase client."
            ) from error

        try:
            auth_response = client.auth.sign_in_with_password(
                {
                    "email": supabase_email,
                    "password": supabase_password,
                }
            )
        except Exception as error:
            raise RuntimeError(
                "Supabase authentication failed."
            ) from error

        if auth_response.session is None:
            raise RuntimeError(
                "Supabase authentication did not return a session."
            )

        if auth_response.user is None:
            raise RuntimeError(
                "Supabase authentication did not return an authenticated user."
            )

        return client

    @staticmethod
    def _get_configuration(variable_name: str) -> str:
        """
        Retrieve required public configuration from the environment.

        Args:
            variable_name:
                Name of the required environment variable.

        Returns:
            str:
                Configuration value.

        Raises:
            RuntimeError:
                If the configuration value is unavailable.
        """

        value = os.getenv(variable_name)

        if value is None or not value.strip():
            raise RuntimeError(
                f"Required configuration '{variable_name}' is unavailable."
            )

        return value.strip()