"""AOGx-Council: diskusi multi-agen AI dengan orchestrator dan penyaringan jawaban berlapis.

Tata letak: 2/4 kiri khusus chat (permanen, tanpa sidebar), 2/4 kanan "mesin" proses agen.
Di kolom kanan: Mesin Council selebar penuh, lalu di bawahnya "Jejak langkah" dan
"Alur Council" berdampingan.

Integrasi tambahan:
- Video Studio: pratinjau video MP4 sebelum diunggah ke YouTube Shorts.
- Callback OAuth YouTube dipisahkan dari callback OAuth GitHub.
- Pembuatan video di Dola tetap manual sampai tersedia API resmi yang dapat digunakan.
"""
import difflib
import hmac
import re
import time
from urllib.parse import urlencode

import streamlit as st

import config
from core import pipeline
from core.router import Router
from core.utils import clip, extract_json
from providers.github import (
    GitHubClient, GitHubError, make_oauth_state, verify_oauth_state, exchange_oauth_code,
)
from ui import autonomous_creator, machine, neural, theme, thinking, video_studio
from ui.flow import CouncilFlow

st.set_page_config(page_title="AOGx Council", page_icon=":material/hub:", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown(theme.CSS, unsafe_allow_html=True)
st.markdown(machine.CSS, unsafe_allow_html=True)
st.markdown(thinking.CSS, unsafe_allow_html=True)
st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 1840px; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] { display: none !important; }
html, body, [class*="css"] { font-family: "Inter", ui-sans-serif, system-ui, -apple-system, sans-serif; }
.aog-title { font-size: 1.5rem; font-weight: 800; letter-spacing: .5px; line-height: 1.15;
  background: linear-gradient(90deg, #e5e7eb, #94a3b8 60%, #cbd5e1);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
[data-testid="stChatMessage"] { background:#0d1523; border:1px solid #1a2740;
  border-radius:18px; padding:.6rem .7rem; margin-bottom:.6rem; }
[data-testid="stChatMessage"]:has(.aog-user-marker) {
  width:fit-content !important; max-width:86% !important; align-self:flex-end !important;
  margin-left:auto !important; margin-right:0 !important; flex-direction:row-reverse;
  background:#12483d !important; border-color:#216d59 !important;
  border-radius:18px 18px 5px 18px !important;
}
[data-testid="stChatMessage"]:has(.aog-assistant-marker) {
  width:fit-content !important; max-width:96% !important; align-self:flex-start !important;
  margin-right:auto !important; background:#0d1523 !important;
  border-radius:18px 18px 18px 5px !important;
}
.aog-user-marker, .aog-assistant-marker { display:none !important; }
/* Jejak langkah dan Alur Council dibuat lebih rapat ke Mesin Council. */
.aog-log { max-height: 580px; }
.st-key-council-lower-panels { margin-top: -44px !important; position: relative; z-index: 2; }
</style>
""", unsafe_allow_html=True)


# ---------- Gerbang kode akses (opsional) ----------
access_code = config.get_secret("APP_ACCESS_CODE")
if access_code and not st.session_state.get("auth"):
    st.markdown('<div class="aog-title">AOGx Council</div>', unsafe_allow_html=True)
    entered = st.text_input("Kode akses", type="password")
    if entered:
        if hmac.compare_digest(entered.encode(), access_code.encode()):
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Kode akses salah.")
    st.stop()


@st.cache_resource
def get_router() -> Router:
    return Router()


router = get_router()
ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("n_requests", 0)
ss.setdefault("demo", not bool(router.active_providers()))


def history_text(messages, pairs: int = 3) -> str:
    lines = []
    for m in messages[-pairs * 2:]:
        who = "Pengguna" if m["role"] == "user" else "Asisten"
