"""Mesin Council bergaya workflow (n8n): node persegi, kabel lengkung, cahaya berjalan.

Modul ini membuat dokumen HTML dengan <canvas> + JavaScript lalu menampilkannya lewat
st.components.v1.html, karena Streamlit tidak menjalankan <script> di dalam st.markdown.
Status node dibaca dari CouncilFlow, jadi pipeline dan CouncilFlow tidak perlu diubah.

Alur pada kanvas:
  Trigger (pertanyaan) -> Orchestrator (prompt) -> 3 agen paralel (Analis, Skeptis, Pakar;
  masing-masing dengan sub-node Chat Model + Structured Output) -> Recall -> Processor
  -> Penyusun (bundle) -> Verifier -> Jawaban final (success).

Ada dua komponen terpisah:
- show()      : kanvas "Mesin Council" selebar kolom penuh.
- show_flow() : panel "Alur Council" (diagram keputusan), opsional.
"""
import json

from ui.flow import DEBATERS, DONE, FAILED, PENDING, RUNNING, SKIPPED, NODES, _clip
from ui.machine import STATE_WORD, debate_state, edge_cls, node_state, norm

HEIGHT = 460        # tinggi awal iframe mesin; JS menyesuaikan dengan lebar kolom
FLOW_HEIGHT = 622   # tinggi awal iframe Alur Council

ORANGE, BLUE, TEAL = "#ff8a3d", "#4da3ff", "#2dd4bf"

# Koordinat dunia (world) kanvas workflow. Kamera di JS menyesuaikan (fit / ikuti).
MID_Y = 330
LANES = {"analyst": 120, "skeptic": 330, "expert": 540}
COL = {"start": 60, "orchestrator": 200, "agent": 430, "recall": 655, "proc": 785,
       "synthesizer": 915, "verifier": 1045, "answer": 1175}
SUB_DY = 100        # jarak vertikal agen -> sub-node (Chat Model / Structured Output)
SUB_DX = 55         # geser horizontal sub-node dari pusat kartu agen

AGENTS = {
    # id: (nama, keterangan kartu, keterangan recall, ikon output)
    "analyst": ("Analis", "Penalaran langkah", "Argumen", "wave"),
    "skeptic": ("Skeptis", "Bantahan & risiko", "Bantahan", "wave"),
    "expert":  ("Pakar", "Pengetahuan domain", "Wawasan", "code"),
}
PROC_ICON = {"analyst": "enter", "skeptic": "chev", "expert": "chev"}


def _status(flow) -> str:
    if flow.error:
        return "Berhenti karena galat"
    if flow.finished:
        return "Selesai"
    return flow.stage_text or "Menunggu pertanyaan"


def _lane_states(flow, agent: str) -> tuple:
    """Status turunan untuk node Recall dan Processor pada jalur satu agen."""
    a = node_state(flow, agent)
    if a in (SKIPPED, FAILED):
        return a, a
    if a != DONE:
        return PENDING, PENDING
    syn = node_state(flow, "synthesizer")
    started = flow.finished or syn in (RUNNING, DONE, FAILED)
    return DONE, (DONE if started else RUNNING)


def _node(flow, nid: str, kind: str, x: float, y: float, label: str, sub: str, icon: str,
          accent: str, depth: int, state: str = "", src: str = "") -> dict:
    src = src or nid
    state = state or node_state(flow, src)
    note = flow.notes.get(src, "")
    if nid == "start":
        note = _clip(flow.question, 90)
    return {"id": nid, "kind": kind, "x": x, "y": y, "label": label, "sub": sub, "icon": icon,
            "accent": accent, "depth": depth, "state": state,
            "word": STATE_WORD.get(state, STATE_WORD[PENDING]),
            "prov": flow.providers.get(src, ""), "dur": flow.durations.get(src, ""), "note": note}


# Rute utama (lajur tengah). Bila ada node yang dilewati (pertanyaan sederhana, mode Flash,
# tanpa verifikasi), cahaya tetap mengalir lewat rute ini, bukan melompat lewat jalan pintas.
MAIN_ROUTE = ["start", "orchestrator", "skeptic", "skeptic_recall", "skeptic_proc",
              "synthesizer", "verifier", "answer"]


def _through_route(states: dict) -> dict:
    """Kelas animasi untuk sisi rute utama yang menyentuh node dilewati.

    Statusnya diambil dari node aktif terdekat di hulu dan hilir, dan tiap sisi diberi nomor
    urut (seq/seqn) supaya JS bisa menjalankan satu cahaya bersambung sepanjang segmen.
    """
    out, route, i = {}, MAIN_ROUTE, 0
    while i < len(route) - 1:
        if SKIPPED not in (states[route[i]], states[route[i + 1]]):
            i += 1
            continue
        j = i + 1
        while j < len(route) - 1 and states[route[j]] == SKIPPED:
            j += 1
        up, down = states[route[i]], states[route[j]]
        cls = "skip" if SKIPPED in (up, down) else edge_cls(up, down)
        for k in range(i, j):
            out[(route[k], route[k + 1])] = {"cls": cls, "seq": k - i, "seqn": j - i,
                                              "to": route[j]}
        i = j
    return out


def payload(flow) -> dict:
    """Data murni (JSON) untuk kanvas mesin; tidak memanggil Streamlit sehingga bisa diuji."""
    nodes = [
        _node(flow, "start", "square", COL["start"], MID_Y, "Pertanyaan Masuk", "Trigger",
              "trigger", ORANGE, 0),
        _node(flow, "orchestrator", "square", COL["orchestrator"], MID_Y, "Orchestrator",
              "Buat prompt & rencana", "pencil", BLUE, 1),
        _node(flow, "researcher", "circle", COL["orchestrator"], MID_Y + 118, "Researcher",
              "Riset web · opsional", "search", BLUE, 1),
    ]
    for agent, (name, sub, recall_sub, out_icon) in AGENTS.items():
        y = LANES[agent]
        ax = COL["agent"]
        recall_state, proc_state = _lane_states(flow, agent)
        prov = flow.providers.get(agent, "")
        nodes += [
            _node(flow, agent, "card", ax, y, f"{name} Agent", sub, "robot", BLUE, 2),
            _node(flow, f"{agent}_model", "circle", ax - SUB_DX, y + SUB_DY, "Chat Model",
                  prov or "otomatis", "model", BLUE, 2, src=agent),
            _node(flow, f"{agent}_parser", "circle", ax + SUB_DX, y + SUB_DY,
                  "Structured Output", "Parsed", out_icon, BLUE, 2, src=agent),
            _node(flow, f"{agent}_recall", "square", COL["recall"], y, f"Recall {name}",
                  recall_sub, "pencil", ORANGE, 3, state=recall_state, src=agent),
            _node(flow, f"{agent}_proc", "square", COL["proc"], y, f"Proses {name}",
                  "Data Processor", PROC_ICON[agent], ORANGE, 4, state=proc_state, src=agent),
        ]
    score = "" if flow.score is None else f"skor {flow.score:.0%}"
    nodes += [
        _node(flow, "synthesizer", "square", COL["synthesizer"], MID_Y, "Penyusun",
              "Bundle hasil diskusi", "merge", TEAL, 5),
        _node(flow, "verifier", "square", COL["verifier"], MID_Y, "Verifier",
              score or "Skor kualitas", "shield", TEAL, 6),
        _node(flow, "answer", "square", COL["answer"], MID_Y, "Jawaban Final",
              "Success status", "pencil", TEAL, 7),
    ]
    states = {n["id"]: n["state"] for n in nodes}
    through = _through_route(states)

    def edge(a, b, kind="main", label="", cls=None):
        e = {"a": a, "b": b, "kind": kind, "label": label}
        if (a, b) in through:  # jalur utama yang melewati node dilewati: tetap dialiri cahaya
            e.update(through[(a, b)])
        elif cls:
            e["cls"] = cls
        elif SKIPPED in (states[a], states[b]):
            e["cls"] = "skip"   # jalur yang tidak dipakai tidak diberi warna
        else:
            e["cls"] = edge_cls(states[a], states[b])
        return e

    edges = [edge("start", "orchestrator"), edge("orchestrator", "researcher", "sub")]
    for agent in AGENTS:
        edges += [
            edge("orchestrator", agent),
            edge(agent, f"{agent}_model", "sub"),
            edge(agent, f"{agent}_parser", "sub"),
            edge(agent, f"{agent}_recall"),
            edge(f"{agent}_recall", f"{agent}_proc"),
            edge(f"{agent}_proc", "synthesizer"),
        ]
    edges += [edge("synthesizer", "verifier"), edge("verifier", "answer", label="lolos"),
              edge("verifier", "synthesizer", "back", "revisi",
                   cls="hot" if flow.attempt > 0 else "faint")]

    live = any(norm(flow.state(n)) == RUNNING for n in NODES if n != "start")
    return {"status": _status(flow), "live": live, "finished": bool(flow.finished),
            "error": bool(flow.error), "attempt": flow.attempt,
            "sig": f"{getattr(flow, 't0', 0):.3f}:{flow.attempt}",
            "nodes": nodes, "edges": edges, "debaters": list(DEBATERS)}


