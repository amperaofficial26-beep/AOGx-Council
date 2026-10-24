"""Uji panel proses (ui/flow.py): status node, escaping HTML, dan tata letak kanvas."""
import unittest

from ui.flow import (DEBATERS, DONE, EDGES, FAILED, NODES, PENDING, RUNNING,
                     SKIPPED, CouncilFlow, _clip, _edge_path)


def st(text):
    return {"kind": "status", "text": text}


def ag(stage, role, text="isi", provider="groq"):
    return {"kind": "agent", "stage": stage, "role": role, "provider": provider, "text": text}


def fin(score=0.9, providers=("groq",), sources=()):
    return {"kind": "final", "answer": "jawaban", "score": score, "issues": [],
            "verified": True, "sources": list(sources), "providers": list(providers)}


class StateTest(unittest.TestCase):
    def test_preview_shows_all_nodes_dim(self):
        flow = CouncilFlow()
        flow.preview()
        html = flow.render()
        self.assertEqual(html.count(f'aog-n-{PENDING}'), len(NODES))
        self.assertIn("aog-e-idle", html)

    def test_status_running_then_agent_done(self):
        flow = CouncilFlow()
        flow.consume(st("Orchestrator menganalisis pertanyaan…"))
        self.assertEqual(flow.state("orchestrator"), RUNNING)
        flow.consume(ag("Perencanaan", "Orchestrator", '{"complexity":"medium","needs_web":false}'))
        self.assertEqual(flow.state("orchestrator"), DONE)
        self.assertEqual(flow.providers["orchestrator"], "groq")
        self.assertIn("s", flow.durations["orchestrator"])

    def test_plan_note_survives_agent_text(self):
        flow = CouncilFlow()
        flow.consume(st("Orchestrator menganalisis pertanyaan…"))
        flow.consume(ag("Perencanaan", "Orchestrator",
                        '{"category":"fakta","complexity":"medium","needs_web":true}'))
        self.assertEqual(flow.notes["orchestrator"], "fakta · medium")

    def test_no_web_skips_researcher(self):
        flow = CouncilFlow()
        flow.consume(st("Orchestrator menganalisis pertanyaan…"))
        flow.consume(ag("Perencanaan", "Orchestrator", '{"needs_web":false,"complexity":"complex"}'))
        self.assertEqual(flow.state("researcher"), SKIPPED)
        self.assertEqual(flow.edge_state("orchestrator", "researcher"), "skip")
        self.assertIn("aog-e-skip", flow.render())

    def test_simple_question_skips_debaters(self):
        flow = CouncilFlow()
        flow.consume(st("Orchestrator menganalisis pertanyaan…"))
        flow.consume(ag("Perencanaan", "Orchestrator", '{"complexity":"simple","needs_web":false}'))
        self.assertEqual({flow.state(n) for n in DEBATERS}, {SKIPPED})

    def test_rounds_relight_debaters(self):
        flow = CouncilFlow()
        flow.consume(st("Agen berdiskusi (putaran 1)…"))
        self.assertEqual({flow.state(n) for n in DEBATERS}, {RUNNING})
        for role in ("Analis", "Skeptis", "Pakar"):
            flow.consume(ag("Diskusi putaran 1", role))
        self.assertEqual({flow.state(n) for n in DEBATERS}, {DONE})
        flow.consume(st("Agen berdiskusi (putaran 2)…"))
        self.assertEqual({flow.state(n) for n in DEBATERS}, {RUNNING})
        self.assertEqual(flow.round_no, 2)

    def test_failed_debater_marks_node(self):
        flow = CouncilFlow()
        flow.consume(st("Agen berdiskusi (putaran 1)…"))
        flow.consume(ag("Diskusi putaran 1", "Analis", text="(gagal: semua provider mati)",
                        provider="-"))
        self.assertEqual(flow.state("analyst"), FAILED)
        self.assertTrue(flow.log[-1]["bad"])
        self.assertNotIn("analyst", flow.providers)

    def test_revision_lights_the_feedback_edge(self):
        flow = CouncilFlow()
        flow.consume(st("Menyusun jawaban final…"))
        flow.consume(ag("Sintesis", "Penyusun"))
        flow.consume(st("Verifier memeriksa jawaban…"))
        flow.consume(ag("Verifikasi", "Verifier", "Skor: 0.30\n- kurang sumber"))
        flow.consume(st("Skor di bawah ambang, jawaban direvisi…"))
        self.assertEqual(flow.attempt, 1)
        self.assertEqual(flow.state("synthesizer"), RUNNING)
        self.assertEqual(flow.edge_state("verifier", "synthesizer"), "live")

    def test_error_marks_running_nodes_failed(self):
        flow = CouncilFlow()
        flow.consume(st("Menyusun jawaban final…"))
        out = flow.consume({"kind": "error", "text": "Semua provider gagal"})
        self.assertEqual(out, "error")
        self.assertEqual(flow.state("synthesizer"), FAILED)
        self.assertEqual(flow.log[-1]["stage"], "Galat")

    def test_final_freezes_score_and_duration(self):
        flow = CouncilFlow()
        flow.consume(fin(score=0.82, sources=[{"title": "t", "url": "u"}]))
        self.assertEqual(flow.state("answer"), DONE)
        self.assertTrue(flow.finished)
        chips = dict(flow.chips())
        self.assertEqual(chips["Skor"], "82%")
        self.assertEqual(chips["Sumber"], "1")
        spent = flow.elapsed
        self.assertEqual(flow.elapsed, spent)

    def test_fast_mode_has_no_verifier_edge_noise(self):
        flow = CouncilFlow(verify=False, rounds=1)
        flow.consume(st("Verifier memeriksa jawaban…"))
        self.assertEqual(flow.state("verifier"), "off")

    def test_flash_flow_skips_rounds_and_tracks_direct_answer(self):
        flow = CouncilFlow(mode_name="Flash", rounds=0, verify=False)
        self.assertEqual(flow.rounds, 0)
        flow.consume(st("Flash menyusun jawaban langsung…"))
        self.assertEqual(flow.state("answer"), RUNNING)
        for node in ("orchestrator", "researcher", *DEBATERS, "synthesizer", "verifier"):
            self.assertEqual(flow.state(node), SKIPPED, node)
        flow.consume(ag("Jawaban langsung", "Flash", "respons ringkas"))
        self.assertEqual(flow.state("answer"), DONE)
        self.assertEqual(dict(flow.chips())["Putaran"], "tanpa putaran")


