"""Animasi loading 'thinking' Council: orb neural berputar, teks berkilau, gelombang sinyal.

CSS murni (tanpa JavaScript) sehingga aman dipakai lewat st.markdown(unsafe_allow_html=True)
dan diganti-ganti tiap event pipeline lewat placeholder st.empty().
"""
import html

BARS = 14

CSS = """
<style>
@keyframes aogSpin { to { transform: rotate(360deg); } }
@keyframes aogShimmer { to { background-position: -220% 0; } }
@keyframes aogWave { 0%,100% { transform: scaleY(.22); opacity: .4; } 50% { transform: scaleY(1); opacity: 1; } }
@keyframes aogDot { 0%,80%,100% { transform: translateY(0); opacity: .25; } 40% { transform: translateY(-4px); opacity: 1; } }
@keyframes aogSweep { 0% { transform: translateX(-110%); } 100% { transform: translateX(280%); } }
@keyframes aogCore { 0%,100% { transform: scale(.8); filter: brightness(.9); } 50% { transform: scale(1.18); filter: brightness(1.4); } }
@keyframes aogEnter { from { opacity: 0; transform: translateY(6px) scale(.985); } to { opacity: 1; transform: none; } }

.aog-think { position: relative; display: flex; align-items: center; gap: 14px; padding: 12px 15px 15px;
  border-radius: 14px; overflow: hidden; isolation: isolate; background: #0b1624;
  animation: aogEnter .35s ease-out both; }
.aog-think::before { content: ""; position: absolute; z-index: -2; inset: -80%;
  background: conic-gradient(from 0deg, transparent 0 58%, #22d3ee 72%, #8b5cf6 86%, #ff69bc 94%, transparent 100%);
  animation: aogSpin 3.4s linear infinite; }
.aog-think::after { content: ""; position: absolute; z-index: -1; inset: 1.5px; border-radius: 12.5px;
  background: linear-gradient(180deg, #0d1a2c, #07101f); }

.aog-orb { position: relative; width: 42px; height: 42px; flex: none; }
.aog-orb i { position: absolute; inset: 0; border-radius: 50%; border: 1px solid rgba(56,189,248,.28);
  animation: aogSpin 2.4s linear infinite; }
.aog-orb i::before { content: ""; position: absolute; top: -3px; left: 50%; width: 6px; height: 6px; margin-left: -3px;
  border-radius: 50%; background: #67e8f9; box-shadow: 0 0 9px #22d3ee; }
.aog-orb i:nth-child(2) { inset: 7px; border-color: rgba(167,139,250,.32); animation-duration: 1.7s; animation-direction: reverse; }
.aog-orb i:nth-child(2)::before { background: #c4b5fd; box-shadow: 0 0 9px #8b5cf6; }
.aog-orb i:nth-child(3) { inset: 14px; border-color: rgba(255,105,188,.32); animation-duration: 1.15s; }
.aog-orb i:nth-child(3)::before { width: 4px; height: 4px; top: -2px; margin-left: -2px; background: #f9a8d4; box-shadow: 0 0 8px #ff69bc; }
.aog-orb b { position: absolute; inset: 18px; border-radius: 50%;
  background: radial-gradient(circle, #fff, #22d3ee 55%, #8b5cf6); animation: aogCore 1.4s ease-in-out infinite; }

.aog-think-body { min-width: 0; flex: 1; }
.aog-think-role { display: inline-block; font: 600 9.5px ui-monospace, "Fira Code", Menlo, monospace; letter-spacing: 1.1px;
  text-transform: uppercase; color: #67e8f9; background: rgba(34,211,238,.09); border: 1px solid rgba(34,211,238,.28);
  border-radius: 999px; padding: 1px 8px; margin-bottom: 4px; }
.aog-think-text { display: flex; align-items: baseline; gap: 3px; font-size: 13.5px; font-weight: 600; line-height: 1.3; }
.aog-think-text span.t { background: linear-gradient(90deg, #7dd3fc 0%, #ffffff 25%, #c4b5fd 50%, #7dd3fc 75%, #ffffff 100%);
  background-size: 220% 100%; -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
  animation: aogShimmer 2.4s linear infinite; word-break: break-word; }
.aog-dots { display: inline-flex; gap: 3px; margin-left: 3px; }
.aog-dots i { width: 4px; height: 4px; border-radius: 50%; background: #7dd3fc; animation: aogDot 1.2s ease-in-out infinite; }
.aog-dots i:nth-child(2) { animation-delay: .15s; } .aog-dots i:nth-child(3) { animation-delay: .3s; }

.aog-wave { display: flex; align-items: center; gap: 3px; height: 14px; margin-top: 7px; }
.aog-wave i { width: 3px; height: 14px; border-radius: 2px; transform-origin: center;
  background: linear-gradient(180deg, #22d3ee, #8b5cf6); animation: aogWave 1.1s ease-in-out infinite; }

.aog-think-bar { position: absolute; left: 0; right: 0; bottom: 0; height: 2px; background: rgba(56,189,248,.1); overflow: hidden; }
.aog-think-bar::after { content: ""; position: absolute; inset: 0; width: 38%;
  background: linear-gradient(90deg, transparent, #22d3ee, #ff69bc, transparent); animation: aogSweep 1.5s ease-in-out infinite; }

@media (prefers-reduced-motion: reduce) {
  .aog-think, .aog-think::before, .aog-orb i, .aog-orb b, .aog-think-text span.t, .aog-dots i, .aog-wave i,
  .aog-think-bar::after { animation: none !important; }
  .aog-think-text span.t { -webkit-text-fill-color: #bae6fd; }
}
</style>
"""


def render(text: str, role: str = "") -> str:
    """HTML satu kartu 'thinking'. Titik di akhir teks dibuang karena sudah ada titik beranimasi."""
    label = html.escape(str(text or "Council bekerja").rstrip("….. ") or "Council bekerja")
    chip = f'<div class="aog-think-role">{html.escape(str(role))}</div>' if role else ""
    bars = "".join(f'<i style="animation-delay:-{(i * 0.37) % 1.1:.2f}s"></i>' for i in range(BARS))
    return (f'<div class="aog-think"><div class="aog-orb"><i></i><i></i><i></i><b></b></div>'
            f'<div class="aog-think-body">{chip}'
            f'<div class="aog-think-text"><span class="t">{label}</span>'
            f'<span class="aog-dots"><i></i><i></i><i></i></span></div>'
            f'<div class="aog-wave">{bars}</div></div>'
            f'<div class="aog-think-bar"></div></div>')
