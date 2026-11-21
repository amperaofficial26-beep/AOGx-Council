"""Halaman BUILD AOGx (Tahap 1): dialog referensi & bentuk aplikasi, verifikasi limit,
lalu pipeline RESEARCH + ANALISIS + PRODUCT PLANNING dengan tampilan hasil bersumber.

Modul ini hanya lapisan tampilan; logika jatah ada di build/limits.py dan pipeline di
build/pipeline.py. Tidak ada pembuatan kode aplikasi di tahap ini.
"""
from datetime import datetime

import streamlit as st

import config
from agent.build_interview import DEFAULT_REFERENCES, suggest
from agent.build_research import TOPICS
from build import limits as build_limits
from build import pipeline as build_pipeline
from core.utils import clip
from ui import thinking

# Bentuk aplikasi yang ditawarkan pada langkah 2 (teks sesuai spesifikasi).
FORM_KINDS = ["Web Application", "Streamlit + GitHub", "Raw Source Code",
              "Desktop Application"]

STEP_ORDER = [("request", "Permintaan"), ("reference", "Referensi"),
              ("form", "Bentuk"), ("confirm", "Limit"),
              ("running", "Proses"), ("result", "Hasil")]

BLUEPRINT_FIELDS = [
    ("nama", "Nama aplikasi"), ("konsep", "Konsep"), ("target", "Target pengguna"),
    ("fitur_inti", "Fitur inti (versi inti)"),
    ("fitur_tambahan", "Fitur tambahan (tahap revisi)"),
    ("fitur_yang_ditingkatkan", "Fitur yang ditingkatkan"),
    ("ui_ux", "Arah UI/UX"), ("halaman", "Struktur halaman"),
    ("alur", "Alur pengguna"), ("backend", "Kebutuhan backend & database"),
    ("ai", "Integrasi AI"), ("teknologi", "Teknologi"),
]


def resolve_user_key(ss) -> str:
    """Kunci jatah: login GitHub bila tersedia, selain itu id anonim per sesi."""
    gh = ss.get("gh_oauth_user") or ss.get("gh_user")
    if isinstance(gh, dict) and str(gh.get("login") or "").strip():
        return "gh:" + str(gh["login"]).strip().lower()
    anon = ss.get("build_anon_id")
    if not anon:
        import uuid
        anon = uuid.uuid4().hex
        try:
            ss["build_anon_id"] = anon
        except Exception:
            pass
    return "anon:" + anon


def _step_indicator(current: str) -> None:
    keys = [k for k, _ in STEP_ORDER]
    # "error" dianggap bagian dari tahap proses agar indikator tidak crash.
    pos = keys.index(current) if current in keys else keys.index("running")
    parts = []
    for idx, (key, label) in enumerate(STEP_ORDER, 1):
        if idx - 1 == pos:
            parts.append(f"**{idx}. {label}**")
        elif idx - 1 < pos:
            parts.append(f":material/check_circle: {idx}. {label}")
        else:
            parts.append(f"{idx}. {label}")
    st.caption(" › ".join(parts))


def _summary_lines(ss) -> None:
    st.markdown(f"**Permintaan:** {clip(str(ss.get('build_request') or ''), 400)}")
    refs = list(ss.get("build_refs") or [])
    ref_text = ", ".join(refs) if refs else "AI yang menentukan"
    st.markdown(f"**Referensi:** {ref_text}")
    st.markdown(f"**Bentuk aplikasi:** {ss.get('build_form_kind') or '-'}")


def _step_request(router, ss) -> None:
    st.markdown("### :material/edit_note: Langkah 1 — Permintaan aplikasi")
    st.caption("Tuliskan satu perintah. AI belum membuat apa pun; setelah ini AI menanyakan "
               "aplikasi referensinya.")
    st.text_area(
        "Satu perintah aplikasi", key="build_request_input", height=140,
        placeholder="contoh: buatkan aplikasi seperti Canva, tapi lebih mudah dipakai…",
    )
    if st.button("Lanjut: pilih referensi", key="build_btn_request", type="primary",
                 icon=":material/arrow_forward:", use_container_width=True):
        request = (ss.get("build_request_input") or "").strip()
        if not request:
            st.error("Tuliskan dulu satu perintah aplikasi.")
            return
        if len(request) > config.MAX_QUESTION_CHARS:
            st.error(f"Perintah terlalu panjang (maks {config.MAX_QUESTION_CHARS} karakter).")
            return
        ss["build_request"] = request
        ss["build_error"] = None
        ss["build_result"] = None
        ss["build_log"] = []
        ss["build_attempts"] = 0
        try:
            with st.spinner("AI menyusun pilihan aplikasi referensi…"):
                out, _prov = suggest(router, request)
        except Exception:
            # Tanpa provider AI, tawarkan daftar bawaan agar dialog tetap bisa dijalani.
            out = {"references": list(DEFAULT_REFERENCES), "extra": [], "reason": "",
                   "ai_ranked": []}
        ss["build_ref_options"] = out.get("references") or list(DEFAULT_REFERENCES)
        ss["build_ref_extra"] = out.get("extra") or []
        ss["build_ai_ranked"] = out.get("ai_ranked") or []
        ss["build_ref_reason"] = out.get("reason") or ""
        ss["build_refs_pick"] = []
        ss["build_ref_custom"] = ""
        ss["build_ai_decide"] = False
        ss["build_step"] = "reference"
        st.rerun()


