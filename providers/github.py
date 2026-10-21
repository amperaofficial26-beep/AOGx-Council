"""GitHub REST helpers for reviewing AI edits and publishing them as a pull request."""
import base64
import re
from urllib.parse import quote

import requests


API_ROOT = "https://api.github.com"


class GitHubError(Exception):
    """Sanitized error returned by GitHub operations."""


class GitHubClient:
    def __init__(self, token: str, timeout: int = 30):
        self.token = (token or "").strip()
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs):
        if not self.token:
            raise GitHubError("GitHub token belum dikonfigurasi.")
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
            # Jangan tampilkan body mentah: mungkin memuat informasi sensitif dari server.
            raise GitHubError(f"GitHub API gagal (HTTP {response.status_code}).")
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            raise GitHubError("Respons GitHub tidak valid.") from None

    @staticmethod
    def validate_repo(repo: str) -> str:
        repo = (repo or "").strip().strip("/")
        parts = repo.split("/")
        if (len(parts) != 2 or any(part in ("", ".", "..") for part in parts)
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)):
            raise GitHubError("Format repositori harus owner/nama-repo.")
        return repo

    def list_files(self, repo: str, branch: str):
        repo = self.validate_repo(repo)
        branch = (branch or "").strip()
        if not branch or len(branch) > 200:
            raise GitHubError("Nama branch dasar tidak valid.")
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
                            body: str, changes: dict, modes: dict | None = None):
        """Commit perubahan sebagai satu commit, buat branch baru, lalu buka PR."""
        repo = self.validate_repo(repo)
        if not changes:
            raise GitHubError("Tidak ada perubahan untuk dikirim.")
        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,180}", branch or "") or ".." in branch:
            raise GitHubError("Nama branch baru tidak valid.")
        if not title.strip():
            raise GitHubError("Judul pull request wajib diisi.")
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
        return {"number": pr["number"], "url": pr["html_url"], "branch": branch}github.py
