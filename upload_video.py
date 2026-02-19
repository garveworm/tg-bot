#!/usr/bin/env python3

import json
import logging
import os
import random
import threading
import time

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 10
TOKEN_FILE = "token.json"

# Cached service — built once, reused across requests
_service = None
_service_lock = threading.Lock()


def get_authenticated_service():
    global _service
    with _service_lock:
        if _service is None:
            _service = _build_service()
        return _service


def _build_service():
    creds = None

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
            "categoryId": category,
        },
        "status": {
            "privacyStatus": privacy,
        },
    }

    media = MediaFileUpload(file, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    return _resumable_upload(request)


def _resumable_upload(request):
    response = None
    retry = 0

    while response is None:
        try:
            logger.info("Uploading chunk...")
            status, response = request.next_chunk()
            if response is not None:
                video_id = response["id"]
                logger.info("Upload complete. Video ID: %s", video_id)
                return f"Upload complete! Video ID: {video_id}"
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                logger.warning("Retriable HTTP error %s: %s", e.resp.status, e)
            else:
                raise

        retry += 1
        if retry > MAX_RETRIES:
            raise RuntimeError("Upload failed after maximum retries.")

        sleep = random.random() * (2 ** retry)
        logger.info("Retrying in %.1f seconds... (attempt %d/%d)", sleep, retry, MAX_RETRIES)
        time.sleep(sleep)
