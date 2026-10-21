"""AOGx-Council: diskusi multi-agen AI dengan orchestrator dan penyaringan jawaban berlapis.

Tata letak: kolom kiri untuk chat, kanvas kanan menampilkan proses agen secara langsung.
"""
import hmac

import streamlit as st

import config
from core import pipeline
from core.router import Router
from core.utils import clip
from providers.base import ProviderError
from ui import theme
from ui.flow import CouncilFlow

st.set_page_config(page_title="AOGx Council", page_icon="🦊", layout="wide")

st.markdown(theme.CSS, unsafe_allow_html=True)
st.markdown("""
<style>
.block-container { padding-top: 1.1rem; padding-bottom: 1.2rem; max-width: 1500px; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
html, body, [class*="css"] { font-family: "Inter", ui-sans-serif, system-ui, -apple-system, sans-serif; }
.aog-title { font-size: 1.9rem; font-weight: 800; letter-spacing: .5px; line-height: 1.15;
  background: linear-gradient(90deg, #e5e7eb, #94a3b8 60%, #cbd5e1);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.aog-sub { color: #94a3b8; margin-top: -0.35rem; }
[data-testid="stChatMessage"] { background: #0d1523; border: 1px solid #1a2740;
  border-radius: 14px; padding: .7rem .85rem; margin-bottom: .5rem; }
[data-testid="stSidebar"] { background: #0a111d; border-right: 1px solid #17233a; }
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
        lines.append(f"{who}: {clip(m['content'], 600)}")
    return "\n".join(lines)


def render_answer(msg: dict, idx: int):
    st.markdown(msg["content"])
    meta = msg.get("meta", {})
    bits = []
    if meta.get("score") is not None:
        bits.append(f"Keyakinan verifier: **{meta['score']:.0%}**")
    elif meta.get("verified") is False:
        bits.append("Belum diverifikasi")
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
    if meta.get("flow"):
        if st.button("🧠 Tampilkan proses ini di kanvas", key=f"flow_{idx}"):
            ss.flow = CouncilFlow.restore(meta["flow"], msg.get("question", ""))
            st.rerun()
    st.download_button("Unduh jawaban (.md)", msg["content"],
                       file_name="jawaban-aogx.md", key=f"dl_{idx}")


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### Pengaturan")
    mode = st.radio("Kedalaman", list(config.MODES), index=1,
                    help="Cepat: 1 putaran tanpa verifikasi. Seimbang: 2 putaran + verifikasi. "
                         "Mendalam: 3 putaran + verifikasi ketat (lebih banyak pemakaian kuota).")
    demo = st.toggle("Mode demo (tanpa API key)", value=ss.demo,
                     help="Semua agen dijawab dengan teks siap pakai supaya kanvas proses tetap bisa "
                          "dilihat. Matikan untuk memakai provider asli.")
    ss.demo = demo
    active = [] if demo else router.active_providers()
    st.markdown("### Status provider")
    if demo:
        st.markdown("🟢 demo (tidak memanggil API)")
    else:
        for name in list(config.OPENAI_COMPAT) + ["gemini"]:
            st.markdown(("🟢 " if name in active else "⚪ ") + name)
        st.markdown(("🟢 " if router.tavily.available() else "⚪ ") + "tavily (web search)")
    if router.stats and not demo:
        with st.expander("Statistik panggilan"):
            for n, s in router.stats.items():
                st.write(f"{n}: {s['ok']} berhasil, {s['fail']} gagal")
    if not demo and st.button("Tes koneksi provider"):
        with st.spinner("Menguji tiap provider…"):
            ss.diag = router.diagnose()
    if ss.get("diag") and not demo:
        for name, ok, msg in ss.diag:
            st.markdown(f"{'✅' if ok else ('⚪' if ok is None else '❌')} **{name}**")
            st.caption(msg)
    if not demo:
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
        ss.pop("flow", None)
        st.rerun()
    if c2.button("Muat ulang key"):
        get_router.clear()
        st.rerun()
    st.caption(f"Permintaan sesi ini: {ss.n_requests}/{config.MAX_REQUESTS_PER_SESSION}"
               + (" · mode demo" if demo else ""))

# ---------- Kepala halaman ----------
st.markdown('<div class="aog-title">AOGx Council</div>', unsafe_allow_html=True)
st.markdown('<div class="aog-sub">Beberapa AI berdiskusi, saling mengoreksi, lalu jawabannya '
            'disaring berlapis — prosesnya tampil langsung di kanvas sebelah kanan.</div>',
            unsafe_allow_html=True)

left, right = st.columns([0.40, 0.60], gap="medium")

# ---------- Kanan: kanvas proses ----------
flow = ss.get("flow")
if flow is None:
    cfg = config.MODES[mode]
    flow = CouncilFlow(mode_name=mode, rounds=cfg["rounds"], verify=cfg["verify"],
                       max_retries=cfg["max_retries"])
    flow.preview()
ss.flow = flow

with right:
    st.markdown('<div class="aog-colhead">⚙️ Proses council — langsung</div>',
                unsafe_allow_html=True)
    ph_chips = st.empty()
    ph_graph = st.empty()
    st.markdown('<div class="aog-colhead" style="margin-top:10px">🧾 Jejak langkah</div>',
                unsafe_allow_html=True)
    ph_log = st.empty()


def draw(redraw_log: bool = True):
    ph_chips.markdown(theme.panel(flow.render_chips() + theme.LEGEND), unsafe_allow_html=True)
    ph_graph.markdown(theme.stage(flow.render()), unsafe_allow_html=True)
    if redraw_log:
        ph_log.markdown(theme.panel(flow.render_log()), unsafe_allow_html=True)


draw()

# ---------- Kiri: chat ----------
with left:
    st.markdown('<div class="aog-colhead">💬 Chat</div>', unsafe_allow_html=True)
    chat_box = st.container(height=560, border=False)
    question = st.chat_input("Tanyakan sesuatu ke AOGx Council…")

with chat_box:
    if not ss.messages:
        st.markdown('<div class="aog-warn">Belum ada pertanyaan. Kirim satu pertanyaan, lalu '
                    'perhatikan kanvas di kanan: node menyala biru saat agen bekerja, hijau saat '
                    'selesai, dan abu-abu saat tahapannya dilewati.</div>',
                    unsafe_allow_html=True)
    for i, m in enumerate(ss.messages):
        with st.chat_message(m["role"]):
            if m["role"] == "user":
                st.markdown(m["content"])
            else:
                render_answer(m, i)
    ph_live = st.empty()

if question:
    question = question.strip()
    usable = demo or bool(active)
    if len(question) > config.MAX_QUESTION_CHARS:
        st.error(f"Pertanyaan terlalu panjang (maks {config.MAX_QUESTION_CHARS} karakter).")
    elif ss.n_requests >= config.MAX_REQUESTS_PER_SESSION:
        st.error("Batas permintaan sesi ini tercapai. Klik \"Chat baru\" atau muat ulang halaman.")
    elif not usable:
        st.error("Belum ada provider aktif. Isi API key di `.env` atau Streamlit secrets "
                 "(lihat `env.example`), atau nyalakan mode demo di sidebar.")
    else:
        history = history_text(ss.messages)
        ss.messages.append({"role": "user", "content": question})
        ss.n_requests += 1
        cfg = config.MODES[mode]
        flow = CouncilFlow(question=question, mode_name=mode, rounds=cfg["rounds"],
                           verify=cfg["verify"], max_retries=cfg["max_retries"])
        ss.flow = flow
        draw()

        run_router = router
        if demo:
            from ui.demo import DemoRouter
            run_router = DemoRouter()

        with chat_box:
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                ph_live.markdown(f'<div class="aog-live"><b>●</b>'
                                 f'<span>{flow.stage_text or "Council mulai bekerja…"}</span></div>',
                                 unsafe_allow_html=True)

        log, final, error = [], None, None
        for ev in pipeline.run(run_router, question, mode, history):
            action = flow.consume(ev)
            if ev["kind"] == "agent":
                log.append({"role": ev["role"], "provider": ev["provider"],
                            "stage": ev["stage"], "text": ev["text"]})
                ph_live.markdown(f'<div class="aog-live"><b>●</b><span>{ev["role"]} — '
                                 f'{ev["stage"]}</span></div>', unsafe_allow_html=True)
            elif ev["kind"] == "status":
                ph_live.markdown(f'<div class="aog-live"><b>●</b><span>{ev["text"]}</span></div>',
                                 unsafe_allow_html=True)
            elif ev["kind"] == "final":
                final = ev
            elif ev["kind"] == "error":
                error = ev["text"]
            draw(redraw_log=(action in ("log", "error", "final")))

        ph_live.empty()
        with chat_box:
            with st.chat_message("assistant"):
                if final:
                    msg = {"role": "assistant", "content": final["answer"], "question": question,
                           "meta": {"score": final["score"], "issues": final["issues"],
                                    "verified": final["verified"], "sources": final["sources"],
                                    "providers": final["providers"], "log": log,
                                    "flow": flow.snapshot()}}
                    ss.messages.append(msg)
                    render_answer(msg, len(ss.messages) - 1)
                else:
                    st.error(error or "Pipeline berhenti tanpa hasil.")
                    if getattr(run_router, "last_error", None):
                        with st.expander("Detail error provider"):
                            for n, e in run_router.last_error.items():
                                st.text(f"{n}: {e}")
                    ss.messages.pop()
                    ss.n_requests -= 1
        draw()
