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
        self.last_error: Dict[str, str] = {}  # error terakhir per provider (untuk diagnosis)

    # ---- status ----
    def _usable(self, name: str) -> bool:
        p = self.providers.get(name)
        return bool(p and p.available() and config.model_for(name))

    def active_providers(self) -> List[str]:
        return [n for n in self.providers if self._usable(n)]

    def _is_cooling(self, name: str) -> bool:
        return self._cooldown_until.get(name, 0) > time.time()

    def _record(self, name: str, ok: bool, status=None, error: str = ""):
        with self._lock:
            s = self.stats.setdefault(name, {"ok": 0, "fail": 0})
            s["ok" if ok else "fail"] += 1
            if ok:
                self.last_error.pop(name, None)
            else:
                self.last_error[name] = error[:300]
                if status in (429, 500, 502, 503, 504):
                    wait = 60    # limit/server sibuk
                elif status in (400, 401, 403, 404):
                    wait = 120   # biasanya salah key/model: mengulang cepat percuma
                else:
                    wait = 20    # gangguan koneksi
                self._cooldown_until[name] = time.time() + wait

    # ---- panggilan utama ----
    def chat(self, role: str, messages: List[Message], temperature: float = 0.7,
             max_tokens: int = 1500) -> Tuple[str, str]:
        """Jalankan chat sesuai rute peran. Return (teks, nama_provider_yang_dipakai)."""
        errors = []
        for name in config.ROUTES.get(role, []):
            provider = self.providers.get(name)
            if not self._usable(name):
                continue
            if self._is_cooling(name):
                errors.append(f"{name}: sedang jeda ({self.last_error.get(name, 'error sebelumnya')})")
                continue
            try:
                model = config.ROLE_MODELS.get((role, name)) or config.model_for(name)
                text = provider.chat(model, messages, temperature, max_tokens)
                if not text.strip():
                    raise ProviderError(f"{name}: jawaban kosong")
                self._record(name, True)
                return text, name
            except ProviderError as e:
                self._record(name, False, e.status, str(e))
                errors.append(str(e))
        raise AllProvidersFailed(
            f"Semua provider untuk peran '{role}' gagal/tidak aktif. " + " | ".join(errors[-5:]))

    def diagnose(self):
        """Tes tiap provider dengan prompt kecil. Return [(nama, True/False/None, pesan)]."""
        out = []
        for name, p in self.providers.items():
            if not p.available():
                out.append((name, None, "tidak aktif (key atau base URL kosong)"))
                continue
            if not config.model_for(name):
                out.append((name, None, f"model belum dipilih (isi {name.upper()}_MODEL)"))
                continue
            model = config.model_for(name)
            try:
                text = p.chat(model, [{"role": "user", "content": "Jawab satu kata: halo"}],
                              temperature=0.0, max_tokens=30)
                out.append((name, True, f"{model} -> {text.strip()[:40] or '(jawaban kosong)'}"))
            except ProviderError as e:
                out.append((name, False, f"{model} -> {e}"))
        if self.tavily.available():
            try:
                self.tavily.search("test", 1)
                out.append(("tavily", True, "pencarian berhasil"))
            except ProviderError as e:
                out.append(("tavily", False, str(e)))
        return out

    def list_models(self, name: str) -> List[str]:
        provider = self.providers.get(name)
        if not provider or not provider.available():
            raise ProviderError(f"{name}: key belum diisi")
        return provider.list_models()

    def search(self, query: str, max_results: int = 5):
        if not self.tavily.available():
            return []
        try:
            return self.tavily.search(query, max_results)
        except ProviderError:
            return []
