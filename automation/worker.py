"""Headless worker invoked by GitHub Actions; safe to run repeatedly for one local date."""
from __future__ import annotations

import os
import sys
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from automation.director import DirectorError, create_daily_brief
from automation.store import StoreError, SupabaseStore
from automation.video_provider import CreditUnavailable, ProviderNotReady, VideoGenerationError


def _local_now(job: dict) -> datetime:
    try:
        zone = ZoneInfo(job.get("timezone") or "Asia/Jakarta")
    except Exception:
        zone = ZoneInfo("Asia/Jakarta")
    return datetime.now(zone)


def _scheduled_time(value: str) -> time:
    try:
        hh, mm = str(value or "08:00").split(":")[:2]
        return time(int(hh), int(mm))
    except Exception:
        return time(8, 0)


def run_once() -> int:
    try:
        store = SupabaseStore.from_env()
        job = store.get_active_job()
    except StoreError as exc:
        print(f"SETUP_ERROR: {exc}")
        return 2
    if not job:
        print("No active video_jobs row. Save a creator instruction from AOGx first.")
        return 0

    now = _local_now(job)
    date_key = now.date().isoformat()
    job_key = job.get("job_key", "main")
    upload_started = False
    try:
        run = store.get_run(job_key, date_key)
        if now.time().replace(tzinfo=None) < _scheduled_time(job.get("scheduled_time", "08:00")) and not run:
            print(f"Not time yet: scheduled {job.get('scheduled_time')} {job.get('timezone')}.")
            return 0

        if run and run.get("status") in ("uploaded", "uploading", "awaiting_review"):
            print(f"Today's run already has terminal/safety status: {run.get('status')}.")
            return 0
        if run and run.get("status") == "waiting_provider" and not os.getenv("VIDEO_PROVIDER"):
            print("Prompt exists; waiting for an authorized VIDEO_PROVIDER adapter.")
            return 0
        if run and run.get("status") == "waiting_credit":
            retry_after = run.get("retry_after")
            if retry_after:
                try:
                    if datetime.fromisoformat(retry_after.replace("Z", "+00:00")) > datetime.now(timezone.utc):
                        print(f"Provider credit wait until {retry_after}.")
                        return 0
                except ValueError:
                    pass

        store.save_run(job_key, date_key, status="preparing", error=None)
        if run and run.get("prompt") and run.get("title"):
            brief = {
                "video_prompt": run.get("prompt"),
                "title": run.get("title"),
                "description": run.get("description") or "",
            }
        else:
            from core.router import Router
            brief = create_daily_brief(Router(), job["instruction"], date_key)
            store.save_run(job_key, date_key, status="prompt_ready", prompt=brief["video_prompt"],
                           title=brief["title"], description=brief["description"], error=None)

        # Check OAuth before consuming video-generation credits.
        client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
        refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
        if not (client_id and client_secret and refresh_token):
            store.save_run(job_key, date_key, status="awaiting_youtube_oauth",
                           error="Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN in GitHub Actions secrets.")
            print("YouTube background OAuth secrets are missing; generation was not started.")
            return 1

        # Validate the long-lived OAuth refresh token before spending video credits.
        from providers import youtube
        try:
            youtube.refresh_access_token(client_id, client_secret, refresh_token)
        except Exception as exc:
            store.save_run(job_key, date_key, status="awaiting_youtube_oauth",
                           error=f"YouTube OAuth preflight failed ({exc.__class__.__name__}); reconnect and update the refresh-token secret.")
            print("YouTube OAuth preflight failed; generation was not started.")
            return 1

        try:
            from automation.video_provider import generate_video
            generated = generate_video(brief["video_prompt"], duration_seconds=20, aspect_ratio="9:16")
        except ProviderNotReady as exc:
            store.save_run(job_key, date_key, status="waiting_provider", error=str(exc), retry_after=None)
            print(str(exc))
            return 0
        except CreditUnavailable as exc:
            retry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            store.save_run(job_key, date_key, status="waiting_credit", error=str(exc), retry_after=retry)
            print(f"Credits/quota unavailable; retry after {retry}.")
            return 0
        except VideoGenerationError as exc:
            retry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            store.save_run(job_key, date_key, status="failed", error=str(exc), retry_after=retry)
            print(str(exc))
            return 1

        # A concrete authorized adapter must return the completed video as bytes.
        video_bytes = generated.get("video_bytes") if isinstance(generated, dict) else None
        filename = generated.get("filename", "aogx-short.mp4") if isinstance(generated, dict) else "aogx-short.mp4"
        if not isinstance(video_bytes, (bytes, bytearray)) or not video_bytes:
            store.save_run(job_key, date_key, status="failed",
                           error="Provider adapter must return non-empty video_bytes.", retry_after=None)
            return 1

        # Mark uploading before calling YouTube. If the connection drops at the end,
        # do not blindly retry and accidentally publish a duplicate; reconcile manually.
        store.save_run(job_key, date_key, status="uploading", error=None, retry_after=None)
        upload_started = True
        tokens = youtube.refresh_access_token(client_id, client_secret, refresh_token)
        access_token = tokens.get("access_token", "")
        if not access_token:
            raise RuntimeError("Google token refresh did not return an access token.")
        privacy = os.getenv("YOUTUBE_PRIVACY", "public").lower()
        if privacy not in {"public", "unlisted", "private"}:
            privacy = "public"
        result = youtube.upload_video(access_token, bytes(video_bytes), filename,
                                      brief["title"], brief["description"], privacy=privacy)
        store.save_run(job_key, date_key, status="uploaded", video_url=result["url"],
                       youtube_video_id=result["id"], error=None, retry_after=None)
        print(f"Uploaded: {result['url']}")
        return 0
    except (StoreError, DirectorError) as exc:
        try:
            if upload_started:
                store.save_run(job_key, date_key, status="uploading",
                               error=f"Upload outcome uncertain ({exc.__class__.__name__}); verify YouTube Studio before retrying.")
            else:
                store.save_run(job_key, date_key, status="failed", error=str(exc))
        except Exception:
            pass
        print(f"WORKER_ERROR: {exc}")
        return 1
    except Exception as exc:
        try:
            if upload_started:
                # YouTube may have accepted the upload before a network failure.
                # Keep the run non-retryable until the owner checks YouTube Studio.
                store.save_run(job_key, date_key, status="uploading",
                               error=f"Upload outcome uncertain ({exc.__class__.__name__}); verify YouTube Studio before retrying.")
            else:
                store.save_run(job_key, date_key, status="failed",
                               error=f"Unexpected {exc.__class__.__name__}")
        except Exception:
            pass
        print(f"WORKER_ERROR: unexpected {exc.__class__.__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(run_once())
