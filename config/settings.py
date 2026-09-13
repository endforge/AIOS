"""
AlphaOmega Configuration Settings

Purpose:
    Loads required local AlphaOmega configuration settings used by
    Microsoft Graph connectivity.

Responsibilities:
    - Load configuration values from the config .env file.
    - Retrieve required settings from the process environment.
    - Fail when a required configuration setting is unavailable.
    - Expose the configured Microsoft Graph client ID.

Does NOT:
    - Retrieve protected credentials.
    - Store or modify configuration values.
    - Authenticate to Microsoft Graph.
    - Establish Microsoft Graph connections.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).parent / ".env"

load_dotenv(ENV_FILE)


def get_required_setting(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Required configuration setting '{name}' was not found."
        )

    return value


GRAPH_CLIENT_ID = get_required_setting("ALPHAOMEGA_CLIENT_ID")