"""GitHub REST helpers for OAuth login, repository discovery, and reviewed PR publishing."""
import base64
import hashlib
import hmac
import re
import secrets
import time
from typing import Optional
from urllib.parse import quote

import requests


API_ROOT = "https://api.github.com"
OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"


class GitHubError(Exception):
    """Sanitized error returned by GitHub operations."""


def make_oauth_state(client_secret: str) -> str:
    """Create a short-lived, signed OAuth state value that survives a redirect."""
    if not client_secret:
        raise GitHubError("GITHUB_CLIENT_SECRET belum dikonfigurasi.")
    issued_at = str(int(time.time()))
    nonce = secrets.token_urlsafe(24)
    payload = f"{issued_at}.{nonce}"
    signature = hmac.new(client_secret.encode("utf-8"), payload.encode("utf-8"),
                         hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_oauth_state(state: str, client_secret: str, max_age: int = 600) -> bool:
    """Validate state signature and ten-minute expiry without relying on browser session state."""
    if not state or not client_secret:
        return False
    try:
        issued_at, nonce, signature = state.split(".", 2)
        timestamp = int(issued_at)
    except (ValueError, TypeError):
        return False
    age = time.time() - timestamp
    if not nonce or age < -60 or age > max_age:
        return False
    payload = f"{issued_at}.{nonce}"
    expected = hmac.new(client_secret.encode("utf-8"), payload.encode("utf-8"),
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def exchange_oauth_code(client_id: str, client_secret: str, code: str,
                        redirect_uri: Optional[str] = None) -> str:
    """Exchange a GitHub OAuth authorization code for a user access token."""
    if not client_id or not client_secret or not code:
        raise GitHubError("Konfigurasi OAuth GitHub tidak lengkap.")
    payload = {"client_id": client_id, "client_secret": client_secret, "code": code}
    if redirect_uri:
        payload["redirect_uri"] = redirect_uri
    try:
        response = requests.post(
            OAUTH_TOKEN_URL,
            data=payload,
            headers={"Accept": "application/json"},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise GitHubError(f"Koneksi OAuth GitHub gagal ({exc.__class__.__name__}).") from None
    if not 200 <= response.status_code < 300:
        raise GitHubError(f"Pertukaran kode OAuth gagal (HTTP {response.status_code}).")
    try:
        data = response.json()
    except ValueError:
        raise GitHubError("Respons OAuth GitHub tidak valid.") from None
    if data.get("error") or not data.get("access_token"):
        # Don't surface raw server responses or credentials in the UI.
        message = data.get("error_description") or data.get("error") or "kode tidak dapat ditukar"
        raise GitHubError(f"Login GitHub gagal: {str(message)[:160]}.")
    return str(data["access_token"])


class GitHubClient:
    def __init__(self, token: str, timeout: int = 30):
        self.token = (token or "").strip()
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs):
        if not self.token:
            raise GitHubError("Akun GitHub belum terhubung.")
        try:
            response = requests.request(
                method, f"{API_ROOT}/{path.lstrip('/')}",
                headers={"Authorization": f"Bearer {self.token}",
                         "Accept": "application/vnd.github+json",
                         "X-GitHub-Api-Version": "2022-11-28"},
                timeout=self.timeout, **kwargs,
            )
        except requests.RequestException as exc:
            raise GitHubError(f"Koneksi GitHub gagal ({exc.__class__.__name__}).") from None
        if not 200 <= response.status_code < 300:
            if response.status_code == 401:
                raise GitHubError("Token GitHub tidak berlaku atau telah dicabut. Hubungkan akun lagi.")
            if response.status_code == 403:
                raise GitHubError("GitHub menolak akses. Periksa izin akun, organisasi, atau batas API.")
            if response.status_code == 404:
                raise GitHubError("Repositori, branch, atau file tidak ditemukan atau tidak dapat diakses.")
            raise GitHubError(f"GitHub API gagal (HTTP {response.status_code}).")
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            raise GitHubError("Respons GitHub tidak valid.") from None

    def get_authenticated_user(self) -> dict:
        """Return only identity fields needed by the UI."""
        data = self._request("GET", "user")
        if not data.get("login"):
            raise GitHubError("GitHub tidak mengembalikan identitas akun yang valid.")
        return {"login": str(data["login"]), "name": str(data.get("name") or data["login"]),
                "avatar_url": str(data.get("avatar_url") or ""),
                "html_url": str(data.get("html_url") or "")}

    def list_user_repositories(self) -> list:
        """List repositories the authenticated user can access, including private/org repos."""
        repositories = []
        page = 1
        while True:
            batch = self._request(
                "GET", "user/repos",
                params={"visibility": "all",
                        "affiliation": "owner,collaborator,organization_member",
                        "sort": "updated", "direction": "desc",
                        "per_page": 100, "page": page},
            )
            if not isinstance(batch, list):
                raise GitHubError("Daftar repositori dari GitHub tidak valid.")
            repositories.extend(batch)
            if len(batch) < 100:
                break
            page += 1
            # Prevent accidental unbounded API loops for accounts with very many repositories.
            if page > 50:
                break
        cleaned = []
        for item in repositories:
            if not isinstance(item, dict) or not item.get("full_name"):
                continue
            permissions = item.get("permissions") or {}
            cleaned.append({
                "full_name": str(item["full_name"]),
                "name": str(item.get("name") or item["full_name"]),
                "private": bool(item.get("private")),
                "archived": bool(item.get("archived")),
                "disabled": bool(item.get("disabled")),
                "default_branch": str(item.get("default_branch") or "main"),
                "description": str(item.get("description") or ""),
                "html_url": str(item.get("html_url") or ""),
                "updated_at": str(item.get("updated_at") or ""),
                "permissions": {"admin": bool(permissions.get("admin")),
                                "push": bool(permissions.get("push")),
                                "pull": bool(permissions.get("pull"))},
            })
        return cleaned

    def list_branches(self, repo: str) -> list:
        """List branch names for a selected repository."""
        repo = self.validate_repo(repo)
        branches, page = [], 1
        while True:
            batch = self._request("GET", f"repos/{repo}/branches",
                                  params={"per_page": 100, "page": page})
            if not isinstance(batch, list):
                raise GitHubError("Daftar branch dari GitHub tidak valid.")
            branches.extend(str(item["name"]) for item in batch
                            if isinstance(item, dict) and item.get("name"))
            if len(batch) < 100:
                break
            page += 1
            if page > 50:
                break
        return branches

    @staticmethod
    def validate_repo(repo: str) -> str:
        repo = (repo or "").strip().strip("/")
        parts = repo.split("/")
        if (len(parts) != 2 or any(part in ("", ".", "..") for part in parts)
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)):
            raise GitHubError("Repositori GitHub yang dipilih tidak valid.")
        return repo

    def list_files(self, repo: str, branch: str):
        repo = self.validate_repo(repo)
        branch = (branch or "").strip()
        if not branch or len(branch) > 200:
            raise GitHubError("Branch dasar tidak valid.")
        ref = self._request("GET", f"repos/{repo}/git/ref/heads/{quote(branch, safe='')}")
        commit_sha = ref["object"]["sha"]
        commit = self._request("GET", f"repos/{repo}/git/commits/{commit_sha}")
        tree_sha = commit["tree"]["sha"]
        tree = self._request("GET", f"repos/{repo}/git/trees/{tree_sha}", params={"recursive": "1"})
        if tree.get("truncated"):
            raise GitHubError("Daftar file repositori terlalu besar; pilih repositori yang lebih kecil.")
        return [item for item in tree.get("tree", [])
                if item.get("type") == "blob" and item.get("size", 0) <= 200_000]

    def get_text_file(self, repo: str, path: str, branch: str) -> str:
        repo = self.validate_repo(repo)
        if not path or path.startswith("/") or ".." in path.split("/"):
            raise GitHubError("Path file tidak valid.")
        result = self._request("GET", f"repos/{repo}/contents/{quote(path, safe='/')}",
                               params={"ref": branch})
        if result.get("encoding") != "base64" or result.get("size", 0) > 200_000:
            raise GitHubError(f"File {path} bukan file teks yang didukung atau terlalu besar.")
        try:
            return base64.b64decode(result["content"]).decode("utf-8")
        except (KeyError, ValueError, UnicodeDecodeError):
            raise GitHubError(f"File {path} tidak dapat dibaca sebagai teks UTF-8.") from None

    def create_pull_request(self, repo: str, base: str, branch: str, title: str,
                            body: str, changes: dict, modes: Optional[dict] = None):
        """Commit reviewed changes as one commit, create a branch, and open a PR."""
        repo = self.validate_repo(repo)
        if not changes:
            raise GitHubError("Tidak ada perubahan untuk dikirim.")
        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,180}", branch or "") or ".." in branch:
            raise GitHubError("Nama branch baru tidak valid.")
        if not title.strip():
            raise GitHubError("Judul Pull Request wajib diisi.")
        ref = self._request("GET", f"repos/{repo}/git/ref/heads/{quote(base, safe='')}")
        parent_sha = ref["object"]["sha"]
        parent = self._request("GET", f"repos/{repo}/git/commits/{parent_sha}")
        tree_items = []
        for path, content in changes.items():
            if not path or path.startswith("/") or ".." in path.split("/"):
                raise GitHubError("Perubahan berisi path file yang tidak valid.")
            blob = self._request("POST", f"repos/{repo}/git/blobs", json={
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "encoding": "base64",
            })
            tree_items.append({"path": path, "mode": (modes or {}).get(path, "100644"),
                              "type": "blob", "sha": blob["sha"]})
        tree = self._request("POST", f"repos/{repo}/git/trees", json={
            "base_tree": parent["tree"]["sha"], "tree": tree_items,
        })
        commit = self._request("POST", f"repos/{repo}/git/commits", json={
            "message": title.strip()[:120], "tree": tree["sha"], "parents": [parent_sha],
        })
        self._request("POST", f"repos/{repo}/git/refs", json={
            "ref": f"refs/heads/{branch}", "sha": commit["sha"],
        })
        pr = self._request("POST", f"repos/{repo}/pulls", json={
            "title": title.strip()[:250], "head": branch, "base": base,
            "body": body.strip()[:60_000],
        })
        return {"number": pr["number"], "url": pr["html_url"], "branch": branch}
