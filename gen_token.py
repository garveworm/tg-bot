#!/usr/bin/env python3
"""Run this locally to generate a fresh token.json, then copy its contents
into the GOOGLE_TOKEN_JSON environment variable on Render."""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
creds = flow.run_local_server(port=8080)

with open("token.json", "w") as f:
    f.write(creds.to_json())

print("token.json written. Copy its contents into GOOGLE_TOKEN_JSON on Render:\n")
print(creds.to_json())