def _step_reference(ss) -> None:
    st.markdown("### :material/explore: Langkah 2 — Aplikasi referensi")
    st.caption(f"Permintaan: {clip(str(ss.get('build_request') or ''), 300)}")
    if ss.get("build_ref_reason"):
        st.caption(f"Saran AI: {ss['build_ref_reason']}")
    ai_decide = st.checkbox("Biarkan AI yang menentukan referensi", key="build_ai_decide",
                            help="Centang bila ingin AI memilih referensi sendiri.")
    options = list(dict.fromkeys(
        list(ss.get("build_ref_options") or []) + list(ss.get("build_ref_extra") or [])))
    if not options:
        options = list(DEFAULT_REFERENCES)
    st.multiselect(
        "Pilih aplikasi referensi (boleh menggabungkan beberapa)", options,
        key="build_refs_pick", disabled=ai_decide,
        help="Boleh pilih satu, gabungkan beberapa, atau centang pilihan AI di atas.",
    )
    st.text_input("Referensi lain di luar daftar (opsional)", key="build_ref_custom",
                  disabled=ai_decide, placeholder="Nama aplikasi lain…")
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Kembali", key="build_btn_ref_back", icon=":material/arrow_back:",
                     use_container_width=True):
            ss["build_step"] = "request"
            st.rerun()
    with col_next:
        if st.button("Lanjut: bentuk aplikasi", key="build_btn_ref_next", type="primary",
                     icon=":material/arrow_forward:", use_container_width=True):
            if ai_decide:
                ranked = list(ss.get("build_ai_ranked") or [])
                refs = ranked[:1]  # pilihan peringkat teratas AI; kosong = AI menentukan lewat riset
            else:
                refs = [str(r).strip() for r in (ss.get("build_refs_pick") or [])]
                custom = str(ss.get("build_ref_custom") or "").strip()
                if custom and custom not in refs:
                    refs.append(custom)
                if not refs:
                    st.error("Pilih minimal satu referensi, isi referensi lain, "
                             "atau centang \"Biarkan AI yang menentukan\".")
                    return
            ss["build_refs"] = refs
            ss["build_form_pick"] = ss.get("build_form_kind") or FORM_KINDS[0]
            ss["build_step"] = "form"
            st.rerun()


def _step_form(ss) -> None:
    st.markdown("### :material/widgets: Langkah 3 — Bentuk aplikasi")
    _summary_lines(ss)
    st.radio("Bentuk aplikasi yang diinginkan", FORM_KINDS, key="build_form_pick",
             help="Menentukan rancangan pengiriman hasil pada tahap berikutnya.")
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("Kembali", key="build_btn_form_back", icon=":material/arrow_back:",
                     use_container_width=True):
            ss["build_step"] = "reference"
            st.rerun()
    with col_next:
        if st.button("Lanjut: verifikasi limit", key="build_btn_form_next", type="primary",
                     icon=":material/arrow_forward:", use_container_width=True):
            ss["build_form_kind"] = ss.get("build_form_pick") or FORM_KINDS[0]
            ss["build_step"] = "confirm"
            st.rerun()


def _backend_label(backend: str) -> str:
    if backend == "supabase":
        return "Supabase"
    if backend == "memory":
        return "memori"
    return "memori (Supabase belum dikonfigurasi)"


