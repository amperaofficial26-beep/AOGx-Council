"""Jatah BUILD: dihitung per aksi BUILD, disimpan di Supabase, reset otomatis 3 hari.

Supabase adalah penyimpanan utama (REST/PostgREST lewat `requests`, tanpa paket tambahan).
Bila Supabase belum dikonfigurasi atau gagal dijangkau, penghitungan jatuh ke memori
proses dan UI menampilkan peringatan bahwa jatah tidak bertahan setelah server dimuat
ulang. Angka jatah tidak pernah disimpan di session state.
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

import requests

import config

RESET_DAYS = config.BUILD_LIMIT_RESET_DAYS  # jendela reset 3 hari
DEFAULT_MAX_BUILDS = 10

# Kalimat verifikasi wajib — teks harus persis seperti yang diminta.
LIMIT_CONFIRM_TEXT = (
    "tindakan ini akan menghabiskan jatah limit aogx anda,"
    "limit akan di reset setelah 3 hari, apakah anda ingin lanjut?"
)


class LimitStoreError(Exception):
    """Gagal membaca/menulis penyimpanan jatah (jaringan atau konfigurasi Supabase)."""


def default_max_builds() -> int:
    """Jatah BUILD per jendela 3 hari (env BUILD_LIMIT_PER_WINDOW, default 10)."""
    raw = config.get_secret("BUILD_LIMIT_PER_WINDOW")
    try:
        return max(1, int(str(raw).strip()))
    except (TypeError, ValueError):
        return DEFAULT_MAX_BUILDS


def _now(now: Optional[datetime] = None) -> datetime:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _parse_ts(value) -> Optional[datetime]:
    """Parse ISO-8601 (termasuk format Supabase 'Z'); anggap UTC bila tanpa zona."""
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()


class MemoryLimitStore:
    """Penyimpanan proses (fallback saat Supabase tidak tersedia; dipakai juga di uji)."""

    def __init__(self):
        self._rows = {}

    def load(self, user_key: str) -> Optional[dict]:
        row = self._rows.get(user_key)
        return dict(row) if row else None

    def save(self, row: dict) -> None:
        self._rows[str(row.get("user_key"))] = dict(row)


class SupabaseLimitStore:
    """Klien PostgREST minimal untuk tabel `build_limits` (lihat README untuk SQL-nya)."""

    def __init__(self, url: str, key: str, table: str = "build_limits", timeout: int = 15):
        self.url = (url or "").rstrip("/")
        self.key = (key or "").strip()
        self.table = table or "build_limits"
        self.timeout = timeout
        if not self.url or not self.key:
            raise LimitStoreError("SUPABASE_URL atau SUPABASE_KEY belum diisi.")
        if not re_fullmatch_table(self.table):
            raise LimitStoreError("Nama tabel Supabase tidak valid.")

    def _headers(self) -> dict:
        return {"apikey": self.key, "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json"}

    def load(self, user_key: str) -> Optional[dict]:
        endpoint = (f"{self.url}/rest/v1/{self.table}"
                    f"?user_key=eq.{quote(str(user_key), safe='')}&select=*")
        try:
            response = requests.get(endpoint, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise LimitStoreError(
                f"koneksi Supabase gagal ({exc.__class__.__name__})") from None
        if response.status_code != 200:
            raise LimitStoreError(f"Supabase HTTP {response.status_code}")
        try:
            rows = response.json()
        except ValueError:
            raise LimitStoreError("respons Supabase bukan JSON") from None
        if not isinstance(rows, list) or not rows:
            return None
        row = rows[0] if isinstance(rows[0], dict) else {}
        try:
            count = int(row.get("build_count") or 0)
        except (TypeError, ValueError):
            count = 0
        return {"user_key": str(row.get("user_key") or user_key),
                "build_count": max(0, count),
                "window_start": row.get("window_start") or ""}

    def save(self, row: dict) -> None:
        endpoint = f"{self.url}/rest/v1/{self.table}"
        headers = dict(self._headers())
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        payload = {"user_key": str(row.get("user_key")),
                   "build_count": int(row.get("build_count") or 0),
                   "window_start": row.get("window_start") or _iso(_now()),
                   "updated_at": _iso(_now())}
        try:
            response = requests.post(endpoint, json=payload, headers=headers,
                                     timeout=self.timeout)
        except requests.RequestException as exc:
            raise LimitStoreError(
                f"koneksi Supabase gagal ({exc.__class__.__name__})") from None
        if response.status_code not in (200, 201):
            raise LimitStoreError(f"Supabase HTTP {response.status_code}")


def re_fullmatch_table(table: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table or ""))


# Fallback memori dipakai otomatis bila Supabase belum disetel atau sedang gagal.
_MEMORY_FALLBACK = MemoryLimitStore()


def get_store():
    """SupabaseLimitStore bila SUPABASE_URL + SUPABASE_KEY tersedia, selain itu None."""
    url = config.get_secret("SUPABASE_URL")
    key = config.get_secret("SUPABASE_KEY") or config.get_secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    table = config.get_secret("BUILD_LIMITS_TABLE") or "build_limits"
    try:
        return SupabaseLimitStore(url, key, table)
    except LimitStoreError:
        return None


def _resolve_store(store=None):
    """Return (store_aktif, backend, error_tampilan)."""
    if store is not None:
        return store, ("supabase" if isinstance(store, SupabaseLimitStore) else "memory"), None
    resolved = get_store()
    if resolved is not None:
        return resolved, "supabase", None
    return _MEMORY_FALLBACK, "fallback", (
        "Supabase belum dikonfigurasi; jatah BUILD disimpan sementara di memori server "
        "dan tidak bertahan setelah aplikasi dimuat ulang.")


def _load(store, user_key: str):
    """Muat baris; bila Supabase gagal, jatuh ke memori dan kembalikan pesan error."""
    try:
        return store.load(user_key), None
    except LimitStoreError as exc:
        row = _MEMORY_FALLBACK.load(user_key)
        return row, str(exc)


def _save(store, row: dict):
    """Simpan baris; bila Supabase gagal, catat ke memori dan kembalikan pesan error."""
    if isinstance(store, SupabaseLimitStore):
        _MEMORY_FALLBACK.save(row)  # cadangan saat Supabase sedang gagal
        try:
            store.save(row)
            return None
        except LimitStoreError as exc:
            return str(exc)
    store.save(row)
    return None


def _view(row: Optional[dict], max_builds: int, now: datetime, backend: str,
          error: Optional[str]) -> dict:
    count = int((row or {}).get("build_count") or 0)
    window_start = _parse_ts((row or {}).get("window_start"))
    if window_start is None or (now - window_start) >= timedelta(days=RESET_DAYS):
        # Jendela kedaluwarsa: hitungan dianggap 0; jendela baru dimulai saat konsumsi berikutnya.
        count = 0
        window_start = None
    used = min(count, max_builds)
    reset_at = (window_start + timedelta(days=RESET_DAYS)) if (window_start and used > 0) else None
    return {"used": used, "max": max_builds, "remaining": max(0, max_builds - used),
            "reset_at": _iso(reset_at) if reset_at else None,
            "backend": backend, "error": error,
            "_window_start": window_start}


def limit_status(user_key: str, store=None, now: Optional[datetime] = None,
                 max_builds: Optional[int] = None) -> dict:
    """Baca jatah tanpa menambah. `used` sudah lewat reset jendela 3 hari bila kedaluwarsa."""
    moment = _now(now)
    limit = max_builds or default_max_builds()
    active, backend, setup_error = _resolve_store(store)
    row, load_error = _load(active, user_key)
    view = _view(row, limit, moment, backend, setup_error or load_error)
    view.pop("_window_start", None)
    return view


def limit_consume(user_key: str, store=None, now: Optional[datetime] = None,
                  max_builds: Optional[int] = None) -> dict:
    """Tambah satu aksi BUILD. `consumed=False` bila jatah habis (jendela belum reset)."""
    moment = _now(now)
    limit = max_builds or default_max_builds()
    active, backend, setup_error = _resolve_store(store)
    row, load_error = _load(active, user_key)
    view = _view(row, limit, moment, backend, setup_error or load_error)
    view["consumed"] = False
    if view["remaining"] <= 0:
        return view
    window_start = view.pop("_window_start", None) or moment
    saved = {"user_key": str(user_key), "build_count": view["used"] + 1,
             "window_start": _iso(window_start)}
    save_error = _save(active, saved)
    view = _view(saved, limit, moment, backend, view.get("error") or save_error)
    view.pop("_window_start", None)
    view["consumed"] = True
    return view
