"""Tampilan 'mesin' Council: kubus agen isometrik + jaringan hub + panel alur ala LangGraph.

Seperti ui/flow.py, modul ini hanya menghasilkan string SVG (tanpa memanggil Streamlit) dan
membaca status dari CouncilFlow, jadi bisa diuji tanpa UI. Kanvas kiri memperlihatkan 7 agen
sebagai kubus yang menyala sesuai status; panel kanan menampilkan alur keputusannya.
"""
import math

from ui.flow import DEBATERS, DONE, FAILED, NODES, PENDING, RUNNING, SKIPPED, _clip, _esc

W, H = 1000, 620          # ukuran viewBox
S = 62                    # tinggi sisi kubus
DX = S * math.sqrt(3) / 2  # setengah lebar kubus isometrik
DY = S / 2
SKEW = math.tan(math.radians(30))
HUB = (345.0, 300.0)

# Pusat tiap kubus (7 agen Council).
CUBES = {
    "orchestrator": (110, 150),
    "researcher":   (290, 80),
    "analyst":      (560, 110),
    "skeptic":      (610, 300),
    "expert":       (540, 490),
    "synthesizer":  (270, 520),
    "verifier":     (95, 380),
}

# (asal, tujuan, label, bias lengkung). bias > 0 melengkung ke hub, < 0 menjauh.
CUBE_EDGES = [
    ("orchestrator", "researcher", "butuh web", 0.45),
    ("researcher", "analyst", "", 0.45),
    ("researcher", "skeptic", "", 0.45),
    ("researcher", "expert", "", 0.45),
    ("analyst", "synthesizer", "", 0.45),
    ("skeptic", "synthesizer", "", 0.45),
    ("expert", "synthesizer", "", 0.45),
    ("synthesizer", "verifier", "", 0.45),
    ("verifier", "synthesizer", "revisi", -0.5),
]

STATE_WORD = {PENDING: "Menunggu", RUNNING: "Berjalan", DONE: "Selesai",
              FAILED: "Gagal", SKIPPED: "Dilewati"}

LG_X = 700  # geser panel alur ke kanan


def norm(state: str) -> str:
    """Status 'off' (belum tersentuh) ditampilkan sama seperti menunggu."""
    return PENDING if state not in STATE_WORD else state


def node_state(flow, node: str) -> str:
    if node == "verifier" and not flow.verify:
        return SKIPPED
    return norm(flow.state(node))


def debate_state(flow) -> str:
    states = [norm(flow.state(n)) for n in DEBATERS]
    if RUNNING in states:
        return RUNNING
    if FAILED in states and DONE not in states:
        return FAILED
    if all(s == SKIPPED for s in states):
        return SKIPPED
    if all(s in (DONE, SKIPPED) for s in states):
        return DONE
    return PENDING


def edge_cls(src: str, dst: str) -> str:
    """Kelas animasi sisi, aturannya sama dengan CouncilFlow.edge_state."""
    if dst == SKIPPED:
        return "skip"
    if dst == RUNNING:
        return "live"
    if FAILED in (src, dst):
        return "bad"
    if dst == DONE and src in (DONE, SKIPPED):
        return "hot"
    return "idle"


def _fit(text: str, size: float, maxw: float, bold: bool = False) -> str:
    """Atribut SVG yang memadatkan teks agar tidak keluar dari sisi kubus."""
    est = len(text) * size * (0.6 if bold else 0.54)
    if est > maxw:
        return f' textLength="{maxw:.0f}" lengthAdjust="spacingAndGlyphs"'
    return ""


def _split(text: str, width: int = 12) -> list:
    """Pecah teks pendek menjadi maksimal dua baris pada spasi terdekat dengan tengah."""
    text = _clip(text, width * 2)
    if len(text) <= width or " " not in text:
        return [text]
    mid = len(text) / 2
    cut = min((i for i, c in enumerate(text) if c == " "), key=lambda i: abs(i - mid))
    return [text[:cut].strip(), text[cut:].strip()]


