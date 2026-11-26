"""Penyimpanan proyek BUILD: snapshot status node/langkah antar-muat ulang halaman.

Supabase (tabel `build_projects`) adalah penyimpanan utama — pola REST/PostgREST
yang sama dengan build/limits.py, tanpa paket tambahan. Bila Supabase belum
dikonfigurasi atau gagal dijangkau, snapshot jatuh ke memori proses (bertahan
selama server hidup; sesi baru memulai proyek kosong).

Snapshot HANYA berisi data UI yang sudah ada di session state (bukan angka jatah).
Satu proyek aktif per user_key (tulis terakhir menang).
"""
import json
import re
from datetime import datetime, timezone
from typing import Optional, Tuple
from urllib.parse import quote

import requests

import config

# Kunci session state yang ikut disimpan/dipulihkan.
PROJECT_FIELDS = (
    "build_step", "build_request", "build_request_input", "build_ref_options",
    "build_ref_extra", "build_ref_reason", "build_ai_ranked", "build_refs_pick",
    "build_ref_custom", "build_ai_decide", "build_refs", "build_form_pick",
    "build_form_kind", "build_result", "build_log", "build_error",
    "build_attempts", "build_finished_at", "build_project_id", "build_started_at",
)


class ProjectStoreError(Exception):
    """Gagal membaca/menulis snapshot proyek (jaringan atau konfigurasi Supabase)."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_table(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""))


class MemoryProjectStore:
    """Fallback memori (uji + saat Supabase tidak tersedia)."""

    def __init__(self):
        self._rows = {}

    def load(self, user_key: str) -> Optional[dict]:
        row = self._rows.get(str(user_key))
        if not row:
            return None
        try:
            data = json.loads(row.get("data") or "{}")
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def save(self, user_key: str, data: dict) -> None:
        self._rows[str(user_key)] = {
            "user_key": str(user_key),
            "data": json.dumps(data, ensure_ascii=False),
            "updated_at": _now_iso(),
        }


class SupabaseProjectStore:
    """Klien PostgREST minimal untuk tabel `build_projects` (lihat README untuk SQL)."""

    def __init__(self, url: str, key: str, table: str = "build_projects", timeout: int = 15):
        self.url = (url or "").rstrip("/")
        self.key = (key or "").strip()
        self.table = table or "build_projects"
        self.timeout = timeout
        if not self.url or not self.key:
            raise ProjectStoreError("SUPABASE_URL atau SUPABASE_KEY belum diisi.")
        if not _valid_table(self.table):
            raise ProjectStoreError("Nama tabel Supabase tidak valid.")

    def _headers(self) -> dict:
        return {"apikey": self.key, "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json"}

    def load(self, user_key: str) -> Optional[dict]:
        endpoint = (f"{self.url}/rest/v1/{self.table}"
                    f"?user_key=eq.{quote(str(user_key), safe='')}&select=data")
        try:
            response = requests.get(endpoint, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise ProjectStoreError(
                f"koneksi Supabase gagal ({exc.__class__.__name__})") from None
        if response.status_code != 200:
            raise ProjectStoreError(f"Supabase HTTP {response.status_code}")
        try:
            rows = response.json()
        except ValueError:
            raise ProjectStoreError("respons Supabase bukan JSON") from None
        if not isinstance(rows, list) or not rows:
            return None
        raw = rows[0].get("data") if isinstance(rows[0], dict) else None
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                return None
        return raw if isinstance(raw, dict) else None

    def save(self, user_key: str, data: dict) -> None:
        endpoint = f"{self.url}/rest/v1/{self.table}"
        headers = dict(self._headers())
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        payload = {"user_key": str(user_key),
                   "data": json.dumps(data, ensure_ascii=False),
                   "updated_at": _now_iso()}
        try:
            response = requests.post(endpoint, json=payload, headers=headers,
                                     timeout=self.timeout)
        except requests.RequestException as exc:
            raise ProjectStoreError(
                f"koneksi Supabase gagal ({exc.__class__.__name__})") from None
        if response.status_code not in (200, 201):
            raise ProjectStoreError(f"Supabase HTTP {response.status_code}")


_MEMORY = MemoryProjectStore()


def get_store():
    """SupabaseProjectStore bila SUPABASE_URL + SUPABASE_KEY tersedia, selain itu None."""
    url = config.get_secret("SUPABASE_URL")
    key = config.get_secret("SUPABASE_KEY") or config.get_secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    table = config.get_secret("BUILD_PROJECTS_TABLE") or "build_projects"
    try:
        return SupabaseProjectStore(url, key, table)
    except ProjectStoreError:
        return None


def load_project(user_key: str) -> Tuple[Optional[dict], Optional[str]]:
    """(snapshot|None, error_tampilan|None). Supabase gagal → jatuh ke memori."""
    _MEMORY_SAVE = None  # noqa: F841 — dokumentasi alur
    active = get_store()
    if active is not None:
        try:
            data = active.load(user_key)
            if data is not None:
                _MEMORY.save(user_key, data)
            return data, None
        except ProjectStoreError as exc:
            return _MEMORY.load(user_key), str(exc)
    return _MEMORY.load(user_key), None


def save_project(user_key: str, data: dict) -> Optional[str]:
    """Simpan snapshot (memori selalu; Supabase best-effort). Kembalikan error bila ada."""
    _MEMORY.save(user_key, data)
    active = get_store()
    if active is None:
        return None
    try:
        active.save(user_key, data)
        return None
    except ProjectStoreError as exc:
        return str(exc)


def snapshot_from(ss) -> dict:
    """Ambil field proyek dari session state (hanya yang ada)."""
    snap = {}
    for key in PROJECT_FIELDS:
        try:
            if key in ss:
                snap[key] = ss[key]
        except Exception:
            continue
    # Objek tak-JSON (jarang) dibuang agar snapshot selalu serializable.
    try:
        json.dumps(snap, ensure_ascii=False)
    except (TypeError, ValueError):
        for key in list(snap):
            try:
                json.dumps(snap[key], ensure_ascii=False)
            except (TypeError, ValueError):
                snap.pop(key, None)
    return snap


def restore_into(ss, data: dict) -> None:
    """Isi session state dari snapshot — hanya kunci yang belum terisi di sesi ini."""
    if not isinstance(data, dict):
        return
    for key in PROJECT_FIELDS:
        if key in data and key not in ss:
            try:
                ss[key] = data[key]
            except Exception:
                pass
