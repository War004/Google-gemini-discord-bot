import os
import requests
from typing import Optional
from google.genai import types


class StartUp:
    def __init__(self, token: str, system_instruction: str):
        self.botToken = token
        self.app_id = self.resolve_application_id()

    def resolve_application_id(self) -> int:
        """
        Gets the Application ID by checking the .env file first, then falling back
        to a dynamic API call.
        """
        print("--- Resolving Application ID ---")

        # 1. Prioritize the .env file for efficiency and explicit configuration.
        print("Attempt 1: Checking for APPLICATION_ID in .env file...")
        try:
            app_id_str = os.getenv("APPLICATION_ID")
            if app_id_str:
                app_id = int(app_id_str)
                print(f"Success! Found Application ID in .env file: {app_id}")
                return app_id
        except (ValueError, TypeError):
            print("[Warning] APPLICATION_ID in .env file is not a valid number. Ignoring it.")

        # 2. If not in .env, try the dynamic method as a fallback.
        print("Attempt 2: Fetching dynamically from Discord API...")
        app_id = self.get_app_id_dynamically(self.botToken)
        if app_id:
            print(f"Success! Dynamically resolved Application ID: {app_id}")
            return app_id

        # 3. If both methods fail, exit with a clear error message.
        print("---------------------------------")
        raise ValueError(
            "CRITICAL: Could not resolve the bot's Application ID.\n"
            "Please find your Application ID in the Discord Developer Portal\n"
            "and add it to your .env file, like this:\n\n"
            "APPLICATION_ID=123456789012345678"
        )

    def get_app_id_dynamically(self, botToken: str) -> Optional[int]:
        """Tries to fetch the application ID from Discord's API using a synchronous request."""
        url = "https://discord.com/api/v10/oauth2/applications/@me"
        headers = {"Authorization": f"Bot {botToken}"}
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            info = response.json()
            return int(info["id"])
        except requests.exceptions.RequestException as e:
            print(f"[Warning] Dynamic Application ID fetch failed: {e}")
        return None