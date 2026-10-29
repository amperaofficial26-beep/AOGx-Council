"""Uji payload Mesin Council bergaya workflow (ui/neural.py)."""
import unittest

from ui import neural
from ui.flow import CouncilFlow


def st(text):
    return {"kind": "status", "text": text}


def ag(stage, role, text="isi", provider="groq"):
    return {"kind": "agent", "stage": stage, "role": role, "provider": provider, "text": text}


class WorkflowPayloadTest(unittest.TestCase):
    def test_layout_has_trigger_lanes_bundle_and_success(self):
        flow = CouncilFlow("tes")
        flow.preview()
        data = neural.payload(flow)
        ids = {n["id"] for n in data["nodes"]}
        for agent in ("analyst", "skeptic", "expert"):
            for suffix in ("", "_model", "_parser", "_recall", "_proc"):
                self.assertIn(agent + suffix, ids)
        for nid in ("start", "orchestrator", "researcher", "synthesizer", "verifier", "answer"):
            self.assertIn(nid, ids)
        for e in data["edges"]:
            self.assertIn(e["a"], ids)
            self.assertIn(e["b"], ids)

    def test_lane_states_follow_agent_and_synthesizer(self):
        flow = CouncilFlow("tes", rounds=1)
        for ev in (st("Menganalisis pertanyaan"),
                   ag("Perencanaan", "Orchestrator", '{"needs_web": false, "complexity": "complex"}'),
                   st("Agen berdiskusi (putaran 1)"), ag("Diskusi", "Analis", "a", "gemini")):
            flow.consume(ev)
        n = {x["id"]: x for x in neural.payload(flow)["nodes"]}
        self.assertEqual(n["analyst"]["state"], "done")
        self.assertEqual(n["analyst_recall"]["state"], "done")
        self.assertEqual(n["analyst_proc"]["state"], "running")
        self.assertEqual(n["analyst_model"]["sub"], "gemini")
        self.assertEqual(n["skeptic_recall"]["state"], "pending")
        self.assertEqual(n["researcher"]["state"], "skipped")

        flow.consume(st("Menyusun jawaban"))
        n = {x["id"]: x for x in neural.payload(flow)["nodes"]}
        self.assertEqual(n["analyst_proc"]["state"], "done")

    def test_simple_question_adds_bypass_and_render_is_safe(self):
        flow = CouncilFlow("</script><b>x</b>")
        flow.consume(st("Menganalisis pertanyaan"))
        flow.consume(ag("Perencanaan", "Orchestrator", '{"needs_web": false, "complexity": "simple"}'))
        data = neural.payload(flow)
        self.assertTrue(any(e["kind"] == "bypass" for e in data["edges"]))
        html = neural.render(flow)
        self.assertNotIn("</script><b>", html)
        self.assertNotIn("__DATA__", html)


if __name__ == "__main__":
    unittest.main()
