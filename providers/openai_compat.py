from typing import List
import time

import requests

from .base import Message, Provider, ProviderError

# Status yang layak dicoba ulang sekali: limit sementara dan gangguan server.
RETRY_STATUS = (429, 500, 502, 503, 504)


class OpenAICompatProvider(Provider):
    """Satu kelas untuk semua provider berformat OpenAI: Groq, OpenRouter, Requesty, Aion, xKiro."""

    def __init__(self, name: str, base_url: str, api_key: str, timeout: int = 60,
                 attempts: int = 2):
        self.name = name
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.attempts = max(1, attempts)

    def available(self) -> bool:
        return bool(self.api_key and self.base_url)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs):
        """Kirim request dengan satu percobaan ulang untuk error sementara."""
        url = f"{self.base_url}{path}"
        last_error = None
        for attempt in range(self.attempts):
            try:
                r = requests.request(method, url, headers=self._headers(),
                                     timeout=self.timeout, **kwargs)
            except requests.RequestException as e:
                last_error = ProviderError(f"{self.name}: koneksi gagal ({e.__class__.__name__})")
                if attempt + 1 < self.attempts:
                    time.sleep(1)
                    continue
                raise last_error
            if r.status_code in RETRY_STATUS and attempt + 1 < self.attempts:
                try:
                    wait = float(r.headers.get("Retry-After", ""))
                except ValueError:
                    wait = 1.5
                time.sleep(min(max(wait, 0.5), 5.0))
                continue
            return r
        raise last_error or ProviderError(f"{self.name}: permintaan gagal")

    def chat(self, model: str, messages: List[Message], temperature: float = 0.7,
             max_tokens: int = 1500) -> str:
        if not model:
            raise ProviderError(f"{self.name}: model belum diisi")
        payload = {"model": model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        if self.name == "groq" and "gpt-oss" in model:
            payload["reasoning_effort"] = "low"  # cegah token habis dipakai "berpikir"

        r = self._request("POST", "/chat/completions", json=payload)
        if r.status_code != 200:
            raise ProviderError(f"{self.name}: HTTP {r.status_code} {r.text[:200]}", r.status_code)
        try:
            data = r.json()
            return data["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            raise ProviderError(f"{self.name}: format respons tidak dikenali")

    def list_models(self) -> List[str]:
        r = self._request("GET", "/models")
        if r.status_code != 200:
            raise ProviderError(f"{self.name}: HTTP {r.status_code} {r.text[:200]}", r.status_code)
        try:
            return sorted(str(m["id"]) for m in r.json().get("data", []) if m.get("id"))
        except (KeyError, ValueError, AttributeError, TypeError):
            raise ProviderError(f"{self.name}: format daftar model tidak dikenali")
