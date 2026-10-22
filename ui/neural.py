"""Mesin Council bergaya 'Neural Architect': kartu node di kanvas, partikel sinyal, bisa digeser.

Berbeda dari ui/machine.py (SVG lewat st.markdown), modul ini membuat dokumen HTML dengan
<canvas> + JavaScript lalu menampilkannya lewat st.components.v1.html, karena Streamlit tidak
menjalankan <script> di dalam st.markdown. Status node dibaca dari CouncilFlow (sama seperti
machine.py), jadi pipeline dan CouncilFlow tidak perlu diubah.

Ada dua komponen terpisah:
- show()      : kanvas "Mesin Council" selebar kolom penuh (kartu agen).
- show_flow() : panel "Alur Council" (diagram keputusan), diletakkan app.py di bawah mesin,
                bersampingan dengan "Jejak langkah".
"""
import json

from ui.flow import DEBATERS, NODES
from ui.machine import CUBE_EDGES, STATE_WORD, debate_state, edge_cls, node_state, norm

HEIGHT = 450        # tinggi awal iframe mesin; JavaScript menyesuaikannya dengan lebar kolom
FLOW_HEIGHT = 622   # tinggi awal iframe Alur Council

# Posisi kartu pada kanvas mesin (viewBox 1000 x 490). Kanvas sekarang memakai seluruh lebar,
# karena panel Alur Council sudah dipindah keluar dari kanvas ini.
POS = {
    "orchestrator": (150, 120),
    "researcher":   (500, 120),
    "expert":       (850, 120),
    "analyst":      (150, 270),
    "skeptic":      (500, 270),
    "synthesizer":  (850, 270),
    "verifier":     (500, 420),
}
START_POS = (150, 420)
ANSWER_POS = (850, 420)


def _node(flow, name: str, x: int, y: int, label: str, sub: str) -> dict:
    state = node_state(flow, name)
    return {"id": name, "x": x, "y": y, "label": label, "sub": sub, "state": state,
            "word": STATE_WORD[state], "prov": flow.providers.get(name, ""),
            "dur": flow.durations.get(name, ""), "note": flow.notes.get(name, "")}


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


