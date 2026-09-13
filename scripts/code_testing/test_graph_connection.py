"""
Microsoft Graph Connection Test

Purpose:
    Validates the production Microsoft Graph connection through a live
    authenticated request.

Verifies:
    - Microsoft Graph configuration can be loaded.
    - Authentication through MSAL succeeds.
    - An access token can be obtained.
    - An authenticated Microsoft Graph request can be sent.
    - Microsoft Graph returns a valid HTTP response.
    - Returned JSON can be parsed.

Does NOT:
    - Modify Microsoft Graph source data.
    - Enumerate a complete Source of Truth.
    - Execute synchronization.
    - Write to the AlphaOmega database.
"""

from scripts.connectors.ms_graph.graph_connection import graph_get


def test_graph_connection():
    """
    Request the signed-in user's basic Microsoft Graph profile.
    """

    endpoint = "/me"

    print("Testing Microsoft Graph connection...")

    response = graph_get(endpoint)

    data = response.json()

    print("Microsoft Graph connection succeeded.")
    print(f"Display name: {data.get('displayName')}")
    print(f"User ID: {data.get('id')}")
    print(f"Email: {data.get('mail')}")


if __name__ == "__main__":
    test_graph_connection()