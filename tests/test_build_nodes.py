"""Unit test model node kanvas BUILD & penyimpanan proyek (tanpa API key)."""
import unittest

from build import project_store
from ui.build_nodes import (
    PREP_NODES, cables_svg, compute_edges, live_stage_from_text,
    prep_status, process_nodes,
)


class PrepStatusTest(unittest.TestCase):
    def test_hanya_langkah_aktif_yang_tampil(self):
        self.assertEqual(prep_status(1, "request"), "active")
        self.assertIsNone(prep_status(2, "request"))  # prasyarat belum selesai
        self.assertIsNone(prep_status(5, "request"))

    def test_progresi_selesai_lalu_aktif(self):
        self.assertEqual(prep_status(1, "reference"), "completed")
        self.assertEqual(prep_status(2, "reference"), "active")
        self.assertEqual(prep_status(3, "reference"), None)
        self.assertEqual(prep_status(4, "confirm"), "active")
        self.assertEqual(prep_status(4, "running"), "completed")
        self.assertEqual(prep_status(4, "result"), "completed")
        self.assertEqual(prep_status(5, "result"), "active")
        self.assertIsNone(prep_status(5, "running"))  # hasil belum ada

    def test_error_tetap_mempertahankan_tahap(self):
        self.assertEqual(prep_status(4, "error"), "completed")
        self.assertIsNone(prep_status(5, "error"))


class ProcessNodesTest(unittest.TestCase):
    def test_kosong_sebelum_proses(self):
        self.assertEqual(process_nodes([]), [])
        self.assertEqual(process_nodes([], error="gagal"), [])

    def test_status_saja_belum_menampilkan_tahap_berikutnya(self):
        nodes = process_nodes([{"kind": "status", "text": "RESEARCH: mencari"}])
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["stage"], "RESEARCH")
        self.assertEqual(nodes[0]["status"], "processing")

    def test_agent_menyelesaikan_tahap(self):
        events = [
            {"kind": "agent", "stage": "RESEARCH", "role": "Researcher",
             "provider": "p", "text": "hasil riset"},
            {"kind": "status", "text": "ANALISIS: memetakan"},
        ]
        nodes = process_nodes(events, live_text="ANALISIS: memetakan")
        self.assertEqual([n["stage"] for n in nodes], ["RESEARCH", "ANALISIS"])
        self.assertEqual(nodes[0]["status"], "completed")
        self.assertEqual(nodes[1]["status"], "processing")
        self.assertEqual(nodes[0]["info"], "hasil riset")

    def test_prefix_product_planning_jadi_planning(self):
        self.assertEqual(live_stage_from_text("PRODUCT PLANNING: menyusun"),
                         "PLANNING")
        nodes = process_nodes(
            [{"kind": "status", "text": "PRODUCT PLANNING: menyusun"}],
            live_text="PRODUCT PLANNING: menyusun")
        self.assertEqual(nodes[0]["stage"], "PLANNING")

    def test_gagal_pada_tahap_yang_sedang_berjalan(self):
        nodes = process_nodes(
            [{"kind": "agent", "stage": "RESEARCH", "role": "r",
              "provider": "p", "text": "x"},
             {"kind": "status", "text": "ANALISIS: memetakan"}],
            live_text="ANALISIS: memetakan", error="provider down")
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0]["status"], "completed")
        self.assertEqual(nodes[1]["status"], "failed")
        self.assertEqual(nodes[1]["info"], "provider down")

    def test_tahap_belum_dimulai_tidak_ditampilkan(self):
        # Larangan aktivitas palsu: PLANNING tanpa event tetap absent.
        nodes = process_nodes(
            [{"kind": "agent", "stage": "RESEARCH", "role": "r",
              "provider": "p", "text": "x"}])
        self.assertEqual([n["stage"] for n in nodes], ["RESEARCH"])


class EdgesTest(unittest.TestCase):
    def _prep(self, count):
        out = []
        for i in range(1, count + 1):
            node = {**PREP_NODES[i - 1], "i": i, "status": "completed",
                    "summary": ""}
            out.append(node)
        return out

    def test_fan_dan_rantai_tanpa_proses(self):
        edges = compute_edges(self._prep(4), [])
        fans = [e for e in edges if e[5] == "fan"]
        solids = [e for e in edges if e[5] == "solid"]
        self.assertEqual(len(fans), 4)
        self.assertEqual(len(solids), 3)  # b1→b2→b3→b4

    def test_jembatan_lewat_proses_menuju_hasil(self):
        proc = [{"status": "completed"}] * 3
        edges = compute_edges(self._prep(5), proc)
        # Pasangan (x, y) sumber→target: kolom persiapan berbagi x, jadi
        # dibedakan lewat y (b4=358, b5=458; proses1=102, proses3=302).
        pairs = [(round(e[0]), round(e[1]), round(e[2]), round(e[3]))
                 for e in edges if e[5] == "solid"]
        self.assertIn((550, 358, 650, 102), pairs)   # b4 → proses 1
        self.assertIn((930, 302, 330, 458), pairs)   # proses 3 → b5 (hasil)
        self.assertNotIn((550, 358, 330, 458), pairs)  # b4 → b5 langsung dilarang
        arrows = [e for e in edges if e[5] == "arrow"]
        self.assertEqual(len(arrows), 1)

    def test_svg_berisi_warna_status(self):
        proc = [{"status": "processing"}]
        svg = cables_svg(compute_edges(self._prep(4), proc))
        self.assertIn("#38bdf8", svg)   # proses (cyan)
        self.assertIn("#34d399", svg)   # selesai (hijau)
        self.assertIn("<svg", svg)


class ProjectStoreTest(unittest.TestCase):
    def test_memori_roundtrip(self):
        store = project_store.MemoryProjectStore()
        self.assertIsNone(store.load("u1"))
        store.save("u1", {"build_step": "form", "build_request": "catatan"})
        data = store.load("u1")
        self.assertEqual(data["build_step"], "form")

    def test_snapshot_dan_restore(self):
        ss = {"build_step": "reference", "build_request": "x",
              "other_key": 1}
        snap = project_store.snapshot_from(ss)
        self.assertIn("build_step", snap)
        self.assertNotIn("other_key", snap)
        fresh = {}
        project_store.restore_into(fresh, snap)
        self.assertEqual(fresh["build_step"], "reference")
        # Restore tidak menimpa state sesi yang sudah ada.
        project_store.restore_into({"build_step": "request"}, snap)
        # field non-JSON dibuang agar snapshot selalu aman
        bad = {"build_step": "request", "build_result": object()}
        json_ok = project_store.snapshot_from(bad)
        self.assertNotIn("build_result", json_ok)

    def test_save_project_fallback_memori_tanpa_supabase(self):
        # Tanpa SUPABASE_URL/KEY di lingkungan test → get_store None.
        err = project_store.save_project("u-test", {"build_step": "form"})
        self.assertIsNone(err)
        data, load_err = project_store.load_project("u-test")
        self.assertIsNone(load_err)
        self.assertEqual(data["build_step"], "form")


if __name__ == "__main__":
    unittest.main()
