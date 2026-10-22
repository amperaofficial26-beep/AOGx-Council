"""Minimal YouTube OAuth + resumable upload helpers for AOGx-Council.

Uses Google's documented YouTube Data API. Tokens are kept in Streamlit session
state by the UI; no token is written to disk.
"""
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode

import requests

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubeError(Exception):
    """Safe, user-facing YouTube integration error."""


def make_state(client_secret: str) -> str:
    issued = str(int(time.time()))
    nonce = secrets.token_urlsafe(18)
    payload = f"yt.{issued}.{nonce}"
    sig = hmac.new(client_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_state(state: str, client_secret: str, max_age: int = 600) -> bool:
    try:
        prefix, issued, nonce, signature = state.split(".", 3)
        timestamp = int(issued)
    except (ValueError, TypeError):
        return False
    if prefix != "yt" or not nonce or time.time() - timestamp > max_age or time.time() - timestamp < -60:
        return False
    payload = f"{prefix}.{issued}.{nonce}"
    expected = hmac.new(client_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def authorization_url(client_id: str, redirect_uri: str, state: str) -> str:
    query = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    })
    return f"{AUTH_URL}?{query}"


def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    try:
        r = requests.post(TOKEN_URL, data={
            "client_id": client_id, "client_secret": client_secret,
            "code": code, "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }, timeout=25)
    except requests.RequestException as exc:
        raise YouTubeError(f"Koneksi Google gagal ({exc.__class__.__name__}).") from None
    if r.status_code != 200:
        raise YouTubeError(f"Google OAuth gagal (HTTP {r.status_code}). Periksa Client ID, secret, dan redirect URI.")
    data = r.json()
    if not data.get("access_token"):
        raise YouTubeError("Google tidak mengembalikan access token.")
    return data


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    try:
        r = requests.post(TOKEN_URL, data={
            "client_id": client_id, "client_secret": client_secret,
            "refresh_token": refresh_token, "grant_type": "refresh_token",
        }, timeout=25)
    except requests.RequestException as exc:
        raise YouTubeError(f"Koneksi Google gagal ({exc.__class__.__name__}).") from None
    if r.status_code != 200:
        raise YouTubeError(f"Token YouTube perlu dihubungkan ulang (HTTP {r.status_code}).")
    return r.json()


def upload_video(access_token: str, video_bytes: bytes, filename: str,
                 title: str, description: str, privacy: str = "public") -> dict:
    """Upload an already-reviewed MP4/WebM video using YouTube's resumable API."""
    if privacy not in {"public", "unlisted", "private"}:
        raise YouTubeError("Pilihan privasi tidak valid.")
    if not video_bytes:
        raise YouTubeError("File video kosong.")
    metadata = {
        "snippet": {
            "title": (title or "AOGx YouTube Short")[:100],
            "description": (description or "")[:5000],
            "categoryId": "22",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(len(video_bytes)),
    }
    try:
        start = requests.post(
            UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"},
            headers=headers, json=metadata, timeout=30,
        )
        if start.status_code not in (200, 201):
            raise YouTubeError(f"YouTube menolak permintaan upload (HTTP {start.status_code}).")
        upload_url = start.headers.get("Location")
        if not upload_url:
            raise YouTubeError("YouTube tidak memberikan URL upload.")
        sent = requests.put(upload_url, data=video_bytes,
                            headers={"Authorization": f"Bearer {access_token}",
                                     "Content-Type": "video/mp4",
                                     "Content-Length": str(len(video_bytes))},
                            timeout=180)
    except requests.RequestException as exc:
        raise YouTubeError(f"Upload terputus ({exc.__class__.__name__}). Cek status YouTube sebelum mencoba lagi.")
    if sent.status_code not in (200, 201):
        raise YouTubeError(f"Upload gagal (HTTP {sent.status_code}). Jangan langsung ulangi sebelum mengecek YouTube Studio.")
    data = sent.json()
    video_id = data.get("id")
    if not video_id:
        raise YouTubeError("Upload selesai tetapi ID video tidak ditemukan.")
    return {"id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}