def _step_confirm(router, ss) -> None:
    st.markdown("### :material/speed: Langkah 4 — Verifikasi limit")
    _summary_lines(ss)
    user_key = resolve_user_key(ss)
    quota = build_limits.limit_status(user_key)
    # Kalimat verifikasi wajib persis seperti spesifikasi:
    st.warning(build_limits.LIMIT_CONFIRM_TEXT)
    if quota.get("error"):
        st.info(quota["error"])
    st.caption(
        f"Terpakai {quota['used']} dari {quota['max']} BUILD · reset otomatis setelah "
        f"{build_limits.RESET_DAYS} hari · penyimpanan: {_backend_label(quota.get('backend', ''))}"
    )
    blocked = ""
    if not router.active_providers():
        blocked = ("Belum ada provider AI aktif. Isi minimal satu API key provider di "
                   "Streamlit Secrets sebelum memulai proses BUILD.")
    if blocked:
        st.error(blocked)
    elif not router.tavily.available():
        st.info("Tavily belum aktif: seluruh topik riset akan berstatus \"tidak ditemukan\".")
    if quota["remaining"] <= 0:
        reset = quota.get("reset_at") or "jadwal reset berikutnya"
        st.error(f"Jatah BUILD habis ({quota['used']}/{quota['max']}). "
                 f"Reset otomatis pada {reset}.")
    col_ok, col_back = st.columns(2)
    with col_ok:
        proceed = st.button(
            "Lanjutkan proses", key="build_btn_confirm", type="primary",
            icon=":material/play_arrow:", use_container_width=True,
            disabled=bool(blocked) or quota["remaining"] <= 0,
        )
    with col_back:
        if st.button("Kembali", key="build_btn_confirm_back", icon=":material/arrow_back:",
                     use_container_width=True):
            ss["build_step"] = "form"
            st.rerun()
    if proceed:
        result = build_limits.limit_consume(user_key)
        if not result.get("consumed"):
            reset = result.get("reset_at") or "jadwal reset berikutnya"
            st.error(f"Jatah BUILD habis ({result['used']}/{result['max']}). "
                     f"Reset otomatis pada {reset}.")
            return
        ss["build_attempts"] = 0
        ss["build_step"] = "running"
        st.rerun()


def _log_markdown(events: list) -> str:
    blocks = []
    for ev in events:
        blocks.append(f"**{ev.get('stage', '')}** · {ev.get('role', '')} · "
                      f"`{ev.get('provider', '-')}`")
        blocks.append(clip(str(ev.get("text") or ""), 900))
    return "\n\n".join(blocks) if blocks else "_Belum ada tahap selesai._"


def _step_running(router, ss) -> None:
    st.markdown("### :material/rocket_launch: Proses BUILD")
    _summary_lines(ss)
    ss["build_attempts"] = int(ss.get("build_attempts") or 0) + 1
    request = str(ss.get("build_request") or "")
    refs = list(ss.get("build_refs") or [])
    form_kind = str(ss.get("build_form_kind") or "")
    live = st.empty()
    log_ph = st.empty()
    events = []
    final = None
    error = None
    for ev in build_pipeline.run(router, request, refs, form_kind):
        if ev["kind"] == "status":
            live.markdown(thinking.render(ev["text"]), unsafe_allow_html=True)
        elif ev["kind"] == "agent":
            events.append(ev)
            live.markdown(
                thinking.render(f"{ev['stage']} selesai · {ev['role']} · {ev['provider']}"),
                unsafe_allow_html=True)
            log_ph.markdown(_log_markdown(events))
        elif ev["kind"] == "final":
            final = ev
        elif ev["kind"] == "error":
            error = ev["text"]
    live.empty()
    if final:
        final["request"] = request
        ss["build_result"] = final
        ss["build_log"] = events
        ss["build_error"] = None
        ss["build_finished_at"] = datetime.now().strftime("%d %b %Y %H:%M")
        ss["build_step"] = "result"
        st.rerun()
    ss["build_error"] = error or "Pipeline berhenti tanpa hasil."
    ss["build_step"] = "error"
    st.rerun()


def _step_error(ss) -> None:
    st.markdown("### :material/error: Proses BUILD terhenti")
    _summary_lines(ss)
    st.error(str(ss.get("build_error") or "Pipeline berhenti tanpa hasil."))
    st.caption(f"Percobaan: {int(ss.get('build_attempts') or 0)}/"
               f"{config.BUILD_MAX_REPAIR_ATTEMPTS} · jatah sudah terpakai pada "
               "langkah verifikasi limit.")
    attempts = int(ss.get("build_attempts") or 0)
    col_retry, col_edit = st.columns(2)
    with col_retry:
        if st.button("Coba lagi", key="build_btn_retry", icon=":material/restart_alt:",
                     use_container_width=True,
                     disabled=attempts >= config.BUILD_MAX_REPAIR_ATTEMPTS):
            ss["build_step"] = "running"
            st.rerun()
    with col_edit:
        if st.button("Ubah permintaan", key="build_btn_edit", icon=":material/edit:",
                     use_container_width=True):
            ss["build_step"] = "request"
            st.rerun()


