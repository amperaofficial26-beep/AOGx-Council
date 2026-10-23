"""Small Supabase REST store for persistent video jobs and daily runs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests


class StoreError(RuntimeError):
    """Safe, user-facing persistence error."""


class SupabaseStore:
    def __init__(self, url: str, service_key: str, timeout: int = 20):
        self.url = url.rstrip("/")
        self.service_key = service_key.strip()
        self.timeout = timeout
        if not self.url.startswith("https://") or not self.service_key:
            raise StoreError("SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY harus diisi.")

    @classmethod
    def from_env(cls):
        import os
        return cls(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))

    def _request(self, method: str, table: str, *, params=None, json=None, prefer=None):
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        try:
            response = requests.request(
                method, f"{self.url}/rest/v1/{table}", headers=headers,
                params=params, json=json, timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise StoreError(f"Database tidak dapat dijangkau ({exc.__class__.__name__}).") from None
        if response.status_code >= 400:
            raise StoreError(f"Supabase mengembalikan HTTP {response.status_code} untuk tabel {table}.")
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def get_job(self, job_key: str = "main") -> dict[str, Any] | None:
        rows = self._request("GET", "video_jobs", params={
            "select": "job_key,instruction,timezone,scheduled_time,active,updated_at",
            "job_key": f"eq.{job_key}", "limit": "1",
        })
        return rows[0] if rows else None

    def get_active_job(self) -> dict[str, Any] | None:
        rows = self._request("GET", "video_jobs", params={
            "select": "job_key,instruction,timezone,scheduled_time,active,updated_at",
            "active": "eq.true", "order": "updated_at.desc", "limit": "1",
        })
        return rows[0] if rows else None

    def save_job(self, instruction: str, scheduled_time: str = "08:00",
                 timezone_name: str = "Asia/Jakarta", active: bool = True) -> dict[str, Any]:
        instruction = instruction.strip()
        if not instruction:
            raise StoreError("Perintah video tidak boleh kosong.")
        payload = {
            "job_key": "main", "instruction": instruction[:6000],
            "timezone": timezone_name,
            "scheduled_time": (scheduled_time[:5] or "08:00") + ":00",
            "active": bool(active), "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        rows = self._request(
            "POST", "video_jobs", params={"on_conflict": "job_key"}, json=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return rows[0] if rows else payload

    def get_run(self, job_key: str, run_date: str) -> dict[str, Any] | None:
        rows = self._request("GET", "video_runs", params={
            "select": "*", "job_key": f"eq.{job_key}", "run_date": f"eq.{run_date}", "limit": "1",
        })
        return rows[0] if rows else None

    def save_run(self, job_key: str, run_date: str, **fields) -> dict[str, Any]:
        allowed = {
            "status", "prompt", "title", "description", "provider_job_id",
            "video_url", "error", "retry_after", "youtube_video_id",
        }
        payload = {"job_key": job_key, "run_date": run_date,
                   "updated_at": datetime.now(timezone.utc).isoformat()}
        payload.update({key: value for key, value in fields.items() if key in allowed})
        rows = self._request(
            "POST", "video_runs", params={"on_conflict": "job_key,run_date"}, json=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return rows[0] if rows else payload
