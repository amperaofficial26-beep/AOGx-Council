"""Gaya visual panel proses + chat (CSS murni, dipakai lewat st.markdown)."""

CSS = """
<style>
@keyframes aogpulse { 0%,100% { stroke-opacity:.5 } 50% { stroke-opacity:1 } }
@keyframes aogdash { to { stroke-dashoffset:-24 } }
@keyframes aogblink { 0%,100% { opacity:.35 } 50% { opacity:1 } }
@keyframes aogelectric { 0%,100% { opacity:.62 } 50% { opacity:1 } }
@keyframes aogcharge { to { stroke-dashoffset:-34 } }

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

.aog-e { fill:none; stroke:#9a86ff; stroke-width:2.2; stroke-linecap:round; stroke-dasharray:8 7;
  animation:aogcharge .85s linear infinite; filter:url(#aogGlow); }
.aog-e-glow { fill:none; stroke:#9268ff; stroke-width:9; stroke-linecap:round; opacity:.26;
  filter:url(#aogGlow); animation:aogelectric 1.05s ease-in-out infinite; }
.aog-e-idle { stroke:#b39cff; }
.aog-e-glow.aog-e-idle { stroke:#8c64ff; }
.aog-e-hot { stroke:#ff77e9; stroke-width:2.8; animation:aogcharge .55s linear infinite; }
.aog-e-glow.aog-e-hot { stroke:#fa58dc; opacity:.42; }
.aog-e-live { stroke:#8efaff; stroke-width:3.4; animation:aogcharge .3s linear infinite; }
.aog-e-glow.aog-e-live { stroke:#37e8ff; opacity:.56; }
.aog-e-bad { stroke:#ff718f; }
.aog-e-glow.aog-e-bad { stroke:#ff516f; }
.aog-e-skip { stroke:#33405a; stroke-dasharray:3 8; animation:none; filter:none; }
.aog-e-particle { fill:#edddff; filter:url(#aogGlow); opacity:.98; }
.aog-p-soft { opacity:.58; }
.aog-p-live { fill:#c5ffff; }
.aog-p-hot { fill:#ffd5ff; }
.aog-p-bad { fill:#ffc2ca; }
.aog-el { fill:#8a7dbb; font-size:9px; font-weight:600; text-anchor:middle; letter-spacing:.3px; }
.aog-el-hot, .aog-el-live { fill:#e4c9ff; }
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

/* Composer gelap berbentuk kapsul dengan halo RGB bergerak di belakangnya. */
@keyframes aogComposerGlow {
  0%,100% { filter:blur(24px) hue-rotate(0deg); opacity:.22; }
  50% { filter:blur(30px) hue-rotate(150deg); opacity:.42; }
}
[data-testid="stChatInput"] {
  position:relative; isolation:isolate; overflow:visible !important;
  background:transparent !important; border:0 !important; border-radius:999px !important;
  padding:8px !important; box-shadow:none !important;
}
[data-testid="stChatInput"]::before {
  content:""; position:absolute; z-index:-1; inset:-5px; border-radius:999px;
  background:linear-gradient(90deg,#24d8ff,#8c55ff,#ff69bc,#45f3ad);
  filter:blur(24px); opacity:.28; animation:aogComposerGlow 9s ease-in-out infinite;
  pointer-events:none;
}
[data-testid="stChatInput"] > div {
  background:#0d1523 !important; border:1px solid #263750 !important;
  border-radius:999px !important; box-shadow:0 0 18px rgba(73,139,255,.12) !important;
}
[data-testid="stChatInput"] textarea {
  color:#e5eaf4 !important; font-size:14px !important; min-height:44px !important;
  background:transparent !important;
}
[data-testid="stChatInput"] textarea::placeholder { color:#9aa6b8 !important; opacity:1; }
[data-testid="stChatInput"] button {
  background:#3478dc !important; color:#fff !important; border-radius:50% !important;
  min-width:44px !important; min-height:44px !important; border:0 !important;
}
[data-testid="stChatInput"] button:hover { background:#2467c7 !important; }
[data-testid="stChatInput"] [data-testid="stFileUploaderFile"] {
  background:#111c2d; border:1px solid #263750; border-radius:14px;
}
[data-testid="stForm"] { padding:0 !important; border:0 !important; }
[data-testid="stTextInput"] label { font-size:10px !important; line-height:1.1 !important;
  margin-bottom:1px !important; }
[data-testid="stTextInput"] [data-baseweb="input"] {
  border:1px solid #2a3547 !important; border-radius:12px !important;
  min-height:33px; background:#0d1523 !important;
}
[data-testid="stTextInput"] input { padding-top:4px !important; padding-bottom:4px !important; }
[data-testid="stFormSubmitButton"] button { min-height:34px !important; height:34px !important;
  border-radius:11px !important; padding-top:3px !important; padding-bottom:3px !important; }
@media (prefers-reduced-motion: reduce) {
  [data-testid="stChatInput"]::before { animation:none; opacity:.24; }
}
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