def _graph(flow) -> dict:
    """Panel 'Alur Council': kotak, belah ketupat, dan jalurnya (koordinat lokal 300 lebar)."""
    st = {n: node_state(flow, n) for n in NODES}
    s_start = "done" if flow.state("start") == "done" else "pending"
    s_orch, s_res = st["orchestrator"], st["researcher"]
    s_deb, s_syn = debate_state(flow), st["synthesizer"]
    s_ver, s_ans = st["verifier"], st["answer"]
    s_end = "done" if flow.finished and not flow.error else "pending"
    revisi = "hot" if flow.attempt > 0 else "idle"
    simple = s_deb == "skipped"
    mid = edge_cls(s_orch, s_syn) if simple else "idle"

    boxes = [
        {"shape": "pill", "x": 150, "y": 74, "w": 120, "h": 30, "label": "START", "state": s_start},
        {"shape": "box", "x": 150, "y": 133, "w": 140, "h": 30, "label": "State", "state": s_start},
        {"shape": "diamond", "x": 150, "y": 215, "w": 132, "h": 60, "label": "Orchestrator", "state": s_orch},
        {"shape": "box", "x": 62, "y": 275, "w": 108, "h": 34, "label": "Researcher", "state": s_res},
        {"shape": "box", "x": 238, "y": 275, "w": 108, "h": 34, "label": "Debat 3 agen", "state": s_deb},
        {"shape": "box", "x": 150, "y": 336, "w": 128, "h": 34, "label": "Penyusun", "state": s_syn},
        {"shape": "diamond", "x": 150, "y": 419, "w": 132, "h": 66, "label": "Verifier", "state": s_ver},
        {"shape": "box", "x": 150, "y": 501, "w": 128, "h": 34, "label": "Jawaban final", "state": s_ans},
        {"shape": "pill", "x": 150, "y": 562, "w": 120, "h": 30, "label": "END", "state": s_end},
    ]
    edges = [
        ("M150,92 L150,118", edge_cls(s_start, s_start), "", 0, 0),
        ("M150,148 L150,186", edge_cls(s_start, s_orch), "", 0, 0),
        ("M88,215 C62,215 62,236 62,258", edge_cls(s_orch, s_res), "butuh web", 30, 232),
        ("M212,215 C238,215 238,236 238,258", edge_cls(s_orch, s_deb), "", 0, 0),
        ("M150,245 L150,328", mid if simple else "idle", "sederhana" if simple else "", 150, 300),
        ("M62,292 C62,318 72,336 86,336", edge_cls(s_res, s_syn), "", 0, 0),
        ("M238,292 C238,318 228,336 214,336", edge_cls(s_deb, s_syn), "", 0, 0),
        ("M150,354 L150,386", edge_cls(s_syn, s_ver), "", 0, 0),
        ("M150,452 L150,484", edge_cls(s_ver, s_ans), "lolos", 176, 472),
        ("M150,518 L150,546", edge_cls(s_ans, s_end), "", 0, 0),
        ("M212,419 C292,419 292,336 214,336", revisi, "revisi", 274, 382),
    ]
    return {"boxes": boxes,
            "edges": [{"d": d, "cls": c, "label": lb, "lx": lx, "ly": ly} for d, c, lb, lx, ly in edges]}


def flow_payload(flow) -> dict:
    """Data untuk panel Alur Council saja."""
    return {"graph": _graph(flow)}


