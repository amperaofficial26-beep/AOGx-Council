"""Model node kanvas BUILD: geometri, status nyata dari data, kabel SVG, HTML proses.

Zona kiri→kanan: CORE (inti) → PREP (langkah interaktif) → PROCESS (proses AI
nyata dari event pipeline) → panah menuju IDENTITAS & FILE (panel kanan, di luar
kanvas). Status node HANYA berasal dari state UI hasil pipeline sungguhan —
tanpa angka progres karangan; bila tahap belum ada, node tidak ditampilkan.
"""
import html
from typing import Optional

# --- Geometri kanvas (px) ---------------------------------------------------
CANVAS_W = 980
CANVAS_H = 540

CORE = {"x": 16, "y": 186, "w": 200, "h": 130}
PREP_X, PREP_W, PREP_H = 330, 220, 84
PREP_Y0, PREP_GAP = 16, 100          # 5 slot: 16, 116, 216, 316, 416
PROC_X, PROC_W, PROC_H = 650, 280, 84
PROC_Y0, PROC_GAP = 60, 100          # 3 slot: 60, 160, 260

# --- Tahap persiapan (interaksi pengguna, urutan asli wizard BUILD) ---------
PREP_NODES = (
    {"id": "b1", "step": "request", "no": 1, "name": "Permintaan",
     "icon": "edit_note", "btn": "Buka permintaan"},
    {"id": "b2", "step": "reference", "no": 2, "name": "Referensi",
     "icon": "explore", "btn": "Buka referensi"},
    {"id": "b3", "step": "form", "no": 3, "name": "Bentuk",
     "icon": "widgets", "btn": "Buka bentuk"},
    {"id": "b4", "step": "confirm", "no": 4, "name": "Validasi",
     "icon": "rule", "btn": "Buka validasi"},
    {"id": "b5", "step": "result", "no": 5, "name": "Hasil",
     "icon": "task", "btn": "Buka hasil"},
)

# Posisi langkah dalam alur (termasuk tahap berjalan & hasil).
FLOW_POS = {"request": 0, "reference": 1, "form": 2, "confirm": 3,
            "running": 4, "error": 4, "result": 5}

# --- Proses kerja AI (tahap NYATA pada build/pipeline.run) ------------------
STAGES = (
    {"id": "p1", "stage": "RESEARCH", "no": 1, "name": "Penelitian Referensi",
     "icon": "search"},
    {"id": "p2", "stage": "ANALISIS", "no": 2, "name": "Analisis Referensi",
     "icon": "insights"},
    {"id": "p3", "stage": "PLANNING", "no": 3, "name": "Perancangan Blueprint",
     "icon": "architecture"},
)
# Prefix teks status → id tahap.
_PREFIX_TO_STAGE = {"RESEARCH": "RESEARCH", "ANALISIS": "ANALISIS",
                    "PRODUCT PLANNING": "PLANNING", "PLANNING": "PLANNING"}

STATUS_COLOR = {"pending": "#475569", "processing": "#38bdf8",
                "completed": "#34d399", "active": "#e0b46e",
                "failed": "#f87171", "idle": "#64748b"}
STATUS_LABEL = {"pending": "menunggu", "processing": "berjalan",
                "completed": "selesai", "active": "aktif",
                "failed": "gagal", "idle": "siap"}


def _clip(text, limit: int = 60) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: max(0, limit - 1)].rstrip() + "…"


def _now_clock() -> str:
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")


def prep_status(index: int, step: str) -> Optional[str]:
    """Status node persiapan ke-`index` (1..5). None = belum tampil (locked)."""
    pos = FLOW_POS.get(step, 0)
    if index == 5:
        return "active" if step == "result" else None
    if step == PREP_NODES[index - 1]["step"]:
        return "active"
    if pos >= index:          # langkah sebelumnya sudah lewat → selesai
        return "completed"
    if pos == index - 1:      # belum terlihat menunggu prasyarat
        return None
    return None


