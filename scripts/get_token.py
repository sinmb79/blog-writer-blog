"""
Create token.json for Blogger publishing.

Usage:
    python scripts/get_token.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/blogger",
    "https://www.googleapis.com/auth/webmasters",
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOKEN_PATH = PROJECT_ROOT / "token.json"
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"


def main() -> None:
    if not CREDENTIALS_PATH.exists():
        print(f"[ERROR] credentials.json not found: {CREDENTIALS_PATH}")
        print("Download OAuth desktop app credentials from Google Cloud Console and place the file here.")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    print("=" * 60)
    print("token.json created successfully")
    print("=" * 60)
    print(f"Saved to: {TOKEN_PATH}")
    print("You can now use Blogger publishing features in the app.")


if __name__ == "__main__":
    main()
