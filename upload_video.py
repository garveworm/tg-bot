#!/usr/bin/env python3

import json
import os
import time
import random

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# OAuth scope for uploading videos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 10

TOKEN_FILE = "token.json"


def get_authenticated_service():
    creds = None

    # Prefer env var (for deployed environments like Render)
    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    elif os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds:
        raise RuntimeError(
            "No credentials found. Set GOOGLE_TOKEN_JSON env var or provide token.json."
        )

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                raise RuntimeError(
                    f"Token refresh failed ({e}). "
                    "Run gen_token.py locally to get a new token, "
                    "then update GOOGLE_TOKEN_JSON on Render."
                ) from e
            # Persist refreshed token locally when running with a file
            if not os.environ.get("GOOGLE_TOKEN_JSON"):
                with open(TOKEN_FILE, "w") as f:
                    f.write(creds.to_json())
        else:
            raise RuntimeError(
                "Credentials are invalid and cannot be refreshed. "
                "Run gen_token.py locally and update GOOGLE_TOKEN_JSON."
            )

    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, file, title, description, category, keywords, privacy):
    tags = keywords.split(",") if keywords else None

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category
        },
        "status": {
            "privacyStatus": privacy
        }
    }

    media = MediaFileUpload(file, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    return resumable_upload(request)


def resumable_upload(request):
    response = None
    retry = 0

    while response is None:
        try:
            print("Uploading...")
            status, response = request.next_chunk()

            if response is not None:
                print("Upload complete! Video ID:", response["id"])
                return f'Upload complete! Video ID: {response["id"]}'

        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                print("Retriable error:", e)
            else:
                raise

        retry += 1
        if retry > MAX_RETRIES:
            raise Exception("Upload failed after multiple retries.")

        sleep = random.random() * (2 ** retry)
        print(f"Retrying in {sleep:.1f} seconds...")
        time.sleep(sleep)


if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--file", required=True)
    # parser.add_argument("--title", default="Test Title")
    # parser.add_argument("--description", default="Test Description")
    # parser.add_argument("--category", default="22")
    # parser.add_argument("--keywords", default="")
    # parser.add_argument("--privacy", default="public",
    #                     choices=["public", "private", "unlisted"])
    #
    # args = parser.parse_args()
    #
    # if not os.path.exists(args.file):
    #     raise Exception("File does not exist.")

    youtube = get_authenticated_service()
    # upload_video(
    #     youtube,
    #     file=args.file,
    #     title=args.title,
    #     description=args.description,
    #     category=args.category,
    #     keywords=args.keywords,
    #     privacy=args.privacy
    # )
