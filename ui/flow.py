"""Graf proses Council: node + sisi bercahaya yang berubah status saat pipeline berjalan.

Modul ini hanya menghasilkan string HTML/SVG (tidak memanggil Streamlit) supaya bisa
diuji tanpa UI. App memanggil CouncilFlow.consume(event) lalu render() tiap ada perubahan.
"""
import copy
import html
import json
import time

PENDING = "pending"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
SKIPPED = "skipped"

# Posisi tiap agen pada kanvas (koordinat viewBox 1130 x 300).
NODES = {
    "start":        {"label": "Mulai",        "sub": "pertanyaan + riwayat", "x": 12,  "y": 126, "w": 60,  "h": 44},
    "orchestrator": {"label": "Orchestrator", "sub": "rencana & fokus",      "x": 94,  "y": 126, "w": 150, "h": 44},
    "researcher":   {"label": "Researcher",   "sub": "riset web (opsional)", "x": 266, "y": 126, "w": 150, "h": 44},
    "analyst":      {"label": "Analis",       "sub": "penalaran langkah",    "x": 452, "y": 6,   "w": 164, "h": 44},
    "skeptic":      {"label": "Skeptis",      "sub": "bantahan & risiko",    "x": 452, "y": 126, "w": 164, "h": 44},
    "expert":       {"label": "Pakar",        "sub": "pengetahuan domain",   "x": 452, "y": 246, "w": 164, "h": 44},
    "synthesizer":  {"label": "Penyusun",     "sub": "gabungkan diskusi",    "x": 644, "y": 126, "w": 150, "h": 44},
    "verifier":     {"label": "Verifier",     "sub": "skor kualitas",        "x": 814, "y": 126, "w": 150, "h": 44},
    "answer":       {"label": "Jawaban final", "sub": "hasil council",       "x": 984, "y": 126, "w": 126, "h": 44},
}

DEBATERS = ["analyst", "skeptic", "expert"]
ROLE_TO_NODE = {"Orchestrator": "orchestrator", "Researcher": "researcher", "Analis": "analyst",
                "Skeptis": "skeptic", "Pakar": "expert", "Penyusun": "synthesizer",
                "Verifier": "verifier", "Council": "answer"}

# (asal, tujuan, keluar_dari, masuk_ke, label, posisi_label)
EDGES = [
    ("start", "orchestrator", "right", "left", "", None),
    ("orchestrator", "researcher", "right", "left", "butuh web", "above"),
    ("researcher", "analyst", "right", "left", "", None),
    ("researcher", "skeptic", "right", "left", "", None),
    ("researcher", "expert", "right", "left", "", None),
    ("analyst", "synthesizer", "right", "left", "", None),
    ("skeptic", "synthesizer", "right", "left", "", None),
    ("expert", "synthesizer", "right", "left", "", None),
    ("synthesizer", "verifier", "right", "left", "", None),
    ("verifier", "answer", "right", "left", "lolos", "above"),
    ("verifier", "synthesizer", "bottom", "bottom", "revisi", "below"),
]


