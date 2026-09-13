"""
Database Connection Test

Purpose:
    Validates AlphaOmega database connectivity using the production database
    connection and credential boundaries.

Verifies:
    - Required database credentials can be retrieved.
    - DatabaseConnection can establish a usable database client.
    - The client can perform a read operation against knowledge_objects.
    - Database connectivity works through the intended production boundary.

Does NOT:
    - Modify Knowledge Objects.
    - Test synchronization behavior.
    - Test repository business operations.
    - Modify database configuration or credentials.
"""

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)


def main():
    """Run the authenticated database connection test."""

    print("Testing authenticated AlphaOmega database connection...")

    credential_provider = LocalCredentialProvider()

    database_connection = DatabaseConnection(
        credential_provider=credential_provider
    )

    try:
        client = database_connection.connect()

        print("Supabase authentication succeeded.")

        response = (
            client.table("knowledge_objects")
            .select("id")
            .limit(1)
            .execute()
        )

        if response.data is None:
            raise RuntimeError(
                "knowledge_objects SELECT returned no response data."
            )

        print("knowledge_objects SELECT succeeded.")
        print("Database connection test succeeded.")

    except Exception as error:
        print(
            f"Database connection test failed: "
            f"{error.__class__.__name__}: {error}"
        )
        raise


if __name__ == "__main__":
    main()