def _qpath(a: tuple, b: tuple, k: float) -> tuple:
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    cx, cy = mx + (HUB[0] - mx) * k, my + (HUB[1] - my) * k
    path = f"M{a[0]:.0f},{a[1]:.0f} Q{cx:.0f},{cy:.0f} {b[0]:.0f},{b[1]:.0f}"
    lx = 0.25 * a[0] + 0.5 * cx + 0.25 * b[0]
    ly = 0.25 * a[1] + 0.5 * cy + 0.25 * b[1]
    return path, lx, ly


def mesh_points() -> tuple:
    """Titik jaringan hub: pusat, cincin dalam (6), cincin luar (8). Deterministik."""
    hx, hy = HUB
    ring1 = [(hx + 48 * math.cos(math.radians(30 + 60 * k)),
              hy + 48 * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    ring2 = [(hx + (100 + 12 * (k % 2)) * math.cos(math.radians(22.5 + 45 * k)),
              hy + (100 + 12 * (k % 2)) * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    return (hx, hy), ring1, ring2


def _nearest(point: tuple, pool: list, n: int) -> list:
    return sorted(pool, key=lambda q: (q[0] - point[0]) ** 2 + (q[1] - point[1]) ** 2)[:n]


def _mesh(live: bool) -> str:
    center, ring1, ring2 = mesh_points()
    lines = [(center, p) for p in ring1]
    lines += [(ring1[i], ring1[(i + 1) % 6]) for i in range(6)]
    lines += [(p, q) for p in ring1 for q in _nearest(p, ring2, 2)]
    lines += [(ring2[i], ring2[(i + 1) % 8]) for i in range(8)]
    for name, (cx, cy) in CUBES.items():  # tiap kubus tersambung samar ke hub
        lines.append(((cx, cy), _nearest((cx, cy), ring2, 1)[0]))
    cls = "aog-mesh aog-mesh-live" if live else "aog-mesh"
    out = [f'<g class="{cls}">']
    out += [f'<line x1="{a[0]:.0f}" y1="{a[1]:.0f}" x2="{b[0]:.0f}" y2="{b[1]:.0f}"></line>'
            for a, b in lines]
    out += [f'<circle cx="{p[0]:.0f}" cy="{p[1]:.0f}" r="3.6"></circle>' for p in ring1 + ring2]
    out.append(f'<circle class="aog-hubc" cx="{center[0]:.0f}" cy="{center[1]:.0f}" r="11"></circle>')
    out.append(f'<text class="aog-hubt" x="{center[0]:.0f}" y="{center[1] + 4:.0f}">State</text>')
    out.append("</g>")
    return "".join(out)


def _cube(flow, name: str) -> str:
    cx, cy = CUBES[name]
    state = node_state(flow, name)
    g = NODES[name]
    top = f"{cx},{cy - S} {cx + DX:.1f},{cy - DY} {cx},{cy} {cx - DX:.1f},{cy - DY}"
    left = f"{cx - DX:.1f},{cy - DY} {cx},{cy} {cx},{cy + S} {cx - DX:.1f},{cy + DY}"
    right = f"{cx},{cy} {cx + DX:.1f},{cy - DY} {cx + DX:.1f},{cy + DY} {cx},{cy + S}"
    parts = [f'<g class="aog-c aog-c-{state}">',
             f'<polygon class="f-left" points="{left}"></polygon>',
             f'<polygon class="f-right" points="{right}"></polygon>',
             f'<polygon class="f-top" points="{top}"></polygon>',
             f'<ellipse class="f-ring" cx="{cx}" cy="{cy - DY:.1f}" rx="{DX * .45:.1f}" '
             f'ry="{DY * .45:.1f}"></ellipse>']
    maxw = DX - 9
    label = g["label"]
    parts.append(f'<g transform="matrix(1,{SKEW:.4f},0,1,{cx - DX:.1f},{cy - DY:.1f})">'
                 f'<text class="c-lb" x="5" y="22"{_fit(label, 10, maxw, True)}>{_esc(label)}</text>')
    sub = flow.notes.get(name) or g["sub"]
    for i, line in enumerate(_split(sub)):
        parts.append(f'<text class="c-sb" x="5" y="{36 + 10 * i}"{_fit(line, 7, maxw)}>'
                     f'{_esc(line)}</text>')
    parts.append("</g>")
    prov = flow.providers.get(name, "")
    dur = flow.durations.get(name, "")
    word = STATE_WORD[state]
    parts.append(f'<g transform="matrix(1,{-SKEW:.4f},0,1,{cx},{cy})">'
                 f'<text class="c-st" x="5" y="24"{_fit(word, 10, maxw, True)}>{_esc(word)}</text>')
    if prov:
        parts.append(f'<text class="c-sb" x="5" y="37"{_fit(prov, 8, maxw)}>{_esc(prov)}</text>')
    if dur:
        parts.append(f'<text class="c-sb" x="5" y="49"{_fit(dur, 8, maxw)}>{_esc(dur)}</text>')
    parts.append("</g></g>")
    return "".join(parts)


# ---------------- panel alur ----------------
def _gbox(cx, cy, w, h, label, sub, state, pill=False) -> str:
    rx = h / 2 if pill else 10
    out = [f'<g class="aog-g aog-g-{state}">',
           f'<rect class="gb" x="{cx - w / 2:.0f}" y="{cy - h / 2:.0f}" width="{w}" height="{h}" '
           f'rx="{rx:.0f}"></rect>']
    if sub:
        out.append(f'<text class="gl" x="{cx}" y="{cy - 2}">{_esc(label)}</text>')
        out.append(f'<text class="gs" x="{cx}" y="{cy + 11}">{_esc(sub)}</text>')
    else:
        out.append(f'<text class="gl" x="{cx}" y="{cy + 4}">{_esc(label)}</text>')
    out.append("</g>")
    return "".join(out)


def _gdiamond(cx, cy, hw, hh, label, state) -> str:
    pts = f"{cx},{cy - hh} {cx + hw},{cy} {cx},{cy + hh} {cx - hw},{cy}"
    return (f'<g class="aog-g aog-g-{state}"><polygon class="gb" points="{pts}"></polygon>'
            f'<text class="gl" x="{cx}" y="{cy + 4}">{_esc(label)}</text></g>')


def _gedge(d: str, state: str, label: str = "", lx: float = 0, ly: float = 0) -> str:
    out = f'<path class="aog-e aog-e-{state}" d="{d}" marker-end="url(#mArr-{state})"></path>'
    if label:
        out += f'<text class="aog-el aog-el-{state}" x="{lx}" y="{ly}">{_esc(label)}</text>'
    return out


def _graph(flow) -> str:
    st = {n: node_state(flow, n) for n in NODES}
    s_start = DONE if flow.state("start") == DONE else PENDING
    s_orch, s_res = st["orchestrator"], st["researcher"]
    s_deb, s_syn = debate_state(flow), st["synthesizer"]
    s_ver, s_ans = st["verifier"], st["answer"]
    s_end = DONE if flow.finished and not flow.error else PENDING
    revisi = "hot" if flow.attempt > 0 else "idle"
    simple = s_deb == SKIPPED
    mid = edge_cls(s_orch, s_syn) if simple else "idle"

    out = [f'<g transform="translate({LG_X},0)">',
           '<rect class="aog-lgbg" x="0" y="10" width="300" height="600" rx="16"></rect>',
           '<text class="aog-lgt" x="150" y="40">Alur Council</text>']
    # sisi lebih dulu, lalu node di atasnya
    out.append(_gedge("M150,92 L150,118", edge_cls(s_start, s_start)))
    out.append(_gedge("M150,148 L150,186", edge_cls(s_start, s_orch)))
    out.append(_gedge("M88,215 C62,215 62,236 62,258", edge_cls(s_orch, s_res), "butuh web", 30, 232))
    out.append(_gedge("M212,215 C238,215 238,236 238,258", edge_cls(s_orch, s_deb)))
    out.append(_gedge("M150,245 L150,328", mid, "sederhana", 150, 300) if simple else
               _gedge("M150,245 L150,328", "idle"))
    out.append(_gedge("M62,292 C62,318 72,336 86,336", edge_cls(s_res, s_syn)))
    out.append(_gedge("M238,292 C238,318 228,336 214,336", edge_cls(s_deb, s_syn)))
    out.append(_gedge("M150,354 L150,386", edge_cls(s_syn, s_ver)))
    out.append(_gedge("M150,452 L150,484", edge_cls(s_ver, s_ans), "lolos", 176, 472))
    out.append(_gedge("M150,518 L150,546", edge_cls(s_ans, s_end)))
    out.append(_gedge("M212,419 C292,419 292,336 214,336", revisi, "revisi", 274, 382))
    out.append(_gbox(150, 74, 120, 30, "START", "", s_start, pill=True))
    out.append(_gbox(150, 133, 140, 30, "State", "", s_start))
    out.append(_gdiamond(150, 215, 66, 30, "Orchestrator", s_orch))
    out.append(_gbox(62, 275, 108, 34, "Researcher", "", s_res))
    out.append(_gbox(238, 275, 108, 34, "Debat 3 agen", "", s_deb))
    out.append(_gbox(150, 336, 128, 34, "Penyusun", "", s_syn))
    out.append(_gdiamond(150, 419, 66, 33, "Verifier", s_ver))
    out.append(_gbox(150, 501, 128, 34, "Jawaban final", "", s_ans))
    out.append(_gbox(150, 562, 120, 30, "END", "", s_end, pill=True))
    out.append("</g>")
    return "".join(out)


def _defs() -> str:
    markers = "".join(
        f'<marker id="mArr-{name}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" '
        f'markerHeight="6" orient="auto"><path d="M0,1 L9,5 L0,9 z" fill="{color}"></path></marker>'
        for name, color in (("idle", "#2c4366"), ("hot", "#3b82f6"), ("live", "#38bdf8"),
                            ("bad", "#f87171"), ("skip", "#22324a")))
    return ('<defs><filter id="aogGlow" x="-60%" y="-60%" width="220%" height="220%">'
            '<feGaussianBlur stdDeviation="3.5" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
            '<pattern id="mGrid" width="40" height="40" patternUnits="userSpaceOnUse">'
            '<path d="M40,0 L0,0 L0,40" fill="none" stroke="#10213a" stroke-width="1"></path>'
            '</pattern>'
            '<radialGradient id="mGlowBg" cx="35%" cy="48%" r="60%">'
            '<stop offset="0" stop-color="#0d2b4a" stop-opacity=".75"></stop>'
            '<stop offset="1" stop-color="#050b14" stop-opacity="0"></stop></radialGradient>'
            f'{markers}</defs>')


def render(flow) -> str:
    """SVG lengkap: kanvas kubus di kiri, panel alur di kanan."""
    live = any(norm(flow.state(n)) == RUNNING for n in CUBES)
    if flow.error:
        status = "Berhenti karena galat"
    elif flow.finished:
        status = "Selesai"
    else:
        status = flow.stage_text or "Menunggu pertanyaan"
    parts = [f'<svg class="aog-svgm" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">',
             _defs(),
             f'<rect width="{W}" height="{H}" fill="url(#mGrid)"></rect>',
             f'<rect width="{W}" height="{H}" fill="url(#mGlowBg)"></rect>',
             '<text class="aog-mt" x="22" y="32">Mesin Council</text>',
             f'<text class="aog-ms" x="22" y="52">{_esc(_clip(status, 34))}</text>']
    parts.append(_mesh(live))
    for src, dst, label, bias in CUBE_EDGES:
        a, b = CUBES[src], CUBES[dst]
        state = edge_cls(node_state(flow, src), node_state(flow, dst))
        if src == "verifier":  # sisi revisi hanya menyala bila memang ada putaran ulang
            state = "hot" if flow.attempt > 0 else "idle"
        path, lx, ly = _qpath(a, b, bias)
        parts.append(f'<path class="aog-e aog-e-{state}" d="{path}"></path>')
        if label:
            parts.append(f'<text class="aog-el aog-el-{state}" x="{lx:.0f}" y="{ly - 6:.0f}">'
                         f'{_esc(label)}</text>')
    for name in CUBES:
        parts.append(_cube(flow, name))
    parts.append(_graph(flow))
    parts.append("</svg>")
    return "".join(parts)


CSS = """
<style>
.aog-svgm { width:100%; height:auto; display:block; max-height:calc(100vh - 260px); }
.aog-mt { fill:#e2e8f0; font-size:15px; font-weight:700; letter-spacing:.6px; }
.aog-ms { fill:#7dd3fc; font-size:11px; }
.aog-mesh line { stroke:#1b5f93; stroke-opacity:.5; stroke-width:1.1; }
.aog-mesh circle { fill:#38bdf8; fill-opacity:.85; }
.aog-mesh .aog-hubc { fill:#0b2238; stroke:#38bdf8; stroke-width:1.6; }
.aog-mesh .aog-hubt { fill:#9be3ff; font-size:7.5px; font-weight:700; text-anchor:middle; }
.aog-mesh-live line { stroke-opacity:.9; stroke-dasharray:4 6; animation:aogdash 1.2s linear infinite; }
.aog-mesh-live circle { animation:aogblink 1.4s ease-in-out infinite; }

.aog-c polygon { stroke-width:1.1; stroke-linejoin:round; transition:fill .35s ease; }
.aog-c .f-ring { fill:none; stroke-width:1.6; }
.aog-c text { font-family:Inter,ui-sans-serif,system-ui,sans-serif; pointer-events:none; }
.aog-c .c-lb { font-size:10px; font-weight:700; fill:#e8f3ff; }
.aog-c .c-st { font-size:10px; font-weight:700; fill:#e8f3ff; }
.aog-c .c-sb { font-size:7px; fill:#b7d3f0; }
.aog-c-pending .f-top { fill:#16294a; stroke:#2b4c7c; }
.aog-c-pending .f-left { fill:#0d1b34; stroke:#2b4c7c; }
.aog-c-pending .f-right { fill:#0a152a; stroke:#2b4c7c; }
.aog-c-pending .f-ring { stroke:#2f5c96; }
.aog-c-pending text { fill:#8fa8cc; }
.aog-c-running { filter:url(#aogGlow); }
.aog-c-running .f-top { fill:#4cc9ff; stroke:#a5e9ff; }
.aog-c-running .f-left { fill:#1a78c9; stroke:#a5e9ff; }
.aog-c-running .f-right { fill:#1160b0; stroke:#a5e9ff; }
.aog-c-running .f-ring { stroke:#ffffff; animation:aogpulse 1.3s ease-in-out infinite; }
.aog-c-done .f-top { fill:#3ddc97; stroke:#98f0c8; }
.aog-c-done .f-left { fill:#138a62; stroke:#98f0c8; }
.aog-c-done .f-right { fill:#0e6e4f; stroke:#98f0c8; }
.aog-c-done .f-ring { stroke:#eafff5; }
.aog-c-failed .f-top { fill:#fb7185; stroke:#fecdd3; }
.aog-c-failed .f-left { fill:#b83a4b; stroke:#fecdd3; }
.aog-c-failed .f-right { fill:#952f3e; stroke:#fecdd3; }
.aog-c-failed .f-ring { stroke:#fff1f2; }
.aog-c-skipped .f-top { fill:#243146; stroke:#33445f; }
.aog-c-skipped .f-left { fill:#18222f; stroke:#33445f; }
.aog-c-skipped .f-right { fill:#141c28; stroke:#33445f; }
.aog-c-skipped .f-ring { stroke:#3b4d69; stroke-dasharray:3 3; }
.aog-c-skipped text { fill:#5d6f8a; }

.aog-lgbg { fill:#07101d; fill-opacity:.82; stroke:#17283f; }
.aog-lgt { fill:#f1f5f9; font-size:17px; font-weight:800; text-anchor:middle; }
.aog-g .gb { fill:#0e1a2e; stroke:#2d4a73; stroke-width:1.4; transition:all .35s ease; }
.aog-g .gl { fill:#a9bfdf; font-size:11px; font-weight:600; text-anchor:middle; }
.aog-g .gs { fill:#5f7798; font-size:8.5px; text-anchor:middle; }
.aog-g-running .gb { fill:#0b2a44; stroke:#38bdf8; stroke-width:1.8; filter:url(#aogGlow); }
.aog-g-running .gl { fill:#e0f2fe; }
.aog-g-done .gb { fill:#0a2a24; stroke:#2dd4a0; }
.aog-g-done .gl { fill:#d1fae5; }
.aog-g-failed .gb { fill:#2a1219; stroke:#f87171; }
.aog-g-failed .gl { fill:#fecaca; }
.aog-g-skipped .gb { fill:#0a111d; stroke:#2b3a52; stroke-dasharray:3 5; }
.aog-g-skipped .gl { fill:#4d5f79; }
</style>
"""