def payload(flow) -> dict:
    """Data murni (JSON) untuk kanvas mesin; tidak memanggil Streamlit sehingga bisa diuji."""
    if flow.error:
        status = "Berhenti karena galat"
    elif flow.finished:
        status = "Selesai"
    else:
        status = flow.stage_text or "Menunggu pertanyaan"

    nodes = [_node(flow, "start", START_POS[0], START_POS[1], "User Input", "Pertanyaan pengguna")]
    for name, (x, y) in POS.items():
        g = NODES[name]
        nodes.append(_node(flow, name, x, y, g["label"], flow.notes.get(name) or g["sub"]))
    nodes.append(_node(flow, "answer", ANSWER_POS[0], ANSWER_POS[1], "Jawaban final", "Council response"))

    edges = [("start", "orchestrator", "", False), ("verifier", "answer", "", False)]
    edges += [(s, d, lb, s == "verifier") for s, d, lb, _ in CUBE_EDGES]
    out_edges = []
    for src, dst, label, back in edges:
        cls = edge_cls(node_state(flow, src), node_state(flow, dst))
        if back:  # sisi revisi hanya menyala bila memang ada putaran ulang
            cls = "hot" if flow.attempt > 0 else "idle"
        out_edges.append({"src": src, "dst": dst, "label": label, "cls": cls, "back": back})

    live = any(norm(flow.state(n)) == "running" for n in POS)
    return {"status": status, "live": live, "nodes": nodes, "edges": out_edges,
            "graph": _graph(flow), "debaters": list(DEBATERS)}


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
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  html,body{margin:0;padding:0;background:#030712;overflow:hidden;font-family:'Inter',sans-serif;}
  #wrap{position:relative;box-sizing:border-box;width:100%;border-radius:16px;overflow:hidden;border:1px solid rgba(56,189,248,.15);
        box-shadow:0 8px 32px rgba(0,0,0,.37);background:radial-gradient(ellipse at 50% 45%,#0c1a3a 0%,#050b18 60%,#030712 100%);}
  canvas{display:block;cursor:grab;}
  canvas.drag{cursor:grabbing;} canvas.hov{cursor:pointer;}
  .scan{position:absolute;inset:0;pointer-events:none;
        background:linear-gradient(to bottom,transparent 50%,rgba(6,182,212,.03) 51%);background-size:100% 4px;}
</style></head>
<body><div id="wrap"><canvas id="c"></canvas><div class="scan"></div></div>
<svg style="position:absolute;width:0;height:0;visibility:hidden"><path id="meas" d="M0,0"/></svg>
<script>
__COMMON__
const D = __DATA__;
const VW = 1000, VH = 490, CW = 190, CH = 90;
const THEME = {orchestrator:'#36cfff', verifier:'#36cfff', researcher:'#d45bff', skeptic:'#d45bff',
               analyst:'#ffad38', expert:'#ffad38', synthesizer:'#ff5ca8', start:'#ff9e43', answer:'#ff6ba9'};

let scale = 1, W = 1000, H = VH;
function resize() {
  W = (document.documentElement.clientWidth || VW) - 2; scale = W / VW; H = Math.round(VH * scale);
  cv.style.width = W + 'px'; cv.style.height = H + 'px';
  cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
  sizeFrame(H + 2);
}
window.addEventListener('resize', resize); resize();

// ---- node (posisi bisa digeser; disimpan di localStorage bila tersedia) ----
const nodes = {}; D.nodes.forEach(n => { n.w = CW; n.h = CH; n.phase = Math.random() * 6.28; nodes[n.id] = n; });
try { const sv = JSON.parse(localStorage.getItem('aog_pos2') || '{}');
      for (const k in sv) if (nodes[k]) { nodes[k].x = sv[k][0]; nodes[k].y = sv[k][1]; } } catch (e) {}
function savePos() { try { const o = {}; for (const k in nodes) o[k] = [Math.round(nodes[k].x), Math.round(nodes[k].y)];
                           localStorage.setItem('aog_pos2', JSON.stringify(o)); } catch (e) {} }

// ---- jalur kabel antar kartu (dihitung ulang tiap frame agar ikut saat digeser) ----
function cablePath(a, b, back) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const s = Math.min((CW / 2) / Math.max(Math.abs(dx), 1), (CH / 2) / Math.max(Math.abs(dy), 1));
  let x1 = a.x + dx * s, y1 = a.y + dy * s, x2 = b.x - dx * s, y2 = b.y - dy * s;
  if (back) {
    const len = Math.hypot(dx, dy) || 1, nx = -dy / len, ny = dx / len, off = 48;
    return `M${x1 + nx * 10},${y1 + ny * 10} Q${(x1 + x2) / 2 + nx * off},${(y1 + y2) / 2 + ny * off} ${x2 + nx * 10},${y2 + ny * 10}`;
  }
  const mx = (x1 + x2) / 2;
  return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
}

// ---- latar ----
const stars = Array.from({length: 24}, (_, i) => ({x: 30 + (i * 173) % 940, y: 70 + (i * 97) % 400, r: 1 + (i % 3) * .5, p: i * .7}));
function background(t) {
  ctx.save(); ctx.fillStyle = 'rgba(56,189,248,.17)';
  for (let x = 20; x < VW; x += 32) for (let y = 20; y < VH; y += 32) ctx.fillRect(x, y, 1.2, 1.2);
  stars.forEach(s => { ctx.globalAlpha = calm ? .4 : .15 + .7 * (.5 + .5 * Math.sin(t * 1.4 + s.p));
    ctx.fillStyle = '#c7aaff'; ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 6.2832); ctx.fill(); });
  ctx.restore();
}
function header(t) {
  const col = D.live ? '#22d3ee' : (D.status === 'Selesai' ? '#34d399' : '#64748b');
  ctx.save();
  if (D.live && !calm) { const k = (t * 1.2) % 1; ctx.globalAlpha = 1 - k; ctx.strokeStyle = col;
    ctx.beginPath(); ctx.arc(30, 27, 4 + k * 8, 0, 6.2832); ctx.stroke(); ctx.globalAlpha = 1; }
  ctx.fillStyle = col; ctx.shadowColor = col; ctx.shadowBlur = 8; ctx.beginPath(); ctx.arc(30, 27, 4, 0, 6.2832); ctx.fill();
  ctx.shadowBlur = 0; ctx.font = '700 15px ' + SANS; ctx.fillStyle = '#e0f2fe'; ctx.fillText('Mesin Council', 44, 32);
  ctx.font = '500 11px ' + MONO; ctx.fillStyle = '#83dfff'; ctx.fillText(fit(D.status, 330), 44, 52);
  ctx.restore();
}

