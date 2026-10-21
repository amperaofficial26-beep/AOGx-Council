from typing import Dict, List
import requests

from .base import ProviderError


class TavilySearch:
    name = "tavily"

    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Kembalikan daftar {title, url, content}. Isi web = data tidak tepercaya."""
        try:
            r = requests.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json={"query": query, "max_results": max_results, "search_depth": "basic"},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise ProviderError(f"tavily: koneksi gagal ({e.__class__.__name__})")
        if r.status_code != 200:
            raise ProviderError(f"tavily: HTTP {r.status_code}", r.status_code)
        results = r.json().get("results", [])
        return [{"title": x.get("title", ""), "url": x.get("url", ""),
                 "content": x.get("content", "")} for x in results]
