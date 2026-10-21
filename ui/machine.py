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
    # Tata letak kartu pipeline mengikuti komposisi bertingkat pada gambar referensi.
    "orchestrator": (120, 125),
    "researcher":   (365, 125),
    "expert":       (600, 125),
    "analyst":      (120, 315),
    "skeptic":      (365, 315),
    "synthesizer":  (600, 315),
    "verifier":     (365, 505),
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
    """Kabel halus antarkartu; masuk/keluar dari tepi kartu, bukan menembus tengahnya."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    width, height = 190 / 2, 90 / 2
    scale = min(width / max(abs(dx), 1), height / max(abs(dy), 1))
    x1, y1 = a[0] + dx * scale, a[1] + dy * scale
    x2, y2 = b[0] - dx * scale, b[1] - dy * scale
    mx = (x1 + x2) / 2
    path = f"M{x1:.0f},{y1:.0f} C{mx:.0f},{y1:.0f} {mx:.0f},{y2:.0f} {x2:.0f},{y2:.0f}"
    return path, mx, (y1 + y2) / 2


def _wire(path: str, state: str) -> str:
    """Kabel berlapis neon dengan partikel listrik yang terus bergerak di sepanjang jalur."""
    if state in ("skip",):
        return f'<path class="aog-e aog-e-{state}" d="{path}"></path>'
    return (f'<path class="aog-e-glow aog-e-{state}" d="{path}"></path>'
            f'<path class="aog-e aog-e-{state}" d="{path}"></path>'
            f'<circle class="aog-e-particle aog-p-{state}" r="3.2">'
            f'<animateMotion dur="2.4s" repeatCount="indefinite" path="{path}"></animateMotion>'
            '</circle>'
            f'<circle class="aog-e-particle aog-p-soft aog-p-{state}" r="1.8">'
            f'<animateMotion dur="3.7s" begin="-1.1s" repeatCount="indefinite" path="{path}"></animateMotion>'
            '</circle>')


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
    """Latar jaringan berupa jalur sirkuit lurus dan titik cahaya, tanpa hub melingkar."""
    cls = "aog-mesh aog-mesh-live" if live else "aog-mesh"
    parts = [f'<g class="{cls}">']
    # Grid elektrik tipis dan titik-titik kecil memberi kedalaman tanpa node melingkar.
    for x in range(20, 700, 40):
        parts.append(f'<line x1="{x}" y1="55" x2="{x}" y2="570"></line>')
    for y in range(60, 600, 40):
        parts.append(f'<line x1="20" y1="{y}" x2="690" y2="{y}"></line>')
    for x, y in ((55, 90), (230, 250), (510, 75), (680, 230), (250, 555), (640, 550)):
        parts.append(f'<circle cx="{x}" cy="{y}" r="2.2"></circle>')
    parts.append("</g>")
    return "".join(parts)


def _cube(flow, name: str) -> str:
    """Kartu agen bergaya node neon, terinspirasi diagram jaringan pada referensi."""
    cx, cy = CUBES[name]
    state = node_state(flow, name)
    g = NODES[name]
    width, height = 190, 90
    x, y = cx - width / 2, cy - height / 2
    label = g["label"]
    sub = flow.notes.get(name) or g["sub"]
    word = STATE_WORD[state]
    prov = flow.providers.get(name, "")
    dur = flow.durations.get(name, "")
    parts = [f'<g class="aog-c aog-agent-{name} aog-c-{state}">',
             f'<rect class="f-card" x="{x:.0f}" y="{y:.0f}" width="{width}" height="{height}" rx="13"></rect>',
             f'<rect class="f-inset" x="{x + 5:.0f}" y="{y + 5:.0f}" width="{width - 10}" '
             f'height="{height - 10}" rx="10"></rect>',
             f'<circle class="f-dot" cx="{x + 17:.0f}" cy="{cy:.0f}" r="4"></circle>',
             f'<text class="c-lb" x="{cx:.0f}" y="{cy - 9:.0f}" text-anchor="middle">{_esc(label)}</text>',
             f'<text class="c-sb" x="{cx:.0f}" y="{cy + 8:.0f}" text-anchor="middle">{_esc(_clip(sub, 24))}</text>',
             f'<text class="c-st" x="{cx:.0f}" y="{cy + 25:.0f}" text-anchor="middle">{_esc(word)}'
             f'{(" · " + _esc(prov)) if prov else ""}{(" · " + _esc(dur)) if dur else ""}</text>',
             '</g>']
    return "".join(parts)


def _terminal(flow, name: str, cx: int, cy: int, label: str, sub: str) -> str:
    """Kartu input/output pada kanvas utama, agar alur berawal dan berakhir di diagram."""
    state = norm(flow.state(name))
    x, y, w, h = cx - 95, cy - 45, 190, 90
    return (f'<g class="aog-c aog-terminal aog-terminal-{name} aog-c-{state}">'
            f'<rect class="f-card" x="{x}" y="{y}" width="{w}" height="{h}" rx="13"></rect>'
            f'<rect class="f-inset" x="{x + 5}" y="{y + 5}" width="{w - 10}" height="{h - 10}" rx="10"></rect>'
            f'<circle class="f-dot" cx="{x + 17}" cy="{cy}" r="4"></circle>'
            f'<text class="c-lb" x="{cx}" y="{cy - 5}" text-anchor="middle">{_esc(label)}</text>'
            f'<text class="c-sb" x="{cx}" y="{cy + 15}" text-anchor="middle">{_esc(sub)}</text>'
            '</g>')


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
    out = _wire(d, state)
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
            '<radialGradient id="mGlowBg" cx="35%" cy="48%" r="70%">'
            '<stop offset="0" stop-color="#21164a" stop-opacity=".78"></stop>'
            '<stop offset=".58" stop-color="#101d3c" stop-opacity=".48"></stop>'
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
    # Koneksi masuk/keluar; sudut membulat menyerupai kabel pada workflow referensi.
    for src, dst, a, b in (("start", "orchestrator", (120, 505), CUBES["orchestrator"]),
                           ("verifier", "answer", CUBES["verifier"], (600, 505))):
        state = edge_cls(node_state(flow, src), node_state(flow, dst))
        path, _, _ = _qpath(a, b, 0)
        parts.append(_wire(path, state))
    for src, dst, label, bias in CUBE_EDGES:
        a, b = CUBES[src], CUBES[dst]
        state = edge_cls(node_state(flow, src), node_state(flow, dst))
        if src == "verifier":  # sisi revisi hanya menyala bila memang ada putaran ulang
            state = "hot" if flow.attempt > 0 else "idle"
        path, lx, ly = _qpath(a, b, bias)
        parts.append(_wire(path, state))
        if label:
            parts.append(f'<text class="aog-el aog-el-{state}" x="{lx:.0f}" y="{ly - 6:.0f}">'
                         f'{_esc(label)}</text>')
    # Node input/output menempati posisi kartu tersendiri seperti pada gambar acuan.
    parts.append(_terminal(flow, "start", 120, 505, "User Input", "Pertanyaan pengguna"))
    for name in CUBES:
        parts.append(_cube(flow, name))
    parts.append(_terminal(flow, "answer", 600, 505, "Jawaban final", "Council response"))
    parts.append(_graph(flow))
    parts.append("</svg>")
    return "".join(parts)


CSS = """
<style>
.aog-svgm { width:100%; height:auto; display:block; max-height:calc(100vh - 260px); }
.aog-mt { fill:#f1eaff; font-size:15px; font-weight:700; letter-spacing:.6px; }
.aog-ms { fill:#83dfff; font-size:11px; }
.aog-mesh line { stroke:#5846a2; stroke-opacity:.13; stroke-width:.8; }
.aog-mesh circle { fill:#a879ff; fill-opacity:.9; filter:url(#aogGlow); }
.aog-mesh .aog-hubc { fill:#160d37; stroke:#d36dff; stroke-width:1.8; }
.aog-mesh .aog-hubt { fill:#f3c5ff; font-size:7.5px; font-weight:700; text-anchor:middle; }
.aog-mesh-live line { stroke:#42d9ff; stroke-opacity:1; stroke-dasharray:4 6; animation:aogdash 1.2s linear infinite; }
.aog-mesh-live circle { fill:#42d9ff; animation:aogblink 1.4s ease-in-out infinite; }

.aog-c text { font-family:Inter,ui-sans-serif,system-ui,sans-serif; pointer-events:none; }
.aog-c .f-card { fill:#101532; stroke:#7661ff; stroke-width:2.2; transition:all .35s ease; }
.aog-c .f-inset { fill:#171c48; fill-opacity:.9; stroke:#5a49d4; stroke-width:1.2; }
.aog-c .f-dot { fill:#46dcff; filter:url(#aogGlow); }
.aog-c .c-lb { font-size:14px; font-weight:750; fill:#f3f2ff; }
.aog-c .c-st { font-size:9px; font-weight:700; fill:#a9b8e5; }
.aog-c .c-sb { font-size:10px; fill:#9da9d8; }
.aog-agent-orchestrator .f-card, .aog-agent-verifier .f-card { stroke:#36cfff; }
.aog-agent-orchestrator .f-inset, .aog-agent-verifier .f-inset { stroke:#198dcf; fill:#102955; }
.aog-agent-researcher .f-card, .aog-agent-skeptic .f-card { stroke:#d45bff; }
.aog-agent-researcher .f-inset, .aog-agent-skeptic .f-inset { stroke:#a53cf2; fill:#271548; }
.aog-agent-analyst .f-card, .aog-agent-expert .f-card { stroke:#ffad38; }
.aog-agent-analyst .f-inset, .aog-agent-expert .f-inset { stroke:#ed772b; fill:#3b1d26; }
.aog-agent-synthesizer .f-card { stroke:#ff5ca8; }
.aog-agent-synthesizer .f-inset { stroke:#ce378c; fill:#321638; }
.aog-terminal-start .f-card { stroke:#ff9e43; }
.aog-terminal-start .f-inset { stroke:#da6634; fill:#3c201d; }
.aog-terminal-answer .f-card { stroke:#ff6ba9; }
.aog-terminal-answer .f-inset { stroke:#ce438d; fill:#321839; }
.aog-c-pending .f-card { fill:#0c1128; stroke-opacity:.82; }
.aog-c-pending .f-inset { fill:#111631; }
.aog-c-running { filter:url(#aogGlow); }
.aog-c-running .f-card { fill:#102c52; stroke:#78f2ff; stroke-width:2.7; animation:aogpulse 1.3s ease-in-out infinite; }
.aog-c-running .f-inset { fill:#124878; stroke:#a4f7ff; }
.aog-c-running .f-dot { fill:#fff; }
.aog-c-running text { fill:#fff; }
.aog-c-done .f-card { fill:#0d382f; stroke:#45f2b0; }
.aog-c-done .f-inset { fill:#105544; stroke:#74ffd0; }
.aog-c-done text { fill:#ddfff2; }
.aog-c-done .f-dot { fill:#5dffb5; }
.aog-c-failed .f-card { fill:#451b31; stroke:#ff718f; }
.aog-c-failed .f-inset { fill:#652039; stroke:#ff9bb3; }
.aog-c-failed text { fill:#fff0f3; }
.aog-c-failed .f-dot { fill:#ff718f; }
.aog-c-skipped .f-card { fill:#111726; stroke:#3b465d; stroke-dasharray:5 5; }
.aog-c-skipped .f-inset { fill:#121827; stroke:#303a50; }
.aog-c-skipped text { fill:#65718a; }
.aog-c-skipped .f-dot { fill:#3b465d; }

.aog-lgbg { fill:#100b25; fill-opacity:.92; stroke:#483174; }
.aog-lgt { fill:#f1eaff; font-size:17px; font-weight:800; text-anchor:middle; }
.aog-g .gb { fill:#17132d; stroke:#59428b; stroke-width:1.4; transition:all .35s ease; }
.aog-g .gl { fill:#d4c5f8; font-size:11px; font-weight:600; text-anchor:middle; }
.aog-g .gs { fill:#9b87c8; font-size:8.5px; text-anchor:middle; }
.aog-g-running .gb { fill:#102c52; stroke:#43dcff; stroke-width:1.8; filter:url(#aogGlow); }
.aog-g-running .gl { fill:#e0faff; }
.aog-g-done .gb { fill:#10372f; stroke:#42e6aa; }
.aog-g-done .gl { fill:#d1fae5; }
.aog-g-failed .gb { fill:#40192a; stroke:#ff718f; }
.aog-g-failed .gl { fill:#fecaca; }
.aog-g-skipped .gb { fill:#111321; stroke:#413953; stroke-dasharray:3 5; }
.aog-g-skipped .gl { fill:#766b8a; }
</style>
"""
