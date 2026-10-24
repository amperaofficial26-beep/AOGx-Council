"""Mode demo: router tiruan supaya panel proses bisa dilihat tanpa API key (dan untuk uji UI).

Tidak menyentuh core/pipeline — hanya menggantikan sumber jawaban.
"""
import json
import random
import time

from providers.base import ProviderError

_PLAN = {"category": "analisis", "complexity": "complex", "needs_web": True,
         "search_queries": ["dampak AI pada produktivitas tim 2026"],
         "focus_points": ["produktivitas", "biaya", "risiko kualitas", "cara ukur"]}

_SOURCES = [{"title": "Riset produktivitas AI 2026", "url": "https://contoh.id/riset-a",
             "content": "Tim yang memakai asisten AI melaporkan kenaikan throughput 12-18% "
                        "untuk pekerjaan tulis-menulis dan analisis data."},
            {"title": "Biaya tersembunyi adopsi AI", "url": "https://contoh.id/riset-b",
             "content": "Hampir 30% organisasi menanggung biaya review ulang keluaran model."}]

_REPLIES = {
    "orchestrator": json.dumps(_PLAN, ensure_ascii=False),
    "researcher": ("Ringkasan riset: [1] throughput naik 12-18% pada kerja tulis & analisis data; "
                   "[2] biaya review ulang mencapai 30% proyek. Sumber saling melengkapi, tidak bertentangan."),
    "analyst": ("Langkah 1: manfaat terkonsentrasi pada kerja repetitif. Langkah 2: pekerjaan judgment "
                "hanya terbantu sedikit. Langkah 3: tanpa mekanisme review, kesalahan model menumpuk. "
                "Kesimpulan: hemat 12-18% waktu bila ada reviewer manusia."),
    "skeptic": ("Angka 12-18% berasal dari survei mandiri, rawan bias seleksi; biaya 30% sering tidak "
                "dicatat. Klaim 'hemat waktu' baru sah bila waktu review ikut dihitung."),
    "expert": ("Praktik terbaik: pilih 3 use case, pasang baseline, ukur cycle time dan defect rate, "
               "lalu wajibkan review untuk keluaran yang menyentuh keputusan. Jangan pakai skor survei "
               "sebagai pengganti metrik operasional."),
    "verifier": json.dumps({"score": 0.86, "issues": ["Metrik pengukuran belum dibatasi waktunya."],
                            "verdict": "pass"}, ensure_ascii=False),
}


class _DemoTavily:
    def __init__(self):
        self.calls = 0

    def available(self):
        return True

    def search(self, query, max_results=5):
        self.calls += 1
        time.sleep(0.3)
        return _SOURCES[:max_results]


class DemoRouter:
    """Antarmuka sama seperti core.router.Router, tapi menjawab dari teks siap pakai."""

    def __init__(self, latency: float = 0.5, bad_rate: float = 0.0, seed: int = 7):
        self.tavily = _DemoTavily()
        self.latency = latency
        self.bad_rate = bad_rate
        self.stats = {}
        self.last_error = {}
        self.providers = {}
        self._rng = random.Random(seed)
        self._answers = {}

    # ---- status ----
    def active_providers(self):
        return ["demo"]

    def diagnose(self):
        return [("demo", True, "mode demo aktif (tanpa API key)")]

    def list_models(self, name="demo"):
        return ["demo-model"]

    def search(self, query: str, max_results: int = 5):
        return self.tavily.search(query, max_results)

    # ---- panggilan ----
    def chat(self, role, messages, temperature=0.7, max_tokens=1500):
        """Return (teks, provider) seperti Router asli."""
        if role == "flash":
            role = "synthesizer"  # satu respons langsung juga saat demo tanpa API key
        time.sleep(self.latency + self._rng.random() * 0.5)
        if self._rng.random() < self.bad_rate:
            self.stats.setdefault("demo", {"ok": 0, "fail": 0})["fail"] += 1
            raise ProviderError("demo: jaringan bermasalah", 503)
        self.stats.setdefault("demo", {"ok": 0, "fail": 0})["ok"] += 1
        if role == "synthesizer":
            if self._answers.get("synthesizer"):  # putaran revisi: jawaban kedua lebih rapi
                return ("Ringkasan council: AI mempercepat kerja repetitif 12-18%, dengan syarat ada "
                        "review manusia; biaya tersembunyi ~30% ikut dihitung sebagai biaya proyek. "
                        "Cara ukur: baseline, cycle time, defect rate. [1][2]", "demo")
            self._answers["synthesizer"] = "v1"
            return ("AI mempercepat kerja repetitif 12-18% dan mengurangi beban dokumen. Untuk "
                    "pekerjaan judgment, manfaatnya lebih kecil.", "demo")
        if role in _REPLIES:
            return _REPLIES[role], "demo"
        return f"({role}) catatan dari agen demo.", "demo"
