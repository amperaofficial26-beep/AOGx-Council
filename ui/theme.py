"""Gaya visual panel proses + chat (CSS murni, dipakai lewat st.markdown)."""

CSS = """
<style>
@keyframes aogpulse { 0%,100% { stroke-opacity:.5 } 50% { stroke-opacity:1 } }
@keyframes aogdash { to { stroke-dashoffset:-24 } }
@keyframes aogblink { 0%,100% { opacity:.35 } 50% { opacity:1 } }

.aog-svg { width:100%; height:auto; display:block; }
.aog-n .aog-box { fill:#0e1726; stroke:#25344c; stroke-width:1.2; transition:all .35s ease; }
.aog-n .aog-lb { fill:#8b9bb4; font-size:12.5px; font-weight:600; }
.aog-n .aog-sb { fill:#5c6c86; font-size:9.5px; }
.aog-n .aog-tg { fill:#46566e; font-size:8.5px; font-family:ui-monospace,Menlo,monospace; }
.aog-n .aog-dot { fill:#334155; }

.aog-n-pending .aog-box { stroke-dasharray:4 4; fill:#0a111d; }
.aog-n-running .aog-box { fill:#0b2233; stroke:#38bdf8; stroke-width:1.6;
  filter:url(#aogGlow); animation:aogpulse 1.5s ease-in-out infinite; }
.aog-n-running .aog-lb { fill:#e0f2fe; }
.aog-n-running .aog-sb { fill:#7dd3fc; }
.aog-n-running .aog-dot { fill:#38bdf8; }
.aog-n-done .aog-box { fill:#0a1f18; stroke:#22c55e; }
.aog-n-done .aog-lb { fill:#dcfce7; } .aog-n-done .aog-sb { fill:#86efac; }
.aog-n-done .aog-dot { fill:#22c55e; }
.aog-n-failed .aog-box { fill:#25121a; stroke:#f87171; }
.aog-n-failed .aog-lb { fill:#fecaca; } .aog-n-failed .aog-sb { fill:#f87171; }
.aog-n-failed .aog-dot { fill:#f87171; }
.aog-n-skipped .aog-box { fill:#0a111d; stroke:#2b3a52; stroke-dasharray:3 5; }
.aog-n-skipped .aog-lb { fill:#4d5f79; } .aog-n-skipped .aog-sb { fill:#3f5170; }

.aog-e { fill:none; stroke:#243349; stroke-width:1.3; }
.aog-e-idle { stroke:#22314a; stroke-dasharray:3 6; }
.aog-e-hot { stroke:#3b82f6; stroke-width:1.8; stroke-dasharray:5 7;
  animation:aogdash 1.4s linear infinite; }
.aog-e-live { stroke:#38bdf8; stroke-width:2.2; stroke-dasharray:5 7;
  animation:aogdash .7s linear infinite; filter:url(#aogGlow); }
.aog-e-bad { stroke:#f87171; stroke-dasharray:2 5; }
.aog-e-skip { stroke:#182335; stroke-dasharray:2 7; }
.aog-el { fill:#3f4f68; font-size:9px; font-weight:600; text-anchor:middle; letter-spacing:.3px; }
.aog-el-hot, .aog-el-live { fill:#7dd3fc; }
.aog-el-skip { fill:#2b3a52; }

.aog-stage { background:linear-gradient(180deg,#0b1220,#070d16); border:1px solid #1b2739;
  border-radius:16px; padding:12px 14px 8px; }
.aog-panel { background:#080e18; border:1px solid #1b2739; border-radius:14px; padding:9px 11px; }
.aog-chips { display:flex; flex-wrap:wrap; gap:8px; }
.aog-chip { background:#0e1726; border:1px solid #22314a; border-radius:10px;
  padding:5px 10px; min-width:74px; }
.aog-chip span { display:block; font-size:8.5px; text-transform:uppercase;
  letter-spacing:.9px; color:#5c6c86; }
.aog-chip b { font-size:12.5px; color:#cbd5e1; font-weight:600; }
.aog-legend { display:flex; flex-wrap:wrap; gap:12px; margin-top:6px; font-size:10.5px; color:#64748b; }
.aog-legend i { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px; }

.aog-log { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11.5px;
  line-height:1.5; max-height:250px; overflow-y:auto; }
.aog-row { display:flex; gap:8px; padding:3px 0; border-bottom:1px solid #111c2c; }
.aog-row:last-child { border-bottom:0; }
.aog-t { color:#3f5170; min-width:44px; }
.aog-r { color:#e2e8f0; font-weight:600; min-width:84px; }
.aog-s { color:#7dd3fc; min-width:118px; }
.aog-p { color:#a3e635; min-width:72px; }
.aog-x { color:#8b9bb4; flex:1; white-space:pre-wrap; word-break:break-word; }
.aog-bad .aog-x, .aog-bad .aog-r { color:#fca5a5; }
.aog-empty { opacity:.65; }

.aog-colhead { font-size:11px; text-transform:uppercase; letter-spacing:1.2px;
  color:#475569; font-weight:700; margin:2px 0 8px; }
.aog-live { display:flex; align-items:center; gap:8px; color:#7dd3fc; font-size:12.5px;
  background:#0b1624; border:1px solid #1c2b42; border-radius:12px; padding:8px 11px; }
.aog-live b { animation:aogblink 1.2s ease-in-out infinite; font-size:14px; }
.aog-warn { background:#1c1608; border:1px solid #4a3a12; border-radius:12px;
  padding:9px 12px; color:#fcd34d; font-size:12.5px; }
</style>
"""

LEGEND = """
<div class="aog-legend">
  <span><i style="background:#334155"></i>menunggu</span>
  <span><i style="background:#38bdf8"></i>berjalan</span>
  <span><i style="background:#22c55e"></i>selesai</span>
  <span><i style="background:#f87171"></i>gagal</span>
  <span><i style="background:#2b3a52"></i>dilewati</span>
</div>
"""


def stage(html_body: str) -> str:
    return f'<div class="aog-stage">{html_body}</div>'


def panel(html_body: str) -> str:
    return f'<div class="aog-panel">{html_body}</div>'