// ---- kartu agen ----
function bob(n, t) { return calm ? 0 : Math.sin(t * 0.9 + n.phase) * 1.6; }
let hover = null, drag = null, off = {x: 0, y: 0};
function drawCard(n, t) {
  const p = pal(n.state, THEME[n.id] || '#7661ff'), by = bob(n, t);
  const x = n.x - CW / 2, y = n.y - CH / 2 + by, isH = hover === n || drag === n;
  ctx.save();
  if (n.state === 'running' && !calm) {  // cincin denyut seperti pada Neural Architect
    const k = (t * 1.1) % 1, g = k * 18; ctx.globalAlpha = 1 - k; ctx.strokeStyle = p.glow; ctx.lineWidth = 2;
    rr(x - g / 2, y - g / 2, CW + g, CH + g, 16 + g / 3); ctx.stroke(); ctx.globalAlpha = 1;
  }
  ctx.globalAlpha = p.a;
  ctx.shadowColor = p.glow || 'rgba(0,0,0,.5)'; ctx.shadowBlur = isH ? 26 : (p.glow ? 18 : 8);
  ctx.fillStyle = p.fill; rr(x, y, CW, CH, 14); ctx.fill();
  ctx.shadowBlur = 0; ctx.lineWidth = isH ? 2.6 : (n.state === 'running' ? 2.4 : 1.6); ctx.strokeStyle = p.line;
  if (n.state === 'skipped') ctx.setLineDash([5, 5]);
  rr(x, y, CW, CH, 14); ctx.stroke(); ctx.setLineDash([]);
  // penanda status (kiri) + header kecil
  ctx.fillStyle = p.line; ctx.shadowColor = p.line; ctx.shadowBlur = n.state === 'skipped' ? 0 : 8;
  ctx.beginPath(); ctx.arc(x + 16, n.y + by - 10, 4, 0, 6.2832); ctx.fill(); ctx.shadowBlur = 0;
  ctx.textAlign = 'center';
  ctx.font = '700 14px ' + SANS; ctx.fillStyle = p.text; ctx.fillText(fit(n.label, CW - 50), n.x + 4, y + 30);
  ctx.font = '400 10px ' + MONO; ctx.fillStyle = p.sub; ctx.fillText(fit(n.sub, CW - 24), n.x, y + 47);
  ctx.font = '600 9px ' + MONO; ctx.fillStyle = p.text;
  const tag = [n.word, n.prov, n.dur].filter(Boolean).join(' · ');
  ctx.fillText(fit(tag, CW - 24), n.x, y + 63);
  // bar mini (sapuan saat berjalan, penuh saat selesai)
  const bx = x + 12, bw = CW - 24, byy = y + CH - 14;
  ctx.fillStyle = 'rgba(30,41,59,.85)'; rr(bx, byy, bw, 4, 2); ctx.fill();
  if (n.state === 'done' || n.state === 'failed') { ctx.fillStyle = p.line; rr(bx, byy, bw, 4, 2); ctx.fill(); }
  else if (n.state === 'running') {
    ctx.save(); rr(bx, byy, bw, 4, 2); ctx.clip(); const seg = bw * .35, u = calm ? .3 : ((t * .8) % 1);
    ctx.fillStyle = p.line; ctx.fillRect(bx + u * (bw + seg) - seg, byy, seg, 4); ctx.restore();
  }
  ctx.restore();
}
function tooltip() {
  if (!hover) return; const n = hover, rows = [['STATUS', n.word], ['PROVIDER', n.prov || '—'], ['DURASI', n.dur || '—']];
  const w = 230, note = String(n.note || n.sub || ''), h = 84 + (note ? 30 : 0);
  let x = n.x + CW / 2 + 12, y = n.y - 40; if (x + w > VW - 6) x = n.x - CW / 2 - w - 12;
  y = Math.max(8, Math.min(VH - h - 8, y));
  ctx.save(); ctx.fillStyle = 'rgba(15,23,42,.96)'; ctx.strokeStyle = 'rgba(56,189,248,.35)'; ctx.lineWidth = 1;
  ctx.shadowColor = 'rgba(56,189,248,.25)'; ctx.shadowBlur = 16; rr(x, y, w, h, 12); ctx.fill(); ctx.shadowBlur = 0; ctx.stroke();
  ctx.font = '700 11px ' + MONO; ctx.fillStyle = '#a5f3fc'; ctx.fillText(n.label.toUpperCase(), x + 12, y + 20);
  ctx.font = '400 10px ' + MONO;
  rows.forEach((r, i) => { ctx.fillStyle = '#64748b'; ctx.fillText(r[0], x + 12, y + 40 + i * 15);
                           ctx.fillStyle = '#e2e8f0'; ctx.fillText(fit(r[1], 130), x + 90, y + 40 + i * 15); });
  if (note) { ctx.fillStyle = '#94a3b8'; ctx.font = '400 9.5px ' + MONO;
    const a = note.slice(0, 34), b = note.slice(34, 68); ctx.fillText(a, x + 12, y + 92); if (b) ctx.fillText(b, x + 12, y + 104); }
  ctx.restore();
}