def _inject(template: str, data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("__COMMON__", COMMON_JS).replace("__DATA__", text)


def render(flow) -> str:
    return _inject(TEMPLATE, payload(flow))


def render_flow(flow) -> str:
    return _inject(FLOW_TEMPLATE, flow_payload(flow))


def _show(placeholder, html: str, cache: dict, height: int):
    import streamlit.components.v1 as components
    if cache.get("html") == html:
        return
    cache["html"] = html
    with placeholder.container():
        components.html(html, height=height)


def show(placeholder, flow, cache: dict):
    """Tampilkan mesin di placeholder st.empty(). `cache` (dict baru tiap run) mencegah iframe
    dimuat ulang bila status tidak berubah, sehingga animasi tidak berkedip."""
    _show(placeholder, render(flow), cache, HEIGHT)


def show_flow(placeholder, flow, cache: dict):
    """Tampilkan panel Alur Council di placeholder tersendiri (cache terpisah dari mesin)."""
    _show(placeholder, render_flow(flow), cache, FLOW_HEIGHT)


# Kode JavaScript bersama (gambar kotak, kabel, partikel) dipakai oleh kedua komponen.
COMMON_JS = r"""
const MONO = '"Fira Code", ui-monospace, Menlo, monospace', SANS = 'Inter, ui-sans-serif, system-ui, sans-serif';
const calm = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
const cv = document.getElementById('c'), ctx = cv.getContext('2d'), meas = document.getElementById('meas');
const dpr = window.devicePixelRatio || 1;

// iframe dibuat setinggi isi kanvas, supaya tidak ada ruang kosong di bawahnya.
function sizeFrame(h) {
  try { if (window.frameElement) window.frameElement.style.height = h + 'px'; } catch (e) {}
  try { parent.postMessage({isStreamlitMessage: true, type: 'streamlit:setFrameHeight', height: h}, '*'); } catch (e) {}
}

function rr(x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
function fit(s, maxw) { s = String(s || ''); if (ctx.measureText(s).width <= maxw) return s;
  while (s.length > 1 && ctx.measureText(s + '…').width > maxw) s = s.slice(0, -1); return s + '…'; }
function pal(state, base) {
  switch (state) {
    case 'running': return {line: '#78f2ff', fill: 'rgba(16,44,82,.93)', glow: '#37e8ff', text: '#ffffff', sub: '#a4f7ff', a: 1};
    case 'done':    return {line: '#45f2b0', fill: 'rgba(13,56,47,.93)', glow: '#45f2b0', text: '#ddfff2', sub: '#8ee9c4', a: 1};
    case 'failed':  return {line: '#ff718f', fill: 'rgba(69,27,49,.93)', glow: '#ff718f', text: '#fff0f3', sub: '#ffb4c3', a: 1};
    case 'skipped': return {line: '#3b465d', fill: 'rgba(17,23,38,.7)', glow: null, text: '#65718a', sub: '#4d5a72', a: .9};
    default:        return {line: base, fill: 'rgba(12,17,40,.88)', glow: null, text: '#cbd5e1', sub: '#7c89b0', a: .72};
  }
}
const EDGE = {
  idle: {c: 'rgba(130,140,200,.32)', w: 1.2, dash: [3, 8], glow: 0, n: 0},
  skip: {c: 'rgba(60,75,100,.4)', w: 1.1, dash: [3, 8], glow: 0, n: 0},
  hot:  {c: '#ff77e9', w: 2.2, dash: [8, 7], glow: 10, n: 2, p: '#ffd5ff', sp: .30},
  live: {c: '#8efaff', w: 2.8, dash: [8, 7], glow: 14, n: 3, p: '#c5ffff', sp: .62},
  bad:  {c: '#ff718f', w: 2.2, dash: [8, 7], glow: 10, n: 1, p: '#ffc2ca', sp: .3},
};
function drawEdge(d, cls, t, label, lx, ly) {
  const st = EDGE[cls] || EDGE.idle, p = new Path2D(d);
  ctx.save();
  ctx.setLineDash(st.dash); ctx.lineCap = 'round'; ctx.strokeStyle = st.c; ctx.lineWidth = st.w;
  if (st.glow) { ctx.shadowColor = st.c; ctx.shadowBlur = st.glow; ctx.lineDashOffset = -t * (st.sp || .3) * 60; }
  ctx.stroke(p); ctx.restore();
  let L = 0;
  if (st.n || (label && lx === undefined)) { meas.setAttribute('d', d); L = meas.getTotalLength(); }
  if (st.n && L > 0 && !calm) {
    for (let i = 0; i < st.n; i++) {
      const u = ((t * st.sp * 0.5 + i / st.n) % 1), pt = meas.getPointAtLength(u * L);
      ctx.save(); ctx.fillStyle = st.p; ctx.shadowColor = st.p; ctx.shadowBlur = 12;
      ctx.beginPath(); ctx.arc(pt.x, pt.y, i ? 2 : 3.2, 0, 6.2832); ctx.fill(); ctx.restore();
    }
  }
  if (label) {
    let x = lx, y = ly;
    if (x === undefined) { const m = meas.getPointAtLength(L / 2); x = m.x; y = m.y - 7; }
    ctx.save(); ctx.font = '600 9px ' + MONO; ctx.textAlign = 'center';
    ctx.fillStyle = (cls === 'hot' || cls === 'live') ? '#e4c9ff' : (cls === 'skip' ? '#2b3a52' : '#8a7dbb');
    ctx.fillText(label, x, y); ctx.restore();
  }
}
"""


TEMPLATE = r"""<!DOCTYPE html>
<html lang="id"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  html,body{margin:0;padding:0;background:#0a0a0c;overflow:hidden;font-family:'Inter',sans-serif;}
  #wrap{position:relative;box-sizing:border-box;width:100%;border-radius:16px;overflow:hidden;
        border:1px solid rgba(255,255,255,.08);box-shadow:0 8px 32px rgba(0,0,0,.45);background:#0d0d10;}
  canvas{display:block;cursor:grab;touch-action:none;}
  canvas.drag{cursor:grabbing;} canvas.hov{cursor:pointer;}
  #ctl{position:absolute;top:10px;right:10px;display:flex;gap:6px;z-index:2;}
  #ctl button{font:600 11px Inter,sans-serif;color:#d4d4d8;background:rgba(24,24,27,.86);
        border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:5px 9px;cursor:pointer;}
  #ctl button:hover{border-color:rgba(77,163,255,.7);color:#fff;}
  #ctl button.on{border-color:#4da3ff;color:#fff;box-shadow:0 0 10px rgba(77,163,255,.35);}
</style></head>
<body><div id="wrap"><canvas id="c"></canvas>
<div id="ctl">
  <button id="b-follow" title="Kamera mengikuti node yang aktif">Ikuti</button>
  <button id="b-fit" title="Tampilkan seluruh alur">Fit</button>
  <button id="b-out" title="Perkecil">&minus;</button>
  <button id="b-in" title="Perbesar">+</button>
</div></div>
<svg style="position:absolute;width:0;height:0;visibility:hidden"><path id="meas" d="M0,0"/></svg>
<script>
__COMMON__
const D = __DATA__;
const SQ = 66, CARD_W = 210, CARD_H = 66, SUB_R = 23, STEP = 0.5;
const N = {}; D.nodes.forEach(n => {
  if (n.kind === 'square') { n.w = SQ; n.h = SQ; }
  else if (n.kind === 'card') { n.w = CARD_W; n.h = CARD_H; }
  else { n.w = SUB_R * 2; n.h = SUB_R * 2; }
  N[n.id] = n;
});

// ---------- ukuran iframe ----------
let W = 600, H = 400;
function resize() {
  W = Math.max(280, (document.documentElement.clientWidth || 600) - 2);
  H = Math.round(Math.max(340, Math.min(620, W * B.h / B.w + 12)));
  cv.style.width = W + 'px'; cv.style.height = H + 'px';
  cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
  sizeFrame(H + 2); computeFit();
}

// ---------- geometri kabel (dihitung sekali, lalu disampel untuk animasi cahaya) ----------
function outPort(n) { return n.kind === 'circle' ? [n.x + SUB_R, n.y] : [n.x + n.w / 2, n.y]; }
function inPort(n) { return n.kind === 'circle' ? [n.x - SUB_R, n.y] : [n.x - n.w / 2, n.y]; }
function pathFor(e) {
  const a = N[e.a], b = N[e.b];
  if (e.kind === 'sub') {  // dari port bawah agen ke atas sub-node
    const x1 = b.x, y1 = a.y + a.h / 2, x2 = b.x, y2 = b.y - SUB_R;
    if (a.kind !== 'card') return `M${a.x},${y1} L${a.x},${y2}`;
    return `M${x1},${y1} L${x2},${y2}`;
  }
  if (e.kind === 'back') {
    const x1 = a.x, y1 = a.y + a.h / 2 + 2, x2 = b.x, y2 = b.y + b.h / 2 + 2, dip = Math.max(y1, y2) + 70;
    return `M${x1},${y1} C${x1},${dip} ${x2},${dip} ${x2},${y2}`;
  }
  const [x1, y1] = outPort(a), [x2, y2] = inPort(b), k = Math.max(40, (x2 - x1) * 0.5);
  return `M${x1},${y1} C${x1 + k},${y1} ${x2 - k},${y2} ${x2},${y2}`;
}
D.edges.forEach(e => {
  e.d = pathFor(e); e.p2d = new Path2D(e.d);
  meas.setAttribute('d', e.d); const L = meas.getTotalLength(); e.len = L; e.pts = [];
  for (let i = 0; i <= 80; i++) { const p = meas.getPointAtLength(L * i / 80); e.pts.push([p.x, p.y]); }
  e.color = (N[e.to || e.b] && N[e.to || e.b].accent) || '#4da3ff';
});
function at(e, u) { u = Math.max(0, Math.min(1, u)); const f = u * 80, i = Math.floor(f), r = f - i;
  const a = e.pts[i], b = e.pts[Math.min(80, i + 1)]; return [a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r]; }

// ---------- batas dunia + kamera ----------
const B = (() => { let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  D.nodes.forEach(n => { x0 = Math.min(x0, n.x - n.w / 2 - 40); x1 = Math.max(x1, n.x + n.w / 2 + (n.id === 'answer' ? 95 : 40));
                         y0 = Math.min(y0, n.y - n.h / 2 - 30); y1 = Math.max(y1, n.y + n.h / 2 + 52); });
  return {x: x0, y: y0 - 58, w: x1 - x0, h: y1 - y0 + 58}; })();
let FIT = {k: 1, x: 0, y: 0};
function computeFit() { const k = Math.min(W / B.w, H / B.h);
  FIT = {k, x: (W - B.w * k) / 2 - B.x * k, y: (H - B.h * k) / 2 - B.y * k}; }
function focus(wx, wy) { const k = Math.min(1.0, Math.max(FIT.k * 1.3, Math.min(W / 760, H / 520)));
  return {k, x: W / 2 - wx * k, y: H / 2 - wy * k + 8}; }

const store = (() => { try { return window.sessionStorage; } catch (e) { return null; } })();
function load(key, dflt) { try { const v = store && store.getItem(key); return v ? JSON.parse(v) : dflt; } catch (e) { return dflt; } }
function save(key, v) { try { store && store.setItem(key, JSON.stringify(v)); } catch (e) {} }

window.addEventListener('resize', resize); resize();
let mode = load('aog_wf_mode', 'auto');
let cam = load('aog_wf_cam', null) || Object.assign({}, FIT);

// Sapuan cahaya sekali dari trigger ke jawaban saat proses selesai (atau diputar ulang).
const swept = load('aog_wf_swept', '');
const sweepOn = D.finished && !D.error && !calm && swept !== D.sig;
let t0 = null;
if (sweepOn) save('aog_wf_swept', D.sig);
const maxDepth = Math.max(...D.nodes.map(n => n.depth));
const SWEEP_END = (maxDepth + 1) * STEP + 1.4;
const colX = []; D.nodes.forEach(n => { colX[n.depth] = colX[n.depth] === undefined ? n.x : colX[n.depth]; });

function camTarget(st) {
  if (mode === 'manual') return null;
  if (mode === 'fit') return FIT;
  if (sweepOn && st < SWEEP_END - 0.6) {
    const d = Math.min(maxDepth, st / STEP), i = Math.floor(d), r = d - i;
    const x = colX[i] + ((colX[Math.min(maxDepth, i + 1)] || colX[i]) - colX[i]) * r;
    return focus(x, 330);
  }
  if (D.live) { const run = D.nodes.filter(n => n.state === 'running' && n.id !== 'start' && !/_model$|_parser$/.test(n.id));
    if (run.length) { const x = run.reduce((s, n) => s + n.x, 0) / run.length;
      const y = run.reduce((s, n) => s + n.y, 0) / run.length; return focus(x, y); } }
  return FIT;
}

// ---------- ikon ----------
function icon(name, x, y, s, col) {
  ctx.save(); ctx.translate(x, y); ctx.strokeStyle = col; ctx.fillStyle = col;
  ctx.lineWidth = 2.2; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  switch (name) {
    case 'pencil':
      ctx.rotate(-Math.PI / 4); ctx.beginPath(); ctx.moveTo(-s * .55, -s * .16); ctx.lineTo(s * .38, -s * .16);
      ctx.lineTo(s * .38, s * .16); ctx.lineTo(-s * .55, s * .16); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(-s * .62, -s * .16); ctx.lineTo(-s * .9, 0); ctx.lineTo(-s * .62, s * .16); ctx.closePath(); ctx.fill();
      ctx.fillRect(s * .44, -s * .16, s * .14, s * .32); break;
    case 'trigger':
      ctx.beginPath(); ctx.moveTo(-s * .1, -s * .5); ctx.lineTo(-s * .55, -s * .5); ctx.lineTo(-s * .55, s * .5); ctx.lineTo(-s * .1, s * .5); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-s * .25, 0); ctx.lineTo(s * .55, 0); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(s * .28, -s * .28); ctx.lineTo(s * .58, 0); ctx.lineTo(s * .28, s * .28); ctx.stroke(); break;
    case 'robot':
      rr(-s * .5, -s * .3, s, s * .72, s * .2); ctx.fill();
      ctx.fillRect(-s * .06, -s * .55, s * .12, s * .25); ctx.beginPath(); ctx.arc(0, -s * .58, s * .1, 0, 6.2832); ctx.fill();
      ctx.fillRect(-s * .68, -s * .05, s * .12, s * .3); ctx.fillRect(s * .56, -s * .05, s * .12, s * .3);
      ctx.fillStyle = '#18181b'; ctx.beginPath(); ctx.arc(-s * .2, s * .04, s * .1, 0, 6.2832); ctx.arc(s * .2, s * .04, s * .1, 0, 6.2832); ctx.fill(); break;
    case 'model':
      ctx.beginPath(); ctx.moveTo(-s * .5, s * .45); ctx.lineTo(-s * .08, -s * .5); ctx.lineTo(s * .12, -s * .5); ctx.lineTo(-s * .12, s * .45); ctx.closePath(); ctx.fill();
      ctx.globalAlpha = .75; ctx.beginPath(); ctx.moveTo(s * .02, -s * .2); ctx.lineTo(s * .52, s * .45); ctx.lineTo(-s * .05, s * .45); ctx.lineTo(s * .18, s * .12); ctx.closePath(); ctx.fill(); break;
    case 'wave':
      [-.42, -.21, 0, .21, .42].forEach((dx, i) => { const h = [.18, .42, .6, .42, .18][i] * s;
        ctx.beginPath(); ctx.moveTo(dx * s, -h); ctx.lineTo(dx * s, h); ctx.stroke(); }); break;
    case 'code':
      ctx.beginPath(); ctx.moveTo(-s * .22, -s * .32); ctx.lineTo(-s * .52, 0); ctx.lineTo(-s * .22, s * .32); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(s * .22, -s * .32); ctx.lineTo(s * .52, 0); ctx.lineTo(s * .22, s * .32); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(s * .08, -s * .42); ctx.lineTo(-s * .08, s * .42); ctx.stroke(); break;
    case 'chev':
      ctx.lineWidth = 3; [-.24, .14].forEach(dx => { ctx.beginPath(); ctx.moveTo(dx * s, -s * .36);
        ctx.lineTo((dx + .3) * s, 0); ctx.lineTo(dx * s, s * .36); ctx.stroke(); }); break;
    case 'enter':
      ctx.beginPath(); ctx.moveTo(s * .1, -s * .5); ctx.lineTo(s * .55, -s * .5); ctx.lineTo(s * .55, s * .5); ctx.lineTo(s * .1, s * .5); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-s * .55, 0); ctx.lineTo(s * .25, 0); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-s * .02, -s * .28); ctx.lineTo(s * .28, 0); ctx.lineTo(-s * .02, s * .28); ctx.stroke(); break;
    case 'merge':
      ctx.beginPath(); ctx.moveTo(-s * .38, -s * .38); ctx.lineTo(s * .38, 0); ctx.lineTo(-s * .38, s * .38);
      ctx.moveTo(-s * .38, -s * .38); ctx.lineTo(-s * .38, s * .38); ctx.stroke();
      [[-.38, -.38], [.38, 0], [-.38, .38]].forEach(p => { ctx.beginPath(); ctx.arc(p[0] * s, p[1] * s, s * .15, 0, 6.2832); ctx.fill(); }); break;
    case 'shield':
      ctx.beginPath(); ctx.moveTo(0, -s * .55); ctx.lineTo(s * .45, -s * .35); ctx.lineTo(s * .4, s * .15);
      ctx.quadraticCurveTo(s * .3, s * .45, 0, s * .58); ctx.quadraticCurveTo(-s * .3, s * .45, -s * .4, s * .15);
      ctx.lineTo(-s * .45, -s * .35); ctx.closePath(); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-s * .18, 0); ctx.lineTo(-s * .03, s * .16); ctx.lineTo(s * .2, -s * .14); ctx.stroke(); break;
    case 'search':
      ctx.beginPath(); ctx.arc(-s * .08, -s * .08, s * .32, 0, 6.2832); ctx.stroke();
      ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(s * .16, s * .16); ctx.lineTo(s * .46, s * .46); ctx.stroke(); break;
  }
  ctx.restore();
}

// ---------- gaya node menurut status ----------
function look(n, t, boost) {
  const s = n.state, L = {border: '#3f3f46', glow: 0, gcol: n.accent, a: 1, ico: '#a1a1aa',
    fill: '#1b1b1f', text: '#e4e4e7', sub: '#71717a', lw: 1.4};
  if (n.id === 'start' && s !== 'skipped') { L.border = n.accent; L.ico = n.accent; L.glow = 8; }
  if (s === 'running') { L.border = n.accent; L.ico = '#ffffff'; L.fill = '#1a2131';
    L.glow = 22 + (calm ? 0 : 8 * Math.sin(t * 4)); L.lw = 2.4; L.text = '#ffffff'; }
  else if (s === 'done') { L.border = 'rgba(244,244,245,.75)'; L.ico = n.accent; L.glow = 6; L.gcol = 'rgba(255,255,255,.35)'; L.lw = 1.6; }
  else if (s === 'failed') { L.border = '#f87171'; L.ico = '#f87171'; L.glow = 14; L.gcol = '#f87171'; }
  else if (s === 'skipped') { L.a = .35; L.border = '#3f3f46'; L.ico = '#52525b'; }
  if (boost > 0) { L.border = n.accent; L.gcol = n.accent; L.glow = Math.max(L.glow, 34 * boost); L.ico = n.accent; L.lw = 2.4; }
  return L;
}
function badge(n, x, y) {
  if (n.state !== 'done' && n.state !== 'failed') return;
  ctx.save(); ctx.fillStyle = n.state === 'done' ? '#22c55e' : '#ef4444';
  ctx.beginPath(); ctx.arc(x, y, 7, 0, 6.2832); ctx.fill();
  ctx.strokeStyle = '#0d0d10'; ctx.lineWidth = 2; ctx.stroke();
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.8; ctx.lineCap = 'round'; ctx.beginPath();
  if (n.state === 'done') { ctx.moveTo(x - 3, y); ctx.lineTo(x - .8, y + 2.4); ctx.lineTo(x + 3.2, y - 2.4); }
  else { ctx.moveTo(x - 2.6, y - 2.6); ctx.lineTo(x + 2.6, y + 2.6); ctx.moveTo(x + 2.6, y - 2.6); ctx.lineTo(x - 2.6, y + 2.6); }
  ctx.stroke(); ctx.restore();
}
function port(x, y, on, col, square) {
  ctx.save(); ctx.fillStyle = on ? col : '#52525b'; if (on) { ctx.shadowColor = col; ctx.shadowBlur = 8; }
  if (square) ctx.fillRect(x - 3.5, y - 5, 7, 10); else { ctx.beginPath(); ctx.arc(x, y, 4.6, 0, 6.2832); ctx.fill(); }
  ctx.restore();
}
function labels(n, y, L, size) {
  ctx.save(); ctx.globalAlpha = L.a; ctx.textAlign = 'center';
  ctx.font = `600 ${size}px ` + SANS; ctx.fillStyle = L.text; ctx.fillText(fit(n.label, 150), n.x, y);
  ctx.font = `400 ${size - 2.5}px ` + SANS; ctx.fillStyle = L.sub; ctx.fillText(fit(n.sub, 150), n.x, y + size + 2);
  ctx.restore();
}
function successRays(n, t, power) {
  ctx.save(); ctx.translate(n.x, n.y);
  const R = 70 + 30 * power, g = ctx.createRadialGradient(0, 0, 10, 0, 0, R * 1.5);
  g.addColorStop(0, `rgba(45,212,191,${.35 + .25 * power})`); g.addColorStop(.5, 'rgba(45,212,191,.12)'); g.addColorStop(1, 'rgba(45,212,191,0)');
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, R * 1.5, 0, 6.2832); ctx.fill();
  ctx.rotate(calm ? 0 : t * .15); ctx.strokeStyle = 'rgba(153,246,228,.55)'; ctx.lineCap = 'round';
  for (let i = 0; i < 28; i++) { const a = i / 28 * 6.2832, r0 = 46 + (i % 3) * 4,
    r1 = r0 + 14 + (i % 4) * 9 + (calm ? 0 : 6 * Math.sin(t * 2.2 + i)) + 24 * power;
    ctx.globalAlpha = .25 + .45 * ((i % 3) / 2); ctx.lineWidth = 1 + (i % 2);
    ctx.beginPath(); ctx.moveTo(Math.cos(a) * r0, Math.sin(a) * r0); ctx.lineTo(Math.cos(a) * r1, Math.sin(a) * r1); ctx.stroke(); }
  ctx.restore();
}

function drawSquare(n, t, boost) {
  const L = look(n, t, boost), x = n.x - SQ / 2, y = n.y - SQ / 2;
  ctx.save(); ctx.globalAlpha = L.a;
  if (L.glow) { ctx.shadowColor = L.gcol; ctx.shadowBlur = L.glow; }
  ctx.fillStyle = L.fill; rr(x, y, SQ, SQ, 14); ctx.fill(); ctx.shadowBlur = 0;
  ctx.lineWidth = L.lw; ctx.strokeStyle = L.border; if (n.state === 'skipped') ctx.setLineDash([4, 4]);
  rr(x, y, SQ, SQ, 14); ctx.stroke(); ctx.setLineDash([]);
  if (n.state === 'running' && !calm) { const k = (t * 1.1) % 1, g = k * 16; ctx.globalAlpha = (1 - k) * .8;
    ctx.strokeStyle = n.accent; ctx.lineWidth = 2; rr(x - g / 2, y - g / 2, SQ + g, SQ + g, 14 + g / 3); ctx.stroke(); ctx.globalAlpha = L.a; }
  icon(n.icon, n.x, n.y, 26, L.ico);
  if (n.id === 'start') { ctx.font = '700 13px ' + SANS; ctx.fillStyle = n.accent; ctx.fillText('ϟ', x - 16, n.y + 5); }
  const on = n.state === 'running' || n.state === 'done' || boost > 0;
  if (n.id !== 'answer') port(x + SQ, n.y, on, n.accent, false);
  if (n.id !== 'start') port(x, n.y, on, n.accent, true);
  ctx.restore();
  badge(n, x + SQ - 4, y + 4);
  labels(n, y + SQ + 18, L, 13);
}
function drawCard(n, t, boost) {
  const L = look(n, t, boost), x = n.x - CARD_W / 2, y = n.y - CARD_H / 2;
  ctx.save(); ctx.globalAlpha = L.a;
  if (L.glow) { ctx.shadowColor = L.gcol; ctx.shadowBlur = L.glow; }
  ctx.fillStyle = L.fill; rr(x, y, CARD_W, CARD_H, 12); ctx.fill(); ctx.shadowBlur = 0;
  ctx.lineWidth = L.lw; ctx.strokeStyle = L.border; if (n.state === 'skipped') ctx.setLineDash([4, 4]);
  rr(x, y, CARD_W, CARD_H, 12); ctx.stroke(); ctx.setLineDash([]);
  if ((n.state === 'running' || boost > .3) && !calm) {  // kilau berjalan di sisi atas kartu
    const u = (t * .7) % 1, sx = x + 14 + u * (CARD_W - 28), g = ctx.createLinearGradient(sx - 50, 0, sx + 50, 0);
    g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(.5, 'rgba(255,255,255,.95)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.strokeStyle = g; ctx.lineWidth = 2.6; ctx.shadowColor = '#fff'; ctx.shadowBlur = 10;
    ctx.beginPath(); ctx.moveTo(x + 12, y); ctx.lineTo(x + CARD_W - 12, y); ctx.stroke(); ctx.shadowBlur = 0;
  }
  icon('robot', x + 30, n.y + 1, 24, L.ico === '#a1a1aa' ? '#d4d4d8' : L.ico);
  ctx.textAlign = 'left'; ctx.font = '700 14px ' + SANS; ctx.fillStyle = L.text; ctx.fillText(fit(n.label, CARD_W - 70), x + 54, n.y - 3);
  ctx.font = '400 10.5px ' + SANS; ctx.fillStyle = L.sub;
  ctx.fillText(fit(n.state === 'running' && n.note ? n.note : n.sub, CARD_W - 70), x + 54, n.y + 13);
  const on = n.state === 'running' || n.state === 'done' || boost > 0;
  port(x + CARD_W, n.y, on, n.accent, false); port(x, n.y, on, n.accent, true);
  // port bawah (Chat Model / Output) seperti sub-node n8n
  ctx.font = '500 9px ' + SANS; ctx.textAlign = 'center';
  [[-55, 'Model'], [0, 'Memori'], [55, 'Output']].forEach(([dx, lb]) => {
    const px = n.x + dx, py = y + CARD_H; ctx.fillStyle = '#71717a'; ctx.fillText(lb, px, py + 15);
    ctx.save(); ctx.translate(px, py); ctx.rotate(Math.PI / 4); ctx.fillStyle = on && dx ? n.accent : '#52525b';
    ctx.fillRect(-3.5, -3.5, 7, 7); ctx.restore(); });
  ctx.restore();
  badge(n, x + CARD_W - 6, y + 6);
}
function drawCircle(n, t, boost) {
  const L = look(n, t, boost);
  ctx.save(); ctx.globalAlpha = L.a;
  if (L.glow) { ctx.shadowColor = L.gcol; ctx.shadowBlur = L.glow * .8; }
  ctx.fillStyle = L.fill; ctx.beginPath(); ctx.arc(n.x, n.y, SUB_R, 0, 6.2832); ctx.fill(); ctx.shadowBlur = 0;
  ctx.lineWidth = L.lw; ctx.strokeStyle = L.border; if (n.state === 'skipped') ctx.setLineDash([4, 4]);
  ctx.beginPath(); ctx.arc(n.x, n.y, SUB_R, 0, 6.2832); ctx.stroke(); ctx.setLineDash([]);
  icon(n.icon, n.x, n.y, 18, n.icon === 'model' && L.ico === '#a1a1aa' ? '#4da3ff' : L.ico);
  ctx.restore();
  labels(n, n.y + SUB_R + 15, L, 11);
}

// ---------- kabel ----------
const ESTYLE = {
  idle:  {c: 'rgba(161,161,170,.38)', w: 1.5},
  faint: {c: 'rgba(113,113,122,.22)', w: 1.2, dash: [4, 6]},
  skip:  {c: 'rgba(82,82,91,.28)', w: 1.2, dash: [4, 6]},
  hot:   {c: 'rgba(228,228,231,.62)', w: 1.8},
  live:  {c: null, w: 2.2},
  bad:   {c: 'rgba(248,113,113,.75)', w: 1.8},
};
function comet(e, u, col, a, size) {
  if (u <= 0 || u > 1.15) return; const tail = .28, n = 16;
  ctx.save(); ctx.lineCap = 'round';
  for (let k = n; k >= 0; k--) { const uu = u - tail * k / n; if (uu < 0 || uu > 1) continue;
    const [x, y] = at(e, uu), f = 1 - k / n;
    ctx.globalAlpha = a * f; ctx.fillStyle = k === 0 ? '#ffffff' : col; ctx.shadowColor = col; ctx.shadowBlur = 14 * f;
    ctx.beginPath(); ctx.arc(x, y, (size || 3.4) * (.35 + .65 * f), 0, 6.2832); ctx.fill(); }
  ctx.restore();
}
function drawEdgeBase(e, t, glowA) {
  const s = ESTYLE[e.cls] || ESTYLE.idle;
  ctx.save(); ctx.lineCap = 'round'; ctx.lineWidth = s.w; ctx.setLineDash(s.dash || []);
  if (e.kind === 'sub') ctx.setLineDash([3, 4]);
  ctx.strokeStyle = s.c || e.color;
  if (e.cls === 'live') { ctx.globalAlpha = .8; ctx.shadowColor = e.color; ctx.shadowBlur = 10; }
  ctx.stroke(e.p2d);
  if (glowA > 0) { ctx.globalAlpha = glowA; ctx.strokeStyle = e.color; ctx.lineWidth = 2.6; ctx.setLineDash([]);
    ctx.shadowColor = e.color; ctx.shadowBlur = 14; ctx.stroke(e.p2d); }
  ctx.restore();
  if (e.kind !== 'sub' && e.kind !== 'back' ) {  // panah kecil di ujung
    const [x2, y2] = at(e, 1), [x1, y1] = at(e, .96), ang = Math.atan2(y2 - y1, x2 - x1);
    if (e.cls === 'live' || e.cls === 'hot') { ctx.save(); ctx.translate(x2 - 5, y2); ctx.rotate(ang);
      ctx.fillStyle = e.cls === 'live' ? e.color : 'rgba(228,228,231,.7)';
      ctx.beginPath(); ctx.moveTo(-6, -4); ctx.lineTo(1, 0); ctx.lineTo(-6, 4); ctx.closePath(); ctx.fill(); ctx.restore(); }
  }
  if (e.label && (e.cls !== 'faint' || e.kind === 'back')) {
    const [lx, ly] = at(e, .5); ctx.save(); ctx.font = '500 10px ' + SANS; ctx.textAlign = 'center';
    ctx.fillStyle = e.cls === 'hot' || e.cls === 'live' ? '#d4d4d8' : '#52525b';
    ctx.fillText(e.label, lx + (e.kind === 'sub' ? 30 : 0), ly + (e.kind === 'back' ? 14 : (e.kind === 'sub' ? 3 : -8))); ctx.restore();
  }
}

// ---------- latar: grid titik + bintang kecil ----------
function grid() {
  const k = cam.k, step = 24 * k; if (step < 6) return;
  ctx.save(); ctx.fillStyle = 'rgba(255,255,255,.07)';
  const ox = ((cam.x % step) + step) % step, oy = ((cam.y % step) + step) % step;
  for (let x = ox; x < W; x += step) for (let y = oy; y < H; y += step) ctx.fillRect(x - .6, y - .6, 1.3, 1.3);
  ctx.restore();
}
function sparkle(x, y, r, a) {
  ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = '#e4e4e7'; ctx.shadowColor = '#fff'; ctx.shadowBlur = 8;
  ctx.beginPath(); ctx.moveTo(x, y - r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.quadraticCurveTo(x, y, x, y + r);
  ctx.quadraticCurveTo(x, y, x - r, y); ctx.quadraticCurveTo(x, y, x, y - r); ctx.fill(); ctx.restore();
}
function header() {
  const col = D.error ? '#f87171' : (D.live ? '#4da3ff' : (D.finished ? '#2dd4bf' : '#71717a'));
  ctx.save(); const g = ctx.createLinearGradient(0, 0, 0, 64); g.addColorStop(0, 'rgba(13,13,16,.95)'); g.addColorStop(1, 'rgba(13,13,16,0)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, 64);
  ctx.fillStyle = col; ctx.shadowColor = col; ctx.shadowBlur = 8; ctx.beginPath(); ctx.arc(20, 22, 4, 0, 6.2832); ctx.fill();
  ctx.shadowBlur = 0; ctx.textAlign = 'left'; ctx.font = '700 14px ' + SANS; ctx.fillStyle = '#f4f4f5'; ctx.fillText('Mesin Council', 32, 27);
  ctx.font = '500 11px ' + MONO; ctx.fillStyle = col === '#71717a' ? '#a1a1aa' : col; ctx.fillText(fit(D.status, Math.max(120, W - 260)), 32, 45);
  ctx.restore();
}
let hover = null;
function tooltip() {
  if (!hover) return; const n = hover;
  const rows = [['STATUS', n.word], ['PROVIDER', n.prov || '—'], ['DURASI', n.dur || '—']];
  const note = String(n.note || ''), w = 236, h = 82 + (note ? 30 : 0);
  let x = n.x * cam.k + cam.x + n.w / 2 * cam.k + 12, y = n.y * cam.k + cam.y - 40;
  if (x + w > W - 6) x = n.x * cam.k + cam.x - n.w / 2 * cam.k - w - 12;
  x = Math.max(6, x); y = Math.max(8, Math.min(H - h - 8, y));
  ctx.save(); ctx.fillStyle = 'rgba(24,24,27,.97)'; ctx.strokeStyle = 'rgba(255,255,255,.14)'; ctx.lineWidth = 1;
  ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 16; rr(x, y, w, h, 10); ctx.fill(); ctx.shadowBlur = 0; ctx.stroke();
  ctx.textAlign = 'left'; ctx.font = '700 11px ' + MONO; ctx.fillStyle = n.accent; ctx.fillText(n.label.toUpperCase(), x + 12, y + 20);
  ctx.font = '400 10px ' + MONO;
  rows.forEach((r, i) => { ctx.fillStyle = '#71717a'; ctx.fillText(r[0], x + 12, y + 40 + i * 14);
    ctx.fillStyle = '#e4e4e7'; ctx.fillText(fit(r[1], 130), x + 90, y + 40 + i * 14); });
  if (note) { ctx.fillStyle = '#a1a1aa'; ctx.font = '400 9.5px ' + MONO;
    ctx.fillText(note.slice(0, 36), x + 12, y + 90); if (note.length > 36) ctx.fillText(fit(note.slice(36), w - 24), x + 12, y + 103); }
  ctx.restore();
}

// ---------- loop utama ----------
function frame(ms) {
  const t = ms / 1000; if (t0 === null) t0 = t; const st = t - t0;
  const tgt = camTarget(st);
  if (tgt) { const f = calm ? 1 : .07; cam.k += (tgt.k - cam.k) * f; cam.x += (tgt.x - cam.x) * f; cam.y += (tgt.y - cam.y) * f; }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#0d0d10'; ctx.fillRect(0, 0, W, H); grid();
  ctx.setTransform(dpr * cam.k, 0, 0, dpr * cam.k, dpr * cam.x, dpr * cam.y);

  const sweeping = sweepOn && st < SWEEP_END;
  const boostOf = n => { if (!sweeping || n.state === 'skipped') return 0; const d = st - n.depth * STEP;
    return d < -0.05 ? 0 : Math.max(0, 1 - Math.abs(d) / (STEP * 1.6)); };

  // kabel: dasar + cahaya
  D.edges.forEach(e => {
    let glowA = 0;
    if (sweeping && e.kind !== 'back' && e.cls !== 'skip' && N[e.a]) { const d = N[e.a].depth, u = (st - d * STEP) / STEP;
      if (e.kind === 'sub') glowA = Math.max(0, 1 - Math.abs(u - .5) * 1.4) * .7;
      else if (u > 0 && u < 2.2) glowA = Math.max(0, .55 - (u - 1) * .35) * (u < 1 ? u : 1); }
    drawEdgeBase(e, t, glowA);
  });
  D.edges.forEach(e => {
    if (sweeping && e.kind !== 'back' && e.kind !== 'sub') { if (e.cls === 'skip') return;
      const u = (st - N[e.a].depth * STEP) / STEP; comet(e, u, e.color, 1, 4);
    } else if (!calm) {
      if (e.seqn > 1) {  // satu cahaya bersambung melewati node yang dilewati
        if (e.cls === 'live') { const ph = (t * .9) % (e.seqn + .6); comet(e, ph - e.seq, e.color, 1, 3.6); }
        else if (e.cls === 'hot') { const ph = (t * .35) % (e.seqn + 1.2); comet(e, ph - e.seq, e.color, .45, 2.6); }
      }
      else if (e.cls === 'live') { const sp = e.kind === 'sub' ? .9 : .7; comet(e, (t * sp) % 1.15, e.color, 1, 3.6);
        comet(e, (t * sp + .55) % 1.15, e.color, .7, 3); }
      else if (e.cls === 'hot' && e.kind !== 'sub') comet(e, (t * .22 + e.len * .003) % 1.6, e.color, .45, 2.6);
    }
  });

  // node
  const ans = N.answer;
  if (ans && ans.state === 'done' && !D.error) {
    const p = sweeping ? Math.max(0, 1 - Math.abs(st - ans.depth * STEP - .25) / .9) : 0;
    if (!sweeping || st > ans.depth * STEP - .2) successRays(ans, t, p);
  }
  D.nodes.forEach(n => { const b = boostOf(n);
    if (n.kind === 'square') drawSquare(n, t, b); else if (n.kind === 'card') drawCard(n, t, b); else drawCircle(n, t, b); });

  // lapisan layar
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  header(); tooltip();
  sparkle(W - 26, H - 26, 9, calm ? .8 : .55 + .35 * Math.sin(t * 1.6));
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

// ---------- interaksi: Ctrl/⌘+scroll zoom, seret untuk geser, klik ganda kembali otomatis ----------
const bF = document.getElementById('b-follow'), bFit = document.getElementById('b-fit');
function setMode(m) { mode = m; save('aog_wf_mode', m); bF.className = m === 'auto' ? 'on' : ''; bFit.className = m === 'fit' ? 'on' : ''; }
setMode(mode);
setInterval(() => save('aog_wf_cam', {k: cam.k, x: cam.x, y: cam.y}), 500);
function zoomAt(px, py, f) { const k = Math.max(.25, Math.min(2.5, cam.k * f));
  cam.x = px - (px - cam.x) * (k / cam.k); cam.y = py - (py - cam.y) * (k / cam.k); cam.k = k; setMode('manual'); }
bF.onclick = () => setMode('auto'); bFit.onclick = () => setMode('fit');
document.getElementById('b-in').onclick = () => zoomAt(W / 2, H / 2, 1.2);
document.getElementById('b-out').onclick = () => zoomAt(W / 2, H / 2, 1 / 1.2);
function spos(e) { const r = cv.getBoundingClientRect(); return {x: e.clientX - r.left, y: e.clientY - r.top}; }
function pick(p) { const wx = (p.x - cam.x) / cam.k, wy = (p.y - cam.y) / cam.k;
  for (let i = D.nodes.length - 1; i >= 0; i--) { const n = D.nodes[i];
    if (Math.abs(wx - n.x) <= n.w / 2 && Math.abs(wy - n.y) <= n.h / 2) return n; } return null; }
let drag = null;
cv.addEventListener('wheel', e => { if (!(e.ctrlKey || e.metaKey)) return; e.preventDefault();
  const p = spos(e); zoomAt(p.x, p.y, Math.exp(-e.deltaY * .0025)); }, {passive: false});
cv.addEventListener('pointerdown', e => { const p = spos(e); drag = {x: p.x, y: p.y, cx: cam.x, cy: cam.y, moved: false};
  cv.setPointerCapture(e.pointerId); });
cv.addEventListener('pointermove', e => { const p = spos(e);
  if (drag) { const dx = p.x - drag.x, dy = p.y - drag.y;
    if (drag.moved || Math.abs(dx) + Math.abs(dy) > 4) { drag.moved = true; setMode('manual');
      cam.x = drag.cx + dx; cam.y = drag.cy + dy; cv.className = 'drag'; } return; }
  hover = pick(p); cv.className = hover ? 'hov' : ''; });
cv.addEventListener('pointerup', () => { drag = null; cv.className = hover ? 'hov' : ''; });
cv.addEventListener('pointerleave', () => { hover = null; });
cv.addEventListener('dblclick', () => setMode('auto'));
</script></body></html>
"""


FLOW_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  html,body{margin:0;padding:0;background:transparent;overflow:hidden;font-family:'Inter',sans-serif;}
  canvas{display:block;}
</style></head>
<body><canvas id="c"></canvas>
<svg style="position:absolute;width:0;height:0;visibility:hidden"><path id="meas" d="M0,0"/></svg>
<script>
__COMMON__
const D = __DATA__;
const VW = 300, VH = 620;

// Panel dipusatkan di iframe; bila kolom lebih sempit dari 300px, panel mengecil mengikuti lebar.
let scale = 1, W = VW, H = VH, ox = 0;
function resize() {
  W = document.documentElement.clientWidth || VW; scale = Math.min(1, W / VW);
  H = Math.round(VH * scale); ox = (W - VW * scale) / 2;
  cv.style.width = W + 'px'; cv.style.height = H + 'px';
  cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
  sizeFrame(H + 2);
}
window.addEventListener('resize', resize); resize();

function drawPanel(t) {
  const G = D.graph; ctx.save();
  ctx.fillStyle = 'rgba(16,11,37,.88)'; ctx.strokeStyle = 'rgba(139,92,246,.45)'; ctx.lineWidth = 1;
  rr(0, 10, 300, 600, 16); ctx.fill(); ctx.stroke();
  ctx.font = '800 17px ' + SANS; ctx.textAlign = 'center'; ctx.fillStyle = '#f1eaff'; ctx.fillText('Alur Council', 150, 46);
  G.edges.forEach(e => drawEdge(e.d, e.cls, t, e.label, e.label ? e.lx : undefined, e.ly));
  G.boxes.forEach(b => {
    const p = pal(b.state, '#59428b'); ctx.save(); ctx.globalAlpha = p.a;
    ctx.fillStyle = p.fill; ctx.strokeStyle = p.line; ctx.lineWidth = b.state === 'running' ? 2 : 1.4;
    if (p.glow) { ctx.shadowColor = p.glow; ctx.shadowBlur = b.state === 'running' ? 16 : 8; }
    if (b.state === 'skipped') ctx.setLineDash([3, 5]);
    if (b.shape === 'diamond') { ctx.beginPath(); ctx.moveTo(b.x, b.y - b.h / 2); ctx.lineTo(b.x + b.w / 2, b.y);
      ctx.lineTo(b.x, b.y + b.h / 2); ctx.lineTo(b.x - b.w / 2, b.y); ctx.closePath(); }
    else rr(b.x - b.w / 2, b.y - b.h / 2, b.w, b.h, b.shape === 'pill' ? b.h / 2 : 10);
    ctx.fill(); ctx.shadowBlur = 0; ctx.stroke(); ctx.setLineDash([]);
    ctx.font = '600 11px ' + SANS; ctx.fillStyle = p.text; ctx.textAlign = 'center'; ctx.globalAlpha = 1;
    ctx.fillText(b.label, b.x, b.y + 4); ctx.restore();
  });
  ctx.restore();
}

function frame(ms) {
  const t = ms / 1000;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
  ctx.setTransform(dpr * scale, 0, 0, dpr * scale, dpr * ox, 0);
  drawPanel(t);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
</script></body></html>
"""
