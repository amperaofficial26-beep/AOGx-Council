"""AOGx-Council: diskusi multi-agen AI dengan orchestrator dan penyaringan jawaban berlapis."""
import hmac

import streamlit as st

import config
from core import pipeline
from core.router import Router
from providers.base import ProviderError
from core.utils import clip

st.set_page_config(page_title="AOGx Council", page_icon="🦊", layout="wide")

st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.aog-title {font-size: 2rem; font-weight: 800; letter-spacing: .5px;
  background: linear-gradient(90deg, #e5e7eb, #94a3b8 60%, #cbd5e1);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
.aog-sub {color: #94a3b8; margin-top: -0.4rem; margin-bottom: 1rem;}
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


def history_text(messages, pairs: int = 3) -> str:
    lines = []
    for m in messages[-pairs * 2:]:
        who = "Pengguna" if m["role"] == "user" else "Asisten"
        lines.append(f"{who}: {clip(m['content'], 600)}")
    return "\n".join(lines)


def render_answer(msg: dict, idx: int):
    st.markdown(msg["content"])
    meta = msg.get("meta", {})
    bits = []
    if meta.get("score") is not None:
        bits.append(f"Keyakinan verifier: **{meta['score']:.0%}**")
    if meta.get("providers"):
        bits.append("Provider: " + ", ".join(meta["providers"]))
    if bits:
        st.caption(" · ".join(bits))
    if meta.get("issues"):
        st.caption("Catatan verifier: " + "; ".join(meta["issues"]))
    if meta.get("sources"):
        with st.expander(f"Sumber web ({len(meta['sources'])})"):
            for i, s in enumerate(meta["sources"], 1):
                st.markdown(f"{i}. [{s['title'] or s['url']}]({s['url']})")
    if meta.get("log"):
        with st.expander(f"Lihat proses diskusi ({len(meta['log'])} langkah)"):
            for ev in meta["log"]:
                st.markdown(f"**{ev['role']}** · `{ev['provider']}` · {ev['stage']}")
                st.text(ev["text"])
    st.download_button("Unduh jawaban (.md)", msg["content"],
                       file_name="jawaban-aogx.md", key=f"dl_{idx}")


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### Pengaturan")
    mode = st.radio("Kedalaman", list(config.MODES), index=1,
                    help="Cepat: 1 putaran tanpa verifikasi. Seimbang: 2 putaran + verifikasi. "
                         "Mendalam: 3 putaran + verifikasi ketat (lebih banyak pemakaian kuota).")
    active = router.active_providers()
    st.markdown("### Status provider")
    for name in list(config.OPENAI_COMPAT) + ["gemini"]:
        st.markdown(("🟢 " if name in active else "⚪ ") + name)
    st.markdown(("🟢 " if router.tavily.available() else "⚪ ") + "tavily (web search)")
    if router.stats:
        with st.expander("Statistik panggilan"):
            for n, s in router.stats.items():
                st.write(f"{n}: {s['ok']} berhasil, {s['fail']} gagal")
    if st.button("Tes koneksi provider"):
        with st.spinner("Menguji tiap provider…"):
            ss.diag = router.diagnose()
    if ss.get("diag"):
        for name, ok, msg in ss.diag:
            st.markdown(f"{'✅' if ok else ('⚪' if ok is None else '❌')} **{name}**")
            st.caption(msg)
    with st.expander("Cari ID model"):
        keyed = [n for n, p in router.providers.items() if p.available()]
        if keyed:
            prov = st.selectbox("Provider", keyed)
            flt = st.text_input("Filter (mis. free, llama, gpt, flash)")
            if st.button("Ambil daftar model"):
                try:
                    ss.models = (prov, router.list_models(prov))
                except ProviderError as e:
                    ss.models = (prov, [f"ERROR: {e}"])
            if ss.get("models"):
                mp, ids = ss.models
                shown = [i for i in ids if flt.lower() in i.lower()][:60]
                st.caption(f"{mp}: {len(ids)} model, tampil {len(shown)}")
                st.code("\n".join(shown) or "(tidak ada yang cocok)")
        else:
            st.caption("Isi minimal satu API key dulu.")
    c1, c2 = st.columns(2)
    if c1.button("Chat baru"):
        ss.messages = []
        ss.n_requests = 0
        ss.diag = None
        st.rerun()
    if c2.button("Muat ulang key"):
        get_router.clear()
        st.rerun()
    st.caption(f"Permintaan sesi ini: {ss.n_requests}/{config.MAX_REQUESTS_PER_SESSION}")

# ---------- Halaman utama ----------
st.markdown('<div class="aog-title">AOGx Council</div>', unsafe_allow_html=True)
st.markdown('<div class="aog-sub">Beberapa AI berdiskusi, saling mengoreksi, lalu jawabannya disaring berlapis.</div>',
            unsafe_allow_html=True)

if not router.active_providers():
    st.warning("Belum ada provider aktif. Isi API key di `.env` atau Streamlit secrets (lihat `.env.example`), "
               "lalu klik \"Muat ulang key\".")

for i, m in enumerate(ss.messages):
    with st.chat_message(m["role"]):
        if m["role"] == "user":
            st.markdown(m["content"])
        else:
            render_answer(m, i)

question = st.chat_input("Tanyakan sesuatu ke AOGx Council…")
if question:
    question = question.strip()
    if len(question) > config.MAX_QUESTION_CHARS:
        st.error(f"Pertanyaan terlalu panjang (maks {config.MAX_QUESTION_CHARS} karakter).")
    elif ss.n_requests >= config.MAX_REQUESTS_PER_SESSION:
        st.error("Batas permintaan sesi ini tercapai. Klik \"Chat baru\" atau muat ulang halaman.")
    elif not router.active_providers():
        st.error("Belum ada provider aktif.")
    else:
        history = history_text(ss.messages)
        ss.messages.append({"role": "user", "content": question})
        ss.n_requests += 1
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            status = st.status("Council mulai bekerja…", expanded=True)
            log, final, error = [], None, None
            for ev in pipeline.run(router, question, mode, history):
                if ev["kind"] == "status":
                    status.update(label=ev["text"])
                elif ev["kind"] == "agent":
                    log.append(ev)
                    status.markdown(f"**{ev['role']}** · `{ev['provider']}` · {ev['stage']}")
                    status.caption(clip(ev["text"], 280))
                elif ev["kind"] == "final":
                    final = ev
                elif ev["kind"] == "error":
                    error = ev["text"]

            if final:
                status.update(label="Selesai", state="complete", expanded=False)
                msg = {"role": "assistant", "content": final["answer"],
                       "meta": {"score": final["score"], "issues": final["issues"],
                                "sources": final["sources"], "providers": final["providers"],
                                "log": log}}
                ss.messages.append(msg)
                render_answer(msg, len(ss.messages) - 1)
            else:
                status.update(label="Gagal", state="error", expanded=False)
                st.error(error or "Pipeline berhenti tanpa hasil.")
                if router.last_error:
                    with st.expander("Detail error provider"):
                        for n, e in router.last_error.items():
                            st.text(f"{n}: {e}")
                ss.messages.pop()  # buang pertanyaan yang gagal supaya riwayat tetap bersih
                ss.n_requests -= 1