def prep_summary(index: int, ss, quota: dict) -> str:
    """Ringkasan data nyata untuk node persiapan."""
    if index == 1:
        return _clip(ss.get("build_request") or "belum diisi", 34) or "belum diisi"
    if index == 2:
        refs = ss.get("build_refs") or ss.get("build_refs_pick") or []
        return f"{len(refs)} referensi dipilih" if refs else "belum dipilih"
    if index == 3:
        return _clip(ss.get("build_form_kind") or "belum dipilih", 34)
    if index == 4:
        return f"jatah {quota.get('used', 0)}/{quota.get('max', 0)} terpakai"
    if index == 5:
        res = ss.get("build_result") or {}
        bp = res.get("blueprint") or {}
        return _clip(bp.get("nama") or "blueprint tersimpan", 34)
    return ""


def live_stage_from_text(text: str) -> Optional[str]:
    """'RESEARCH: …' → 'RESEARCH'; 'PRODUCT PLANNING: …' → 'PLANNING'."""
    prefix = str(text or "").split(":", 1)[0].strip().upper()
    return _PREFIX_TO_STAGE.get(prefix)


def process_nodes(events, live_text: str = "", error: str = "") -> list:
    """Bangun daftar node proses dari event pipeline nyata.

    Tahap tampil hanya bila benar-benar dimulai (ada status/agent-nya) — tahap
    berikutnya muncul setelah prasyarat (tahap sebelumnya) menghasilkan event.
    """
    events = list(events or [])
    agents = {e.get("stage"): e for e in events if e.get("kind") == "agent"}
    statuses = [e for e in events if e.get("kind") == "status"]
    live_stage = live_stage_from_text(live_text) if live_text else None
    last_status_stage = (live_stage_from_text(statuses[-1].get("text", ""))
                         if statuses else None)
    if live_stage is None:
        # Tanpa teks live (render ulang dari log tersimpan), tahap yang terakhir
        # dipancarkan statusnya dianggap sedang berjalan bila belum ada agent.
        live_stage = last_status_stage
    failed_stage = None
    if error:
        # Kegagalan terjadi pada tahap yang sedang berjalan (status terakhir
        # yang belum menghasilkan event agent).
        for st in STAGES:
            if st["stage"] not in agents and st["stage"] == (live_stage or last_status_stage):
                failed_stage = st["stage"]
    nodes = []
    for st in STAGES:
        stage = st["stage"]
        agent = agents.get(stage)
        if agent is not None:
            status = "completed"
        elif error and stage == failed_stage:
            status = "failed"
        elif stage == live_stage and not error:
            status = "processing"
        else:
            status = None           # belum dimulai → jangan ditampilkan
        if status is None:
            continue
        if status == "completed":
            info = _clip(agent.get("text") or "", 150)
            who = " · ".join(x for x in (_clip(agent.get("role"), 18),
                                         _clip(agent.get("provider"), 18)) if x)
            when = agent.get("t") or ""
        elif status == "failed":
            info = _clip(error, 150)
            who, when = "", ""
        else:
            info = _clip(live_text, 150)
            who, when = "", _now_clock()
        nodes.append({"id": st["id"], "stage": stage, "no": st["no"],
                      "name": st["name"], "icon": st["icon"], "status": status,
                      "info": info, "who": who, "when": when})
    return nodes


