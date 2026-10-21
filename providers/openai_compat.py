from typing import List
import requests

from .base import Message, Provider, ProviderError


class OpenAICompatProvider(Provider):
    """Satu kelas untuk semua provider berformat OpenAI: Groq, OpenRouter, Requesty, Aion, xKiro."""

    def __init__(self, name: str, base_url: str, api_key: str, timeout: int = 60):
        self.name = name
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key and self.base_url)

    def chat(self, model: str, messages: List[Message], temperature: float = 0.7,
             max_tokens: int = 1500) -> str:
        if not model:
            raise ProviderError(f"{self.name}: model belum diisi")
        payload = {"model": model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        if self.name == "groq" and "gpt-oss" in model:
            payload["reasoning_effort"] = "low"  # cegah token habis dipakai "berpikir"
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise ProviderError(f"{self.name}: koneksi gagal ({e.__class__.__name__})")
        if r.status_code != 200:
            raise ProviderError(f"{self.name}: HTTP {r.status_code} {r.text[:200]}", r.status_code)
        try:
            return r.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, ValueError):
            raise ProviderError(f"{self.name}: format respons tidak dikenali")

    def list_models(self) -> List[str]:
        try:
            r = requests.get(f"{self.base_url}/models",
                             headers={"Authorization": f"Bearer {self.api_key}"},
                             timeout=self.timeout)
        except requests.RequestException as e:
            raise ProviderError(f"{self.name}: koneksi gagal ({e.__class__.__name__})")
        if r.status_code != 200:
            raise ProviderError(f"{self.name}: HTTP {r.status_code} {r.text[:200]}", r.status_code)
        try:
            return sorted(str(m["id"]) for m in r.json().get("data", []) if m.get("id"))
        except (KeyError, ValueError, AttributeError):
            raise ProviderError(f"{self.name}: format daftar model tidak dikenali")