// ---- loop utama ----
function frame(ms) {
  const t = ms / 1000; ctx.setTransform(dpr * scale, 0, 0, dpr * scale, 0, 0); ctx.clearRect(0, 0, VW, VH);
  background(t); header(t);
  D.edges.forEach(e => { const a = nodes[e.src], b = nodes[e.dst];
    drawEdge(cablePath(a, b, e.back), e.cls, t, e.label, undefined, undefined); });
  D.nodes.forEach(n => drawCard(n, t));
  tooltip();
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

// ---- interaksi: hover untuk detail, seret untuk memindahkan node ----
function pos(e) { const r = cv.getBoundingClientRect(); return {x: (e.clientX - r.left) / scale, y: (e.clientY - r.top) / scale}; }
function pick(p) { for (let i = D.nodes.length - 1; i >= 0; i--) { const n = D.nodes[i];
  if (Math.abs(p.x - n.x) <= CW / 2 && Math.abs(p.y - n.y) <= CH / 2) return n; } return null; }
cv.addEventListener('mousedown', e => { const p = pos(e), n = pick(p); if (n) { drag = n; off = {x: p.x - n.x, y: p.y - n.y}; cv.className = 'drag'; } });
cv.addEventListener('mousemove', e => { const p = pos(e);
  if (drag) { drag.x = Math.max(CW / 2, Math.min(VW - CW / 2, p.x - off.x)); drag.y = Math.max(CH / 2, Math.min(VH - CH / 2, p.y - off.y)); return; }
  hover = pick(p); cv.className = hover ? 'hov' : ''; });
cv.addEventListener('mouseleave', () => { hover = null; });
window.addEventListener('mouseup', () => { if (drag) { drag = null; cv.className = ''; savePos(); } });
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