def _render_research(research: dict, sources: list) -> None:
    claims = {}
    for c in (research.get("claims") or []):
        claims.setdefault(c.get("topic"), []).append(c)
    if not claims and not sources:
        st.info("Tidak ada sumber yang ditemukan; seluruh topik berstatus tidak ditemukan.")
    for key, desc in TOPICS:
        st.markdown(f"**{desc.capitalize()}**")
        items = claims.get(key) or []
        if not items:
            st.markdown("- tidak ditemukan")
            continue
        for item in items:
            url = item.get("source") or ""
            claim = clip(str(item.get("claim") or ""), 400)
            st.markdown(f"- {claim} — [sumber]({url})" if url else f"- {claim}")


def _render_blueprint(blueprint: dict) -> None:
    if not blueprint.get("nama"):
        st.caption("(nama aplikasi belum tersusun)")
    for key, label in BLUEPRINT_FIELDS:
        value = blueprint.get(key)
        if isinstance(value, list):
            if not value:
                continue
            st.markdown(f"**{label}**")
            for item in value:
                st.markdown(f"- {item}")
        elif value:
            st.markdown(f"**{label}**")
            st.markdown(str(value))


def _step_result(ss) -> None:
    res = ss.get("build_result") or {}
    blueprint = res.get("blueprint") or {}
    st.markdown("### :material/task: Langkah 6 — Hasil BUILD (Tahap 1)")
    st.success(f"Blueprint siap: **{blueprint.get('nama') or '(nama belum tersusun)'}**")
    _summary_lines(ss)
    st.caption(
        f"Selesai: {ss.get('build_finished_at') or '-'} · provider: "
        f"{', '.join(res.get('providers') or []) or '-'} · "
        f"sumber unik: {len(res.get('sources') or [])}"
    )
    if st.button("BUILD baru", key="build_btn_new", icon=":material/add_task:",
                 use_container_width=False):
        # Reset state BUILD (bukan key widget yang sedang aktif, kecuali id anonim jatah).
        for key in ("build_step", "build_request", "build_request_input",
                    "build_ref_options", "build_ref_extra", "build_ref_reason",
                    "build_ai_ranked", "build_refs_pick", "build_ref_custom",
                    "build_ai_decide", "build_refs", "build_form_pick",
                    "build_form_kind", "build_result", "build_log", "build_error",
                    "build_attempts", "build_finished_at"):
            ss.pop(key, None)
        ss["build_step"] = "request"
        st.rerun()
    tab_ringkasan, tab_riset, tab_analisis, tab_blueprint, tab_sumber = st.tabs(
        ["Ringkasan", "Riset", "Analisis", "Blueprint", "Sumber"])
    with tab_ringkasan:
        st.markdown(f"**Permintaan:** {clip(str(res.get('request') or ss.get('build_request') or ''), 800)}")
        refs = res.get("references") or ss.get("build_refs") or []
        st.markdown(f"**Referensi:** {', '.join(refs) if refs else 'AI yang menentukan'}")
        st.markdown(f"**Bentuk aplikasi:** {res.get('form_kind') or ss.get('build_form_kind') or '-'}")
        st.markdown(f"**Provider:** {', '.join(res.get('providers') or []) or '-'}")
        st.markdown("**Langkah berikutnya (Tahap 2+):** pembuatan kode aplikasi oleh agen "
                    "builder, pemeriksaan statis, testing, dan preview — belum aktif di tahap ini.")
    with tab_riset:
        _render_research(res.get("research") or {}, res.get("sources") or [])
    with tab_analisis:
        st.markdown(str(res.get("analysis") or "(analisis tidak tersedia)"))
    with tab_blueprint:
        _render_blueprint(blueprint)
    with tab_sumber:
        sources = res.get("sources") or []
        if not sources:
            st.caption("Tidak ditemukan sumber web.")
        for i, source in enumerate(sources, 1):
            url = source.get("url") or ""
            st.markdown(f"{i}. [{source.get('title') or url}]({url})")


def render_build_page(router, ss=None) -> None:
    """Titik masuk halaman BUILD dari app.py."""
    ss = ss if ss is not None else st.session_state
    ss.setdefault("build_step", "request")
    st.markdown(":material/build: **AOGx Build**")
    st.caption("Beri satu perintah, tim agen meneliti aplikasi referensi, menganalisis "
               "kekurangannya, lalu menyusun blueprint aplikasi alternatif. Tahap ini belum "
               "membuat kode aplikasi.")
    _step_indicator(str(ss.get("build_step") or "request"))
    step = str(ss.get("build_step") or "request")
    if step == "request":
        _step_request(router, ss)
    elif step == "reference":
        _step_reference(ss)
    elif step == "form":
        _step_form(ss)
    elif step == "confirm":
        _step_confirm(router, ss)
    elif step == "running":
        _step_running(router, ss)
    elif step == "error":
        _step_error(ss)
    elif step == "result":
        _step_result(ss)
    else:
        ss["build_step"] = "request"
        st.rerun()