def _esc(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def _clip(text, n: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def _dur(seconds: float) -> str:
    return f"{seconds:.1f}s" if seconds < 10 else f"{seconds:.0f}s"


def _anchor(node: dict, side: str) -> tuple:
    if side == "right":
        return node["x"] + node["w"], node["y"] + node["h"] / 2
    if side == "left":
        return node["x"], node["y"] + node["h"] / 2
    if side == "top":
        return node["x"] + node["w"] / 2, node["y"]
    return node["x"] + node["w"] / 2, node["y"] + node["h"]


def _edge_path(a: dict, b: dict, out: str, inn: str) -> str:
    x1, y1 = _anchor(a, out)
    x2, y2 = _anchor(b, inn)
    if out == "right" and inn == "left":
        mx = (x1 + x2) / 2
        return f"M{x1:.0f},{y1:.0f} C{mx:.0f},{y1:.0f} {mx:.0f},{y2:.0f} {x2:.0f},{y2:.0f}"
    if out == "bottom" and inn == "bottom":
        dip = max(y1, y2) + 24
        return f"M{x1:.0f},{y1:.0f} C{x1:.0f},{dip:.0f} {x2:.0f},{dip:.0f} {x2:.0f},{y2:.0f}"
    if out == "top" and inn == "top":
        rise = min(y1, y2) - 22
        return f"M{x1:.0f},{y1:.0f} C{x1:.0f},{rise:.0f} {x2:.0f},{rise:.0f} {x2:.0f},{y2:.0f}"
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    return f"M{x1:.0f},{y1:.0f} C{mx:.0f},{my:.0f} {mx:.0f},{y2:.0f} {x2:.0f},{y2:.0f}"


class CouncilFlow:
    """Penerjemah event pipeline -> status node, daftar log, dan HTML graf."""

    def __init__(self, question: str = "", mode_name: str = "Seimbang",
                 rounds: int = 2, verify: bool = True, max_retries: int = 1):
        self.question = question
        self.mode_name = mode_name
        self.rounds = max(1, rounds)
        self.verify = verify
        self.max_retries = max_retries
        self.states = {name: "off" for name in NODES}
        self.providers = {}
        self.notes = {}
        self.durations = {}
        self.log = []
        self.round_no = 0
        self.attempt = 0
        self.score = None
        self.issues = []
        self.sources = []
        self.error = ""
        self.finished = False
        self.stage_text = ""
        self.t0 = time.time()
        self._t_last = self.t0
        self._elapsed = 0.0
        self._running_at = {}
        self.states["start"] = DONE
        self.states["orchestrator"] = PENDING

    # ---------- status ----------
    def set(self, node: str, state: str, provider: str = "", note: str = ""):
        if node not in self.states:
            return
        if state == RUNNING and self.states[node] != RUNNING:
            self._running_at[node] = time.time()
        self.states[node] = state
        if provider and provider != "-":
            self.providers[node] = provider
        if note:
            self.notes[node] = _clip(note, 46)
        if state in (DONE, FAILED, SKIPPED) and node in self._running_at:
            self.durations[node] = _dur(time.time() - self._running_at.pop(node))

    def state(self, node: str) -> str:
        return self.states.get(node, "off")

    def note(self, node: str, text: str):
        if node in self.states:
            self.notes[node] = _clip(text, 46)

    def finish(self, nodes, state: str = DONE, provider: str = "", note: str = ""):
        for node in nodes:
            self.set(node, state, provider, note)

    def _quiesce(self, keep=()):
        """Node yang sedang berjalan tapi bukan bagian tahap baru dianggap selesai."""
        for node, state in list(self.states.items()):
            if state == RUNNING and node not in keep:
                self.set(node, DONE)

    def begin_stage(self, nodes, round_no: int = 0, again: bool = False):
        """Nyalai node tahap baru. `again=True`: nyalakan ulang walau sudah pernah selesai."""
        if round_no:
            self.round_no = round_no
        self._quiesce(nodes)
        for node in nodes:
            state = self.state(node)
            if state in ("off", PENDING) or (again and state in (DONE, FAILED)):
                self.set(node, RUNNING)

    FIELDS = ("states", "providers", "notes", "durations", "log", "score", "issues", "sources",
              "error", "finished", "mode_name", "rounds", "verify", "max_retries", "round_no",
              "attempt", "stage_text", "_elapsed")

    def snapshot(self) -> dict:
        """Salinan data (bukan objek) supaya proses bisa ditampilkan ulang dari riwayat chat."""
        return {k: copy.deepcopy(getattr(self, k)) for k in self.FIELDS}

    @classmethod
    def restore(cls, data: dict, question: str = "") -> "CouncilFlow":
        flow = cls(question=question, mode_name=data.get("mode_name", "Seimbang"))
        flow.__dict__.update(copy.deepcopy(data))
        flow.finished = True
        return flow

    def preview(self):
        """Semua node redup: dipakai saat belum ada pertanyaan."""
        for name in NODES:
            self.states[name] = PENDING

    def skip(self, node: str, why: str = "dilewati"):
        if self.state(node) in ("off", PENDING):
            self.set(node, SKIPPED, note=why)

    # ---------- event pipeline ----------
    def consume(self, ev: dict) -> str:
        """Terapkan satu event. Nilai kembali: '', 'log', 'final', 'error' (petunjuk render)."""
        kind = ev.get("kind")
        if kind == "status":
            self._apply_status(ev.get("text", ""))
            return ""
        if kind == "agent":
            self._apply_agent(ev)
            return "log"
        if kind == "error":
            self.error = ev.get("text", "")
            for node, state in list(self.states.items()):
                if state == RUNNING:
                    self.set(node, FAILED)
            self._push("Sistem", "Galat", "-", self.error, bad=True)
            return "error"
        if kind == "final":
            self.score = ev.get("score")
            self.issues = list(ev.get("issues") or [])
            self.sources = list(ev.get("sources") or [])
            self._quiesce()
            self.set("answer", DONE, provider=",".join(ev.get("providers") or []),
                     note=ev.get("answer", ""))
            self.finished = True
            self._elapsed = time.time() - self.t0
            return "final"
        return ""

    def _apply_agent(self, ev: dict):
        stage, role = ev.get("stage", ""), ev.get("role", "")
        prov, text = ev.get("provider", ""), ev.get("text", "")
        bad = text.startswith("(gagal")
        node = ROLE_TO_NODE.get(role)
        if stage == "Perencanaan" and node:
            self._read_plan(text)
            self.set(node, FAILED if bad else DONE, prov)
        elif node:
            self.set(node, FAILED if bad else DONE, prov, "" if bad else text)
        self._push(role, stage, prov, text, bad=bad)

    def _read_plan(self, text: str):
        """Baca JSON rencana orchestrator: node mana yang akan dilewati."""
        try:
            plan = json.loads("".join(str(text).split("```")[1:2]) or text)
        except (ValueError, IndexError, TypeError):
            plan = {}
        if not isinstance(plan, dict):
            plan = {}
        if not plan:
            return
        simple = plan.get("complexity") == "simple"
        self.note("orchestrator", f'{plan.get("category", "?")} · {plan.get("complexity", "?")}')
        if not plan.get("needs_web"):
            self.skip("researcher", "tidak butuh web")
        if simple:
            for node in DEBATERS:
                self.skip(node, "pertanyaan sederhana")
            self.note("synthesizer", "langsung dari rencana")
        elif plan.get("focus_points"):
            self.note("synthesizer", "; ".join(plan["focus_points"])[:46])

    def _apply_status(self, text: str):
        self.stage_text = text
        t = text.lower()
        if "menganalisis" in t:
            self.begin_stage(["orchestrator"])
        elif "mencari sumber" in t:
            self.begin_stage(["researcher"])
        elif "berdiskusi" in t:
            num = next((int(c) for c in text if c.isdigit()), 1)
            self.begin_stage(DEBATERS, round_no=num, again=num > 1)
            for node in DEBATERS:
                self.note(node, f"putaran {num} · 3 agen paralel")
            self.set("orchestrator", DONE)
            self.set("researcher", DONE if self.state("researcher") == RUNNING else
                     self.state("researcher"))
        elif "menyusun" in t:
            self.begin_stage(["synthesizer"])
            self._quiesce(["synthesizer"])
        elif "memeriksa" in t:
            if not self.verify:
                return
            self.begin_stage(["verifier"])
        elif "direvisi" in t:
            self.attempt += 1
            self.set("verifier", PENDING)
            self.begin_stage(["synthesizer"], again=True)
            self.note("verifier", f"skor di bawah ambang → revisi {self.attempt}")

    def _push(self, role: str, stage: str, provider: str, text: str, bad: bool = False):
        self.log.append({"dt": time.time() - self._t_last, "role": role or "?", "stage": stage,
                         "provider": provider or "-", "text": _clip(text, 900), "bad": bad})
        self._t_last = time.time()

    # ---------- ringkasan ----------
    @property
    def elapsed(self) -> float:
        return self._elapsed if self.finished else time.time() - self.t0

    def chips(self) -> list:
        return [("Mode", self.mode_name),
                ("Putaran", f"{self.round_no or 1}/{self.rounds}"),
                ("Revisi", str(self.attempt)),
                ("Sumber", str(len(self.sources))),
                ("Skor", "—" if self.score is None else f"{self.score:.0%}"),
                ("Durasi", _dur(self.elapsed)),
                ("Provider", ", ".join(sorted(set(self.providers.values()))) or "—")]

    def edge_state(self, src: str, dst: str) -> str:
        s, d = self.state(src), self.state(dst)
        if "off" in (s, d):
            return "off"
        if d == SKIPPED:
            return "skip"
        if d == RUNNING:
            return "live"
        if d == FAILED or s == FAILED:
            return "bad"
        if d == DONE and s in (DONE, SKIPPED):
            return "hot"
        if d == PENDING:
            return "idle"
        return "idle"

    # ---------- render ----------
    def render(self) -> str:
        parts = ['<svg class="aog-svg" viewBox="0 0 1130 300" '
                 'preserveAspectRatio="xMidYMid meet"><defs>'
                 '<filter id="aogGlow" x="-60%" y="-60%" width="220%" height="220%">'
                 '<feGaussianBlur stdDeviation="3.5" result="b"/>'
                 '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
                 '</filter></defs>']
        for src, dst, out, inn, label, lpos in EDGES:
            state = self.edge_state(src, dst)
            if state == "off":
                continue
            parts.append(f'<path class="aog-e aog-e-{state}" '
                         f'd="{_edge_path(NODES[src], NODES[dst], out, inn)}"></path>')
            if label:
                a, b = NODES[src], NODES[dst]
                if lpos == "above":
                    lx, ly = (a["x"] + a["w"] + b["x"]) / 2, min(a["y"], b["y"]) - 6
                else:
                    lx = (a["x"] + a["w"] / 2 + b["x"] + b["w"] / 2) / 2
                    ly = max(a["y"] + a["h"], b["y"] + b["h"]) + 30
                parts.append(f'<text class="aog-el aog-el-{state}" x="{lx:.0f}" '
                             f'y="{ly:.0f}">{_esc(label)}</text>')
        for name, g in NODES.items():
            state = self.state(name)
            if state == "off":
                continue
            x, y, w, h = g["x"], g["y"], g["w"], g["h"]
            parts.append(f'<g class="aog-n aog-n-{state}" transform="translate({x},{y})">')
            parts.append(f'<rect class="aog-box" width="{w}" height="{h}" rx="11"></rect>')
            parts.append(f'<circle class="aog-dot" cx="{w - 13}" cy="12" r="4"></circle>')
            parts.append(f'<text class="aog-lb" x="12" y="19">{_esc(g["label"])}</text>')
            sub = self.notes.get(name) or self.providers.get(name) or g["sub"]
            parts.append(f'<text class="aog-sb" x="12" y="35">{_esc(_clip(sub, 42))}</text>')
            tag = " · ".join(filter(None, [self.providers.get(name), self.durations.get(name)]))
            if tag:
                parts.append(f'<text class="aog-tg" x="{w - 12}" y="{h - 5}" '
                             f'text-anchor="end">{_esc(tag)}</text>')
            parts.append("</g>")
        parts.append("</svg>")
        return "".join(parts)

    def render_log(self, limit: int = 30) -> str:
        rows = []
        for e in self.log[-limit:]:
            rows.append(
                f'<div class="aog-row{" aog-bad" if e["bad"] else ""}">'
                f'<span class="aog-t">+{e["dt"]:.1f}s</span>'
                f'<span class="aog-r">{_esc(e["role"])}</span>'
                f'<span class="aog-s">{_esc(e["stage"])}</span>'
                f'<span class="aog-p">{_esc(e["provider"])}</span>'
                f'<span class="aog-x">{_esc(e["text"])}</span></div>')
        if not rows:
            rows.append('<div class="aog-row aog-empty"><span class="aog-x">'
                        'Belum ada langkah. Kirim pertanyaan untuk melihat prosesnya secara langsung.'
                        '</span></div>')
        return '<div class="aog-log">' + "".join(rows) + "</div>"

    def render_chips(self) -> str:
        cells = "".join(f'<div class="aog-chip"><span>{_esc(k)}</span><b>{_esc(v)}</b></div>'
                        for k, v in self.chips())
        return f'<div class="aog-chips">{cells}</div>'
