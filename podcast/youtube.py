import json
import logging
import os

import requests
from .cache import read_cache_json, get_cache_path

logger = logging.getLogger(__name__)


def step_upload_youtube(config):
    if not config.get("is_github_run"):
        logger.info("Skipping YouTube upload for local run.")
        return

    video_path = get_cache_path(config, "video")
    if not os.path.exists(video_path):
        raise FileNotFoundError(
            f"Missing production asset target video file: {video_path}"
        )

    data = read_cache_json(config)
    if not isinstance(data, dict) or "selected" not in data:
        raise KeyError(
            "No selected paper found in cache; run the 'select' step first."
        )
    paper = data["selected"]

    logger.info("Initializing YouTube programmatic video upload sequence...")
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        logger.warning("Missing YouTube credentials in environment (.env). Skipping YouTube upload step.")
        return

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    logger.debug(f"Refreshing YouTube OAuth access token at URL: {token_url}")
    token_response = requests.post(token_url, data=token_data)
    logger.debug(f"Token Refresh Status: {token_response.status_code}")
    logger.debug(f"Token Refresh Payload: {token_response.text}")

    if token_response.status_code != 200:
        raise RuntimeError(
            f"Failed to refresh YouTube OAuth Access Token: {token_response.text}"
        )

    access_token = token_response.json().get("access_token")

    file_size = os.path.getsize(video_path)

    initiate_url = (
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status"
    )
    initiate_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": "video/mp4",
    }

    title = paper.get("title", "")
    if len(title) >= 99:
        title = title[:95] + "..."

    metadata_payload = {
        "snippet": {
            "title": title,
            "description": (
                f"{config['podcast']['show_name']}\n"
                f"{config['podcast']['show_description']}\n\n"
                f"{paper.get('id', '')}\n\n"
                f"{paper.get('selection_reason', 'AI Research Paper')}"
            ),
            "categoryId": "27",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    logger.debug(f"Sending Resumable Upload Init Request to: {initiate_url}")
    logger.debug(f"Init Request Headers: {initiate_headers}")
    logger.debug(f"Metadata JSON Body: {json.dumps(metadata_payload)}")

    initiate_response = requests.post(
        initiate_url, headers=initiate_headers, json=metadata_payload
    )
    logger.debug(f"Init Request Response Code: {initiate_response.status_code}")
    logger.debug(f"Init Request Response Headers: {initiate_response.headers}")

    initiate_response.raise_for_status()

    upload_session_url = initiate_response.headers.get("Location")
    if not upload_session_url:
        raise RuntimeError(
            "YouTube API did not return unique 'Location' session header."
        )

    logger.debug(f"Streaming video byte packet matrix to: {upload_session_url}")
    upload_headers = {
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4",
    }

    with open(video_path, "rb") as video_file:
        upload_response = requests.put(
            upload_session_url, headers=upload_headers, data=video_file
        )

    logger.debug(f"Upload Data Put Status Code: {upload_response.status_code}")
    logger.debug(f"Upload Data Put Body Response: {upload_response.text}")

    if upload_response.status_code in (200, 201):
        video_id = upload_response.json().get("id")
        logger.info(
            f"SUCCESS! Podcast video uploaded to YouTube. Video ID: {video_id}"
        )
    else:
        raise RuntimeError(
            f"Video upload failed: {upload_response.text}"
        )
