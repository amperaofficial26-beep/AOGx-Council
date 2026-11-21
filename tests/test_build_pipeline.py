"""Uji pipeline BUILD (build/pipeline.py) + agen research/interview/planner tanpa API key.

Semua interaksi model dan Tavily memakai router/tavily palsu sehingga uji berjalan offline.
"""
import json
import unittest
from unittest.mock import patch

from agent import build_interview, build_planner, build_research
from build import pipeline
from core.router import AllProvidersFailed

SOURCE_A = {"title": "Dokumentasi Fitur", "url": "https://docs.contoh.id/features",
            "content": "Aplikasi menyediakan template dan ekspor PNG."}
SOURCE_B = {"title": "Issue tracker", "url": "https://github.com/contoh/app/issues",
            "content": "Pengguna melaporkan bug ekspor berulang kali."}


class FakeTavily:
    def __init__(self, available=True, results=None):
        self._available = available
        self._results = results if results is not None else [SOURCE_A, SOURCE_B]

    def available(self):
        return self._available


class FakeRouter:
    """Router tiruan: `search` dari Tavily palsu, `chat` menjawab berdasarkan peran."""

    def __init__(self, replies=None, search_results=None, tavily_available=True,
                 chat_error=None):
        self.tavily = FakeTavily(tavily_available, search_results)
        self.replies = dict(replies or {})
        self.search_results = search_results if search_results is not None else [SOURCE_A, SOURCE_B]
        self.chat_error = chat_error
        self.chat_calls = []

    def search(self, query, max_results=5):
        return self.search_results[:max_results]

    def chat(self, role, messages, temperature=0.7, max_tokens=1500):
        self.chat_calls.append(role)
        if self.chat_error is not None:
            raise self.chat_error
        reply = self.replies.get(role, "{}")
        if isinstance(reply, list):  # jawaban bergiliran per peran
            reply = reply.pop(0) if reply else "{}"
        return reply, "groq"


RESEARCH_REPLY = json.dumps({
    "findings": [
        {"topic": "fitur", "claim": "Menyediakan template siap pakai",
         "source": "https://docs.contoh.id/features"},
        {"topic": "bug", "claim": "Ekspor PNG gagal berulang",
         "source": "https://github.com/contoh/app/issues"},
        # Klaim dengan URL yang tidak ada di daftar sumber: wajib dibuang.
        {"topic": "keluhan", "claim": "Klaim ngawur", "source": "https://karangan.tld/x"},
    ],
    "missing": ["teknologi"],
}, ensure_ascii=False)

ANALYSIS_REPLY = ("1. Kekurangan: ekspor rawan gagal. 2. Titik sulit: alur berlapis. "
                  "3. Peluang: ekspor sekali klik. 4. Fitur baru: preset cerdas. "
                  "5. Konsep: StudioRingan — editor ringan satu layar.")

BLUEPRINT_REPLY = json.dumps({
    "nama": "StudioRingan",
    "konsep": "Editor visual ringan untuk pemula",
    "target": ["Kreator pemula"],
    "fitur_inti": ["Editor kanvas", "Ekspor satu klik"],
    "fitur_tambahan": ["Kolaborasi"],
    "fitur_yang_ditingkatkan": ["Ekspor jadi lebih andal"],
    "ui_ux": "Satu layar, tombol besar",
    "halaman": ["Beranda", "Editor"],
    "alur": ["Pilih template", "Edit", "Ekspor"],
    "backend": ["Penyimpanan berkas"],
    "ai": ["Saran preset"],
    "teknologi": ["Streamlit", "SQLite"],
}, ensure_ascii=False)


def make_router(**kwargs):
    replies = {"build_research": RESEARCH_REPLY, "build_analyst": ANALYSIS_REPLY,
               "build_planner": BLUEPRINT_REPLY, "build_interview": "{}"}
    replies.update(kwargs.pop("replies", {}))
    return FakeRouter(replies=replies, **kwargs)


class ResearchAgentTest(unittest.TestCase):
    def test_gather_keeps_only_claims_with_valid_urls(self):
        router = make_router()
        research, sources, provider = build_research.gather(
            router, "buatkan app seperti canva", ["Canva"])
        self.assertEqual(len(sources), 2)
        self.assertEqual(provider, "groq")
        urls = {s["url"] for s in sources}
        for claim in research["claims"]:
            self.assertIn(claim["source"], urls)  # setiap klaim menyimpan URL sumbernya
        topics = {c["topic"] for c in research["claims"]}
        self.assertIn("fitur", topics)
        self.assertIn("bug", topics)
        self.assertNotIn("keluhan", topics)  # sumber karangan dibuang
        # Topik tanpa klaim masuk "missing" dan akan ditampilkan "tidak ditemukan".
        self.assertIn("teknologi", research["missing"])
        self.assertIn("workflow", research["missing"])

    def test_without_tavily_everything_is_missing(self):
        router = make_router(tavily_available=False, search_results=[])
        research, sources, provider = build_research.gather(
            router, "permintaan", ["Canva"])
        self.assertEqual(research["claims"], [])
        self.assertEqual(sources, [])
        self.assertIsNone(provider)
        self.assertEqual(len(research["missing"]), len(build_research.TOPICS))

    def test_empty_search_results_skip_model_call(self):
        router = make_router(search_results=[])
        research, sources, _ = build_research.gather(router, "x", [])
        self.assertEqual(sources, [])
        self.assertEqual(research["claims"], [])
        self.assertEqual(router.chat_calls, [])  # tanpa sumber, model tidak dipanggil

    def test_queries_mention_references(self):
        queries = build_research.search_queries("buat app edit video", ["CapCut"])
        self.assertTrue(any("CapCut" in q for q in queries))
        self.assertTrue(any("features" in q for q in queries))


class InterviewAgentTest(unittest.TestCase):
    def test_suggest_merges_defaults_and_keeps_ranking(self):
        router = make_router(replies={
            "build_interview": json.dumps({
                "references": ["Figma", "Canva"], "reason": "permintaan soal desain",
                "extra": ["Penpot"]})})
        out, provider = build_interview.suggest(router, "buat app desain")
        self.assertEqual(provider, "groq")
        self.assertEqual(out["ai_ranked"], ["Figma", "Canva"])
        # Daftar tawaran tetap memuat pilihan bawaan lain.
        for name in build_interview.DEFAULT_REFERENCES:
            self.assertIn(name, out["references"])
        self.assertIn("Penpot", out["references"])
        self.assertIn("Penpot", out["extra"])

    def test_suggest_falls_back_when_model_returns_garbage(self):
        router = make_router(replies={"build_interview": "bukan json sama sekali"})
        out, _ = build_interview.suggest(router, "permintaan")
        self.assertEqual(out["references"], build_interview.DEFAULT_REFERENCES)
        self.assertEqual(out["ai_ranked"], [])


class PlannerAgentTest(unittest.TestCase):
    def test_plan_normalizes_blueprint(self):
        router = make_router()
        blueprint, provider = build_planner.plan(
            router, "permintaan", ["Canva"], ANALYSIS_REPLY, form_kind="Web Application")
        self.assertEqual(provider, "groq")
        self.assertEqual(blueprint["nama"], "StudioRingan")
        self.assertEqual(blueprint["fitur_inti"], ["Editor kanvas", "Ekspor satu klik"])
        self.assertIn("Streamlit", blueprint["teknologi"])

    def test_plan_handles_empty_model_reply(self):
        router = make_router(replies={"build_planner": "tidak ada json"})
        blueprint, _ = build_planner.plan(router, "x", [], "")
        self.assertEqual(blueprint["nama"], "")
        self.assertEqual(blueprint["fitur_inti"], [])


class PipelineTest(unittest.TestCase):
    def run_pipeline(self, router, form="Web Application"):
        return list(pipeline.run(router, "buatkan aplikasi seperti Canva",
                                 ["Canva"], form))

    def test_nominal_flow_produces_sourced_result(self):
        events = self.run_pipeline(make_router())
        kinds = [e["kind"] for e in events]
        self.assertEqual(kinds[0], "status")
        self.assertIn("final", kinds)
        stages = [e["stage"] for e in events if e["kind"] == "agent"]
        self.assertEqual(stages, ["RESEARCH", "ANALISIS", "PLANNING"])
        final = [e for e in events if e["kind"] == "final"][0]
        self.assertEqual(final["blueprint"]["nama"], "StudioRingan")
        self.assertEqual(final["form_kind"], "Web Application")
        self.assertEqual(final["references"], ["Canva"])
        self.assertEqual(final["request"], "buatkan aplikasi seperti Canva")
        self.assertIn("groq", final["providers"])
        # Sumber ikut tersimpan untuk ditampilkan di UI.
        self.assertEqual({s["url"] for s in final["sources"]},
                         {SOURCE_A["url"], SOURCE_B["url"]})
        for claim in final["research"]["claims"]:
            self.assertIn(claim["source"], {s["url"] for s in final["sources"]})

    def test_provider_failure_yields_error_event(self):
        router = make_router(chat_error=AllProvidersFailed("semua provider gagal"))
        events = self.run_pipeline(router)
        self.assertEqual(events[-1]["kind"], "error")
        self.assertIn("semua provider gagal", events[-1]["text"])
        self.assertNotIn("final", [e["kind"] for e in events])

    def test_unexpected_exception_is_sanitized(self):
        router = make_router()
        with patch.object(build_research, "gather",
                          side_effect=ValueError("detail internal rahasia")):
            events = self.run_pipeline(router)
        self.assertEqual(events[-1]["kind"], "error")
        self.assertNotIn("rahasia", events[-1]["text"])
        self.assertIn("ValueError", events[-1]["text"])

    def test_status_events_describe_each_stage(self):
        events = self.run_pipeline(make_router())
        texts = [e["text"] for e in events if e["kind"] == "status"]
        self.assertTrue(any("RESEARCH" in t for t in texts))
        self.assertTrue(any("ANALISIS" in t for t in texts))
        self.assertTrue(any("PLANNING" in t for t in texts))


if __name__ == "__main__":
    unittest.main()
