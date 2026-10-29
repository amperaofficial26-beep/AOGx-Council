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

    def test_simple_question_flows_through_main_route_without_jumping(self):
        flow = CouncilFlow("</script><b>x</b>")
        flow.consume(st("Menganalisis pertanyaan"))
        flow.consume(ag("Perencanaan", "Orchestrator", '{"needs_web": false, "complexity": "simple"}'))
        flow.consume(st("Menyusun jawaban"))
        data = neural.payload(flow)
        self.assertFalse(any(e["kind"] == "bypass" for e in data["edges"]))
        cls = {(e["a"], e["b"]): e for e in data["edges"]}
        route = [("orchestrator", "skeptic"), ("skeptic", "skeptic_recall"),
                 ("skeptic_recall", "skeptic_proc"), ("skeptic_proc", "synthesizer")]
        for i, key in enumerate(route):
            self.assertEqual(cls[key]["cls"], "live", key)
            self.assertEqual((cls[key]["seq"], cls[key]["seqn"]), (i, 4))
        for agent in ("analyst", "expert"):
            self.assertEqual(cls[("orchestrator", agent)]["cls"], "skip")
            self.assertEqual(cls[(f"{agent}_proc", "synthesizer")]["cls"], "skip")
        nodes = {n["id"]: n for n in data["nodes"]}
        self.assertEqual(nodes["skeptic"]["state"], "skipped")
        html = neural.render(flow)
        self.assertNotIn("</script><b>", html)
        self.assertNotIn("__DATA__", html)

    def test_flash_mode_runs_light_from_trigger_to_answer(self):
        flow = CouncilFlow("hai", rounds=0, verify=False)
        flow.consume(st("Flash: menjawab langsung"))
        edges = {(e["a"], e["b"]): e for e in neural.payload(flow)["edges"]}
        self.assertEqual(edges[("start", "orchestrator")]["cls"], "live")
        self.assertEqual(edges[("verifier", "answer")]["seqn"], 7)


if __name__ == "__main__":
    unittest.main()