class RenderTest(unittest.TestCase):
    def test_agent_text_is_escaped(self):
        flow = CouncilFlow()
        flow.consume(ag("Riset", "Researcher", '<script>alert(1)</script> & "kutipan"'))
        html = flow.render() + flow.render_log()
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_unknown_event_ignored(self):
        flow = CouncilFlow()
        self.assertEqual(flow.consume({"kind": "entah"}), "")
        self.assertEqual(flow.log, [])

    def test_log_html_and_placeholder(self):
        flow = CouncilFlow()
        self.assertIn("Belum ada langkah", flow.render_log())
        flow.consume(ag("Riset", "Researcher", "catatan"))
        html = flow.render_log()
        self.assertIn('<div class="aog-log">', html)
        self.assertIn("Researcher", html)

    def test_snapshot_can_be_shown_again(self):
        flow = CouncilFlow(mode_name="Mendalam", rounds=3, verify=True, max_retries=2)
        flow.consume(st("Orchestrator menganalisis pertanyaan…"))
        flow.consume(ag("Perencanaan", "Orchestrator", '{"needs_web":true}'))
        flow.consume(fin(score=0.75))
        copy = CouncilFlow.restore(flow.snapshot(), "q")
        self.assertEqual(copy.states, flow.states)
        self.assertEqual(copy.score, 0.75)
        self.assertEqual(copy.mode_name, "Mendalam")
        self.assertEqual(copy.render(), flow.render())

    def test_snapshot_is_deep_copy(self):
        flow = CouncilFlow()
        flow.consume(fin())
        copy = CouncilFlow.restore(flow.snapshot())
        copy.set("analyst", FAILED)
        self.assertEqual(flow.state("analyst"), "off")


class LayoutTest(unittest.TestCase):
    W, H = 1130, 300

    def test_nodes_inside_canvas(self):
        for name, g in NODES.items():
            self.assertGreaterEqual(g["x"], 0, name)
            self.assertGreaterEqual(g["y"], 0, name)
            self.assertLessEqual(g["x"] + g["w"], self.W, f"{name} keluar kanan")
            self.assertLessEqual(g["y"] + g["h"], self.H, f"{name} keluar bawah")

    def test_nodes_do_not_overlap(self):
        boxes = [(n, g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"]) for n, g in NODES.items()]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                apart = a[3] <= b[1] or b[3] <= a[1] or a[4] <= b[3] or b[4] <= a[3]
                self.assertTrue(apart, f"node tumpang tindih: {a[0]} dan {b[0]}")

    def test_edges_connect_declared_nodes(self):
        for src, dst, _out, _inn, label, pos in EDGES:
            self.assertIn(src, NODES)
            self.assertIn(dst, NODES)
            if label:
                self.assertIn(pos, ("above", "below"))

    def test_edge_curves_inside_canvas(self):
        for src, dst, out, inn, _, _ in EDGES:
            path = _edge_path(NODES[src], NODES[dst], out, inn)
            nums = [float(v) for v in
                    path.replace("M", " ").replace("C", " ").replace(",", " ").split()]
            xs, ys = nums[0::2], nums[1::2]
            self.assertTrue(min(xs) >= 0 and max(xs) <= self.W, f"{src}->{dst} keluar lebar")
            self.assertTrue(min(ys) >= 0 and max(ys) <= self.H, f"{src}->{dst} keluar tinggi")

    def test_clip_collapses_whitespace(self):
        self.assertEqual(_clip("a  b\n c", 40), "a b c")
        self.assertEqual(_clip("x" * 50, 10), "x" * 9 + "…")


class DemoTest(unittest.TestCase):
    def test_demo_router_matches_router_interface(self):
        from ui.demo import DemoRouter
        router = DemoRouter(latency=0)
        text, provider = router.chat("analyst", [{"role": "user", "content": "x"}])
        self.assertTrue(text.strip())
        self.assertEqual(provider, "demo")
        self.assertTrue(router.tavily.available())
        self.assertEqual(len(router.search("q", 4)), 2)
        self.assertEqual(router.active_providers(), ["demo"])

    def test_demo_pipeline_drives_the_flow(self):
        from core import pipeline
        from ui.demo import DemoRouter
        flow = CouncilFlow(mode_name="Seimbang", rounds=2, verify=True, max_retries=1)
        events = list(pipeline.run(DemoRouter(latency=0), "uji", "Seimbang", ""))
        for ev in events:
            flow.consume(ev)
        kinds = [e["kind"] for e in events]
        self.assertIn("final", kinds)
        self.assertEqual(flow.state("answer"), DONE)
        self.assertTrue(flow.finished)
        self.assertIn("aog-n-done", flow.render())
        self.assertGreaterEqual(len(flow.log), 5)


if __name__ == "__main__":
    unittest.main()
