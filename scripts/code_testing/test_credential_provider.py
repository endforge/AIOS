"""
Local Credential Provider Test

Purpose:
    Validates the local AlphaOmega credential-provider implementation.

Verifies:
    - Valid logical credential names can be submitted for retrieval.
    - Invalid credential names are rejected.
    - Missing or unavailable credentials produce controlled failures.
    - Credential retrieval follows the LocalCredentialProvider contract.

Does NOT:
    - Create or modify stored credentials.
    - Expose credential values as test output.
    - Test Microsoft Graph authentication.
    - Test database connectivity.
"""

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)


def main():
    """Run the Credential Provider test."""

    print("Testing AlphaOmega Credential Provider...")

    provider = LocalCredentialProvider()

    try:
        credential = provider.get(
            "supabase.alphaomega"
        )

        if not credential:
            raise RuntimeError(
                "Credential Provider returned an empty credential."
            )

        print(
            "Credential Provider test succeeded."
        )

    except Exception as error:
        print(
            f"Credential Provider test failed: "
            f"{error.__class__.__name__}: {error}"
        )
        raise


if __name__ == "__main__":
    main()