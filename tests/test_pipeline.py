import unittest
from unittest.mock import patch

import config
from core import pipeline
from core.router import AllProvidersFailed


class FakeTavily:
    def __init__(self, available=True, results=None):
        self._available = available
        self._results = results or []
        self.queries = []

    def available(self):
        return self._available

    def search(self, query, max_results=5):
        self.queries.append(query)
        return self._results[:max_results]


PLAN = {"category": "analisis", "complexity": "medium", "needs_web": False,
        "search_queries": [], "focus_points": ["fokus"]}


def run_events(plan=None, tavily=None, rounds=2, verify=True, max_retries=1,
               answer="jawaban", scores=None, fail_synth=False):
    """Jalankan pipeline dengan agen palsu, kembalikan daftar event."""
    scores = list(scores or [0.9])
    fake_router = type("R", (), {"tavily": tavily or FakeTavily(available=False)})()
    modes = dict(config.MODES)
    modes["Uji"] = {"rounds": rounds, "verify": verify, "max_retries": max_retries}

    def synth(*args, **kwargs):
        if fail_synth:
            raise AllProvidersFailed("semua provider gagal")
        return answer, "gemini"

    def verify_agent(*args, **kwargs):
        return {"score": scores.pop(0) if scores else 0.9, "issues": ["kurang sumber"]}, "gemini"

    with patch.dict(config.MODES, modes, clear=False), \
         patch.object(pipeline.orchestrator, "plan", return_value=(plan or PLAN, "groq")), \
         patch.object(pipeline.researcher, "gather", return_value=("catatan", [], "groq")), \
         patch.object(pipeline.debaters, "opening", return_value=("jawaban awal", "gemini")), \
         patch.object(pipeline.debaters, "rebuttal", return_value=("revisi agen", "aion")), \
         patch.object(pipeline.synthesizer, "synthesize", side_effect=synth), \
         patch.object(pipeline.verifier, "verify", side_effect=verify_agent):
        return list(pipeline.run(fake_router, "pertanyaan", "Uji"))


def scripted_router(replies, calls=None):
    """Router palsu yang membalas berurutan; cocok untuk menguji retry agen."""
    replies = list(replies)
    calls = calls if calls is not None else []
    router = type("R", (), {})()
    router.chat = lambda role, messages, temperature=0.7, max_tokens=1500: (
        calls.append(messages), (replies.pop(0) if replies else "kosong", "groq"))[1]
    return router


def final(events):
    return [e for e in events if e["kind"] == "final"][0]


class PipelineTest(unittest.TestCase):
    def test_nominal_flow(self):
        events = run_events()
        f = final(events)
        self.assertEqual(f["answer"], "jawaban")
        self.assertTrue(f["verified"])
        self.assertEqual(f["score"], 0.9)
        self.assertIn("gemini", f["providers"])
        stages = [e["stage"] for e in events if e["kind"] == "agent"]
        self.assertIn("Perencanaan", stages)
        self.assertIn("Sintesis", stages)
        self.assertIn("Verifikasi", stages)

    def test_low_score_triggers_revision(self):
        events = run_events(scores=[0.2, 0.95], max_retries=1)
        f = final(events)
        self.assertEqual(f["score"], 0.95)
        self.assertIn("Revisi", [e["stage"] for e in events if e["kind"] == "agent"])

    def test_simple_question_still_verified(self):
        simple = dict(PLAN, complexity="simple")
        events = run_events(plan=simple, rounds=2)
        stages = [e["stage"] for e in events if e["kind"] == "agent"]
        self.assertNotIn("Diskusi putaran 1", stages)  # diskusi dilewati
        self.assertIn("Verifikasi", stages)  # tapi tetap diverifikasi
        self.assertTrue(final(events)["verified"])

    def test_fast_mode_skips_verification(self):
        events = run_events(verify=False)
        f = final(events)
        self.assertFalse(f["verified"])
        self.assertIsNone(f["score"])
        self.assertNotIn("Verifikasi", [e["stage"] for e in events if e["kind"] == "agent"])

    def test_verifier_unavailable_marks_unverified(self):
        fake_router = type("R", (), {"tavily": FakeTavily(available=False)})()
        with patch.object(pipeline.orchestrator, "plan", return_value=(PLAN, "groq")), \
             patch.object(pipeline.debaters, "opening", return_value=("a", "gemini")), \
             patch.object(pipeline.debaters, "rebuttal", return_value=("b", "aion")), \
             patch.object(pipeline.synthesizer, "synthesize", return_value=("jawaban", "gemini")), \
             patch.object(pipeline.verifier, "verify", side_effect=AllProvidersFailed("kosong")):
            f = final(list(pipeline.run(fake_router, "t", "Seimbang")))
        self.assertFalse(f["verified"])
        self.assertIsNone(f["score"])
        self.assertEqual(f["answer"], "jawaban")

    def test_web_research_runs_when_requested(self):
        tavily = FakeTavily(results=[{"title": "T", "url": "https://a", "content": "isi"}])
        plan = dict(PLAN, needs_web=True, complexity="complex", search_queries=["q1"])
        events = run_events(plan=plan, tavily=tavily)
        self.assertIn("Riset", [e["stage"] for e in events if e["kind"] == "agent"])

    def test_web_research_skipped_without_tavily(self):
        plan = dict(PLAN, needs_web=True)
        events = run_events(plan=plan, tavily=FakeTavily(available=False))
        self.assertNotIn("Riset", [e["stage"] for e in events if e["kind"] == "agent"])

    def test_pipeline_failure_returns_error_event(self):
        events = run_events(fail_synth=True)
        self.assertEqual(events[-1]["kind"], "error")
        self.assertNotIn("Traceback", events[-1]["text"])

    def test_rounds_are_respected(self):
        events = run_events(rounds=3)
        stages = [e["stage"] for e in events if e["kind"] == "agent"]
        self.assertIn("Diskusi putaran 2", stages)
        self.assertIn("Diskusi putaran 3", stages)

    def test_failed_debater_does_not_kill_run(self):
        fake_router = type("R", (), {"tavily": FakeTavily(available=False)})()
        with patch.object(pipeline.orchestrator, "plan", return_value=(PLAN, "groq")), \
             patch.object(pipeline.debaters, "opening",
                          side_effect=AllProvidersFailed("mati")), \
             patch.object(pipeline.synthesizer, "synthesize", return_value=("jawaban", "gemini")), \
             patch.object(pipeline.verifier, "verify", return_value=({"score": 0.9, "issues": []}, "gemini")):
            events = list(pipeline.run(fake_router, "t", "Seimbang"))
        self.assertEqual(events[-1]["kind"], "final")


class JsonPlanTest(unittest.TestCase):
    """Rencana default tetap masuk akal kalau model tidak memberi JSON."""

    def test_orchestrator_falls_back_to_default(self):
        from agent import orchestrator
        plan, _ = orchestrator.plan(scripted_router(["bukan json"]), "halo", "")
        self.assertEqual(plan, orchestrator.DEFAULT)

    def test_orchestrator_retries_bad_json(self):
        from agent import orchestrator
        calls = []
        router = scripted_router(["maaf saya lupa format",
                                  '{"complexity": "simple", "needs_web": true}'], calls)
        plan, _ = orchestrator.plan(router, "halo", "")
        self.assertEqual(plan["complexity"], "simple")
        self.assertTrue(plan["needs_web"])
        self.assertEqual(len(calls), 2)

    def test_verifier_retries_bad_json(self):
        from agent import verifier
        router = scripted_router(["skor bagus kok", '{"score": 0.9, "issues": []}'])
        v, prov = verifier.verify(router, "t", "j", "")
        self.assertEqual(v["score"], 0.9)
        self.assertEqual(prov, "groq")


if __name__ == "__main__":
    unittest.main()