# --- Geometri & kabel -------------------------------------------------------
def _anchor_core() -> tuple:
    return (CORE["x"] + CORE["w"], CORE["y"] + CORE["h"] // 2)


def _prep_box(i: int) -> dict:
    return {"x": PREP_X, "y": PREP_Y0 + (i - 1) * PREP_GAP, "w": PREP_W, "h": PREP_H}


def _proc_box(i: int) -> dict:
    return {"x": PROC_X, "y": PROC_Y0 + (i - 1) * PROC_GAP, "w": PROC_W, "h": PROC_H}


def compute_edges(prep_visible: list, proc: list) -> list:
    """Daftar tepi (x1,y1,x2,y2,status) dari dependensi data nyata.

    prep_visible: node persiapan tampil (urutan) berstatus; proc: node proses
    yang tampil. Fan tipis inti→tahap (hierarki), rantai solid antar-tahap,
    tahap terakhir → proses, proses terakhir → node Hasil, panah ke panel file.
    """
    edges = []
    half = PREP_H // 2
    # Fan tipis dari inti ke tahap persiapan 1..4 (hierarki proyek).
    cx, cy = _anchor_core()
    for p in prep_visible[:4]:
        box = _prep_box(p["i"])
        edges.append((cx, cy, box["x"], box["y"] + half, p["status"], "fan"))
    # Rantai persiapan. Bila proses sudah ada, jembatan terakhir melewati
    # proses (b4 → proses → b5), jadi pasangan terakhir tidak dirantai langsung.
    chain = prep_visible[:-1] if proc else prep_visible
    for a, b in zip(chain, chain[1:]):
        ba, bb = _prep_box(a["i"]), _prep_box(b["i"])
        edges.append((ba["x"] + ba["w"], ba["y"] + half,
                      bb["x"], bb["y"] + half, b["status"], "solid"))
    # Tahap Validasi (b4) → proses pertama.
    if proc and prep_visible:
        src = next((p for p in reversed(prep_visible)
                    if p["step"] != "result"), prep_visible[-1])
        bl = _prep_box(src["i"])
        p0 = _proc_box(1)
        edges.append((bl["x"] + bl["w"], bl["y"] + half,
                      p0["x"], p0["y"] + half, proc[0]["status"], "solid"))
    # Rantai proses.
    for idx in range(1, len(proc)):
        ba, bb = _proc_box(idx), _proc_box(idx + 1)
        edges.append((ba["x"] + ba["w"], ba["y"] + half,
                      bb["x"], bb["y"] + half, proc[idx]["status"], "solid"))
    # Proses terakhir → node Hasil (b5) bila tampil, lalu panah ke IDENTITAS.
    has_result = any(p["step"] == "result" for p in prep_visible)
    if proc:
        bl = _proc_box(len(proc))
        if has_result:
            box = _prep_box(5)
            edges.append((bl["x"] + bl["w"], bl["y"] + half,
                          box["x"], box["y"] + half, "active", "solid"))
        edges.append((bl["x"] + bl["w"], bl["y"] + half,
                      CANVAS_W - 8, bl["y"] + half,
                      proc[-1]["status"], "arrow"))
    return edges


def cables_svg(edges: list) -> str:
    """SVG satu lapis berisi lengkung bezier status + penanda arah."""
    markers, paths = [], []
    seen = set()
    for x1, y1, x2, y2, status, kind in edges:
        color = STATUS_COLOR.get(status, STATUS_COLOR["pending"])
        if status not in seen:
            seen.add(status)
            markers.append(
                f'<marker id="aogArrow-{status}" viewBox="0 0 10 10" refX="8" refY="5"'
                f' markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
                f'<path d="M 0 1 L 9 5 L 0 9 z" fill="{color}"/></marker>')
        dx = max(28.0, (x2 - x1) * 0.45)
        d = (f"M {x1:.0f} {y1:.0f} C {x1 + dx:.0f} {y1:.0f}, "
             f"{x2 - dx:.0f} {y2:.0f}, {x2:.0f} {y2:.0f}")
        cls = "bld-edge"
        if kind == "fan":
            cls += " is-fan"
        if status == "processing":
            cls += " is-live"
        width = 1.2 if kind == "fan" else 2.2
        opacity = ' opacity="0.4"' if kind == "fan" else ""
        end = (f' marker-end="url(#aogArrow-{status})"'
               if kind == "arrow" else "")
        paths.append(f'<path class="{cls}" d="{d}" stroke="{color}" '
                     f'stroke-width="{width}" fill="none"{opacity}{end}/>')
    return (
        f'<svg class="bld-cables" viewBox="0 0 {CANVAS_W} {CANVAS_H}" '
        f'preserveAspectRatio="none" aria-hidden="true">'
        f'<defs>{"".join(markers)}</defs>{"".join(paths)}</svg>'
    )


# --- HTML -------------------------------------------------------------------
def status_marker(status: str) -> str:
    return (f'<span class="bld-st is-{status}">'
            f'{html.escape(STATUS_LABEL.get(status, status))}</span>')


def core_html(ss, step: str, quota: dict) -> str:
    """Kartu inti proyek: nama, chip status, jumlah nyata."""
    name = _clip(ss.get("build_request") or "proyek baru", 36)
    pos = FLOW_POS.get(step, 0)
    if step == "running":
        status = "processing"
    elif step == "result":
        status = "completed"
    elif step == "error":
        status = "failed"
    else:
        status = "idle"
    prep_done = sum(1 for i in range(1, 5) if prep_status(i, step) == "completed")
    proc_done = len([n for n in process_nodes(ss.get("build_log"),
                                              error=ss.get("build_error") or "")
                     if n["status"] == "completed"])
    counts = (f'{prep_done}/5 tahap · {proc_done}/3 proses AI')
    if pos >= 5:
        counts = f'5/5 tahap · {proc_done}/3 proses AI'
    return (
        f'{status_marker(status)}'
        f'<div class="bld-core-name">{html.escape(name)}</div>'
        f'<div class="bld-core-sub">status: <b>{STATUS_LABEL[status]}</b>'
        f' · {counts}</div>'
        f'<div class="bld-core-sub">jatah {quota.get("used", 0)}/'
        f'{quota.get("max", 0)} · sisa {quota.get("remaining", 0)}</div>'
    )


def prep_html(node: dict, status: str, summary: str) -> str:
    return (
        f'{status_marker(status)}'
        f'<div class="bld-node-sub">{html.escape(summary or "")}</div>'
    )


def proc_html(node: dict) -> str:
    meta = " · ".join(x for x in (node.get("who"), node.get("when")) if x)
    info = html.escape(node.get("info") or "")
    return (
        f'{status_marker(node["status"])}'
        + (f'<div class="bld-node-meta">{html.escape(meta)}</div>' if meta else "")
        + (f'<div class="bld-node-info">{info}</div>' if info else "")
    )


def live_layer_html(events, live_text: str = "") -> str:
    """Lapisan HTML absolut untuk node proses yang sedang berjalan (di dalam
    loop Streamlit — container tidak bisa muncul di tengah satu run)."""
    nodes = process_nodes(events, live_text=live_text)
    parts = []
    for i, n in enumerate(nodes, start=1):
        box = _proc_box(i)
        parts.append(
            f'<div class="bld-pnode is-{n["status"]}" style="left:{box["x"]}px;'
            f'top:{box["y"]}px;width:{box["w"]}px;min-height:{box["h"]}px">'
            f'<div class="bld-node-head">'
            f'<span class="bld-node-no is-{n["status"]}">{n["no"]}</span>'
            f'<span class="bld-node-name"><i class="bld-mi">{n["icon"]}</i> '
            f'{html.escape(n["name"])}</span></div>'
            f'{proc_html(n)}</div>')
    if not parts:
        return ('<div class="bld-live"><div class="bld-wait">Proses kerja AI '
                'muncul di sini setelah tahap Validasi dijalankan.</div></div>')
    return ('<div class="bld-live">'
            + "".join(parts) + "</div>")


def node_position_css() -> str:
    """CSS posisi semua node (dihitung dari konstanta geometri di atas)."""
    rules = [
        f'.st-key-bnode-core{{left:{CORE["x"]}px;top:{CORE["y"]}px;'
        f'width:{CORE["w"]}px;min-height:{CORE["h"]}px}}',
    ]
    for i in range(1, 6):
        box = _prep_box(i)
        rules.append(
            f'.st-key-bnode-b{i}{{left:{box["x"]}px;top:{box["y"]}px;'
            f'width:{box["w"]}px;min-height:{box["h"]}px}}')
    for i in range(1, 4):
        box = _proc_box(i)
        rules.append(
            f'.st-key-bnode-p{i}{{left:{box["x"]}px;top:{box["y"]}px;'
            f'width:{box["w"]}px;min-height:{box["h"]}px}}')
    return "\n".join(rules)


def fit_zoom_css() -> str:
    """Zoom 'fit' per lebar layar — jaga node tetap terbaca, geser bila sempit."""
    return (
        ".st-key-build-canvas-inner{zoom:.7}\n"
        "@media (min-width:1360px){.st-key-build-canvas-inner{zoom:.8}}\n"
        "@media (min-width:1620px){.st-key-build-canvas-inner{zoom:.9}}\n"
        "@media (min-width:1880px){.st-key-build-canvas-inner{zoom:1}}"
    )


def zoom_css(ss) -> str:
    z = ss.get("build_zoom")
    if z is None:
        return fit_zoom_css()
    try:
        z = round(min(1.5, max(0.55, float(z))), 2)
    except (TypeError, ValueError):
        return fit_zoom_css()
    return f".st-key-build-canvas-inner{{zoom:{z}}}"
