"""Uji tampilan mesin (ui/machine.py): kubus, status, panel alur, dan batas kanvas."""
import unittest

from ui import machine
from ui.flow import DEBATERS, DONE, FAILED, NODES, PENDING, RUNNING, SKIPPED, CouncilFlow


def st(text):
    return {"kind": "status", "text": text}


def ag(stage, role, text="isi", provider="groq"):
    return {"kind": "agent", "stage": stage, "role": role, "provider": provider, "text": text}


class CubeTest(unittest.TestCase):
    def test_every_agent_has_a_cube_inside_canvas(self):
        agents = [n for n in NODES if n not in ("start", "answer")]
        self.assertEqual(sorted(machine.CUBES), sorted(agents))
        for name, (x, y) in machine.CUBES.items():
            self.assertGreaterEqual(x - machine.DX, 0, name)
            self.assertLessEqual(x + machine.DX, machine.LG_X, f"{name} masuk panel alur")
            self.assertGreaterEqual(y - machine.S, 0, name)
            self.assertLessEqual(y + machine.S, machine.H, name)

    def test_cubes_do_not_overlap(self):
        items = list(machine.CUBES.items())
        for i, (a, (ax, ay)) in enumerate(items):
            for b, (bx, by) in items[i + 1:]:
                apart = abs(ax - bx) >= 2 * machine.DX or abs(ay - by) >= 2 * machine.S
                self.assertTrue(apart, f"kubus tumpang tindih: {a} dan {b}")

    def test_preview_shows_all_cubes_pending(self):
        flow = CouncilFlow()
        flow.preview()
        html = machine.render(flow)
        self.assertTrue(flow.verify)
        self.assertEqual(html.count('class="aog-c aog-c-pending"'), len(machine.CUBES))

    def test_running_and_done_states(self):
        flow = CouncilFlow()
        flow.consume(st("Orchestrator menganalisis pertanyaan…"))
        html = machine.render(flow)
        self.assertIn("aog-c-running", html)
        self.assertIn("aog-mesh-live", html)
        flow.consume(ag("Perencanaan", "Orchestrator", '{"complexity":"medium","needs_web":true}'))
        html = machine.render(flow)
        self.assertIn("aog-c-done", html)
        self.assertIn("groq", html)

    def test_skipped_verifier_when_mode_has_no_verify(self):
        flow = CouncilFlow(verify=False)
        self.assertEqual(machine.node_state(flow, "verifier"), SKIPPED)

    def test_text_is_escaped(self):
        flow = CouncilFlow()
        flow.notes["orchestrator"] = "<script>x</script>"
        self.assertNotIn("<script>", machine.render(flow))

    def test_finished_status_text(self):
        flow = CouncilFlow()
        flow.stage_text = "Verifier memeriksa jawaban…"
        flow.consume({"kind": "final", "answer": "a", "score": 0.9, "issues": [],
                      "verified": True, "sources": [], "providers": ["groq"]})
        html = machine.render(flow)
        self.assertIn(">Selesai<", html)
        self.assertNotIn("Verifier memeriksa", html)


class GraphTest(unittest.TestCase):
    def test_debate_state_aggregates(self):
        flow = CouncilFlow()
        self.assertEqual(machine.debate_state(flow), PENDING)
        flow.set("analyst", RUNNING)
        self.assertEqual(machine.debate_state(flow), RUNNING)
        for n in DEBATERS:
            flow.set(n, DONE)
        self.assertEqual(machine.debate_state(flow), DONE)
        for n in DEBATERS:
            flow.set(n, SKIPPED)
        self.assertEqual(machine.debate_state(flow), SKIPPED)
        flow.set("analyst", FAILED)
        flow.set("skeptic", FAILED)
        flow.set("expert", FAILED)
        self.assertEqual(machine.debate_state(flow), FAILED)

    def test_simple_question_lights_direct_edge(self):
        flow = CouncilFlow()
        flow.consume(st("Orchestrator menganalisis pertanyaan…"))
        flow.consume(ag("Perencanaan", "Orchestrator", '{"complexity":"simple","needs_web":false}'))
        self.assertIn("sederhana", machine.render(flow))

    def test_revision_edge_only_lights_after_retry(self):
        flow = CouncilFlow()
        self.assertIn('aog-e aog-e-idle" d="M212,419', machine._graph(flow))
        flow.attempt = 1
        self.assertIn('aog-e aog-e-hot" d="M212,419', machine._graph(flow))

    def test_graph_has_all_steps(self):
        html = machine._graph(CouncilFlow())
        for label in ("START", "State", "Orchestrator", "Researcher", "Debat 3 agen",
                      "Penyusun", "Verifier", "Jawaban final", "END"):
            self.assertIn(label, html)

    def test_restore_renders_same(self):
        flow = CouncilFlow()
        flow.consume(st("Orchestrator menganalisis pertanyaan…"))
        copy = CouncilFlow.restore(flow.snapshot())
        self.assertEqual(machine.render(copy).count("aog-c-"),
                         machine.render(flow).count("aog-c-"))

    def test_mesh_is_deterministic(self):
        self.assertEqual(machine.mesh_points(), machine.mesh_points())


if __name__ == "__main__":
    unittest.main()
