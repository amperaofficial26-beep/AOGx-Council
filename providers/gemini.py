from typing import List
import requests

from .base import Message, Provider, ProviderError


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, api_key: str, timeout: int = 90):
        self.api_key = api_key
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, model: str, messages: List[Message], temperature: float = 0.7,
             max_tokens: int = 1500) -> str:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [{"text": m["content"]}]}
            for m in messages if m["role"] != "system"
        ]
        body = {"contents": contents,
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
        if system_parts:
            body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=body, timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise ProviderError(f"gemini: koneksi gagal ({e.__class__.__name__})")
        if r.status_code != 200:
            raise ProviderError(f"gemini: HTTP {r.status_code} {r.text[:200]}", r.status_code)
        try:
            parts = r.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, ValueError):
            raise ProviderError("gemini: respons kosong atau diblokir")

    def list_models(self) -> List[str]:
        try:
            r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                             headers={"x-goog-api-key": self.api_key},
                             params={"pageSize": 200}, timeout=self.timeout)
        except requests.RequestException as e:
            raise ProviderError(f"gemini: koneksi gagal ({e.__class__.__name__})")
        if r.status_code != 200:
            raise ProviderError(f"gemini: HTTP {r.status_code} {r.text[:200]}", r.status_code)
        out = []
        for m in r.json().get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                out.append(m.get("name", "").replace("models/", ""))
        return sorted(x for x in out if x)
