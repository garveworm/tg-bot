#!/usr/bin/env python3

import os
import time
import random
import argparse

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# OAuth scope for uploading videos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 10


def get_authenticated_service():
    creds = None

    # Token is stored locally after first auth
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If not authenticated, do OAuth login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secrets.json", SCOPES)
            creds = flow.run_local_server(port=8080)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

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

    resumable_upload(request)


def resumable_upload(request):
    response = None
    retry = 0

    while response is None:
        try:
            print("Uploading...")
            status, response = request.next_chunk()

            if response is not None:
                print("Upload complete! Video ID:", response["id"])
                return

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
