import re
import time
from typing import List

import requests

from .base import Message, Provider, ProviderError

RETRY_STATUS = (429, 500, 502, 503, 504)
API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, api_key: str, timeout: int = 90, attempts: int = 2):
        self.api_key = api_key
        self.timeout = timeout
        self.attempts = max(1, attempts)

    def available(self) -> bool:
        return bool(self.api_key)

    def _request(self, method: str, url: str, **kwargs):
        """Request dengan satu percobaan ulang untuk limit sementara / gangguan server."""
        last_error = None
        for attempt in range(self.attempts):
            try:
                r = requests.request(method, url, headers={"x-goog-api-key": self.api_key,
                                                           "Content-Type": "application/json"},
                                     timeout=self.timeout, **kwargs)
            except requests.RequestException as e:
                last_error = ProviderError(f"gemini: koneksi gagal ({e.__class__.__name__})")
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
        raise last_error or ProviderError("gemini: permintaan gagal")

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
        # Gemini 3 Flash memakai token "berpikir" dari jatah maxOutputTokens. Level "low"
        # membuat jawaban pendek (verifier/orchestrator) tidak habis sebelum selesai.
        thinking = bool(re.match(r"gemini-3(\.\d+)?-flash", model))
        if thinking:
            body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "low"}
        if system_parts:
            body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        url = f"{API_ROOT}/models/{model}:generateContent"
        r = self._request("POST", url, json=body)
        # Sebagian model/versi API menolak thinkingConfig: ulangi tanpa config itu.
        if r.status_code == 400 and thinking and "thinking" in r.text.lower():
            body["generationConfig"].pop("thinkingConfig", None)
            r = self._request("POST", url, json=body)
        if r.status_code != 200:
            raise ProviderError(f"gemini: HTTP {r.status_code} {r.text[:200]}", r.status_code)

        try:
            data = r.json()
        except ValueError:
            raise ProviderError("gemini: respons bukan JSON")

        feedback = data.get("promptFeedback") or {}
        if feedback.get("blockReason"):
            raise ProviderError(f"gemini: prompt diblokir ({feedback['blockReason']})")

        try:
            candidate = data["candidates"][0]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("gemini: respons kosong atau diblokir")

        finish = candidate.get("finishReason") or ""
        parts = (candidate.get("content") or {}).get("parts") or []
        # Bagian bertanda thought adalah proses berpikir, bukan jawaban.
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))

        if not text.strip():
            if finish == "MAX_TOKENS":
                raise ProviderError("gemini: token habis sebelum jawaban selesai "
                                    "(naikkan max_tokens atau pakai model lain)")
            if finish in ("SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST"):
                raise ProviderError(f"gemini: jawaban diblokir ({finish})")
            raise ProviderError(f"gemini: jawaban kosong (finishReason={finish or 'tidak ada'})")
        return text

    def list_models(self) -> List[str]:
        r = self._request("GET", f"{API_ROOT}/models", params={"pageSize": 200})
        if r.status_code != 200:
            raise ProviderError(f"gemini: HTTP {r.status_code} {r.text[:200]}", r.status_code)
        try:
            models = r.json().get("models", [])
        except ValueError:
            raise ProviderError("gemini: format daftar model tidak dikenali")
        out = []
        for m in models:
            if "generateContent" in m.get("supportedGenerationMethods", []):
                out.append(m.get("name", "").replace("models/", ""))
        return sorted(x for x in out if x)
