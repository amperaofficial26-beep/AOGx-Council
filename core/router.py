"""Router: pilih provider per peran, fallback otomatis, dan circuit breaker sederhana."""
import threading
import time
from typing import Dict, List, Tuple

import config
from providers.base import Message, ProviderError
from providers.gemini import GeminiProvider
from providers.openai_compat import OpenAICompatProvider
from providers.tavily import TavilySearch


class AllProvidersFailed(Exception):
    pass


class Router:
    def __init__(self):
        self.providers: Dict[str, object] = {}
        for name, cfg in config.OPENAI_COMPAT.items():
            base_url = cfg["base_url"] or config.get_secret(f"{name.upper()}_BASE_URL")
            self.providers[name] = OpenAICompatProvider(
                name, base_url, config.get_secret(cfg["key"]))
        self.providers["gemini"] = GeminiProvider(config.get_secret(config.GEMINI["key"]))
        self.tavily = TavilySearch(config.get_secret(config.TAVILY["key"]))

        self._cooldown_until: Dict[str, float] = {}
        self._lock = threading.Lock()
        self.stats: Dict[str, Dict[str, int]] = {}

    # ---- status ----
    def active_providers(self) -> List[str]:
        return [n for n, p in self.providers.items() if p.available()]

    def _is_cooling(self, name: str) -> bool:
        return self._cooldown_until.get(name, 0) > time.time()

    def _record(self, name: str, ok: bool, status=None):
        with self._lock:
            s = self.stats.setdefault(name, {"ok": 0, "fail": 0})
            s["ok" if ok else "fail"] += 1
            if not ok:
                # 429/5xx: tunggu lebih lama; error lain: jeda singkat
                wait = 60 if status in (429, 500, 502, 503, 504) else 20
                self._cooldown_until[name] = time.time() + wait

    # ---- panggilan utama ----
    def chat(self, role: str, messages: List[Message], temperature: float = 0.7,
             max_tokens: int = 1500) -> Tuple[str, str]:
        """Jalankan chat sesuai rute peran. Return (teks, nama_provider_yang_dipakai)."""
        errors = []
        for name in config.ROUTES.get(role, []):
            provider = self.providers.get(name)
            if not provider or not provider.available() or self._is_cooling(name):
                continue
            try:
                model = config.ROLE_MODELS.get((role, name)) or config.model_for(name)
                text = provider.chat(model, messages, temperature, max_tokens)
                if not text.strip():
                    raise ProviderError(f"{name}: jawaban kosong")
                self._record(name, True)
                return text, name
            except ProviderError as e:
                self._record(name, False, e.status)
                errors.append(str(e))
        raise AllProvidersFailed(
            f"Semua provider untuk peran '{role}' gagal/tidak aktif. " + " | ".join(errors[-3:]))

    def search(self, query: str, max_results: int = 5):
        if not self.tavily.available():
            return []
        try:
            return self.tavily.search(query, max_results)
        except ProviderError:
            return []
