"""Halaman BUILD AOGx (Tahap 1): dialog referensi & bentuk aplikasi, verifikasi limit,
lalu pipeline RESEARCH + ANALISIS + PRODUCT PLANNING dengan tampilan hasil bersumber.

Modul ini hanya lapisan tampilan; logika jatah ada di build/limits.py dan pipeline di
build/pipeline.py. Tidak ada pembuatan kode aplikasi di tahap ini.
"""
from datetime import datetime
from html import escape as html_escape

import streamlit as st

import config
from agent.build_interview import DEFAULT_REFERENCES, suggest
from agent.build_research import TOPICS
from build import limits as build_limits
from build import pipeline as build_pipeline
from core.utils import clip
from ui import thinking
from ui.build_style import CABLES, CSS as BUILD_CSS

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


def _step_pos(current: str) -> int:
    """Posisi langkah saat ini; "error" dianggap bagian tahap proses."""
    keys = [k for k, _ in STEP_ORDER]
    return keys.index(current) if current in keys else keys.index("running")


def _steps_html(current: str) -> str:
    """Kolom panel tahap (gaya kartu kecil referensi): muncul progresif — panel
    langkah ke-N baru tampil setelah langkah sebelumnya selesai; aktif = emas."""
    pos = _step_pos(current)
    cards = []
    for idx, (_key, label) in enumerate(STEP_ORDER):
        if idx > pos:
            break
        state = "is-current" if idx == pos else "is-done"
        badge = "aktif" if idx == pos else "selesai"
        cards.append(
            f'<div class="bld-stepcard {state}">'
            '<span class="bld-step-dot"></span>'
            '<span class="bld-step-body">'
            f'<span class="bld-step-num">{idx + 1}</span>'
            f'<span class="bld-step-label">{html_escape(label)}</span>'
            "</span>"
            f'<span class="bld-step-state">{badge}</span>'
            "</div>"
        )
    return ('<div class="bld-zone-kicker">Tahapan</div>'
            '<div class="bld-steps"><span class="bld-spine"></span>'
            + "".join(cards) + "</div>")


def _render_header(ss) -> None:
    """Kepala halaman: wordmark + pil permintaan (kanan atas, gaya referensi)."""
    request = clip(str(ss.get("build_request") or ""), 90)
    pill = request or "Belum ada permintaan"
    st.markdown(
        '<div class="bld-head">'
        '<div class="bld-wordmark">'
        "<strong>AOGx <em>Build</em></strong>"
        "<small>Tahap 1 · Perancang blueprint</small>"
        "</div>"
        f'<span class="bld-pill" title="{html_escape(pill)}">{html_escape(pill)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def _render_core(ss, quota: dict) -> None:
    """Zona inti paling kiri: orb + nama proyek + chip jatah (gaya orb referensi)."""
    name = clip(str(ss.get("build_request") or ""), 90) or "Belum ada permintaan"
    remaining = int(quota.get("remaining") or 0)
    maximum = int(quota.get("max") or 0)
    sisa_cls = "bld-chip" if remaining > 0 else "bld-chip is-warn"
    st.markdown(
        '<div class="bld-zone-kicker">Inti proyek</div>'
        '<div class="bld-core">'
        '<span class="bld-orb"></span>'
        f'<div class="bld-core-name">{html_escape(name)}</div>'
        '<div class="bld-core-badges">'
        f'<span class="{sisa_cls}">Sisa {remaining}/{maximum}</span>'
        '<span class="bld-chip is-gold">Tahap 1</span>'
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_identity(ss, step: str, quota: dict) -> None:
    """Panel paling kanan: identitas aplikasi + statistik + berkas/sumber."""
    pos = _step_pos(step)
    label = STEP_ORDER[pos][1]
    used = int(quota.get("used") or 0)
    maximum = int(quota.get("max") or 0)
    remaining = int(quota.get("remaining") or 0)
    reset = str(quota.get("reset_at") or "-")
    res = ss.get("build_result") or {}
    blueprint = res.get("blueprint") or {}
    refs = list(ss.get("build_refs") or []) or list(ss.get("build_refs_pick") or [])
    form_kind = str(ss.get("build_form_kind") or res.get("form_kind") or "")
    request = clip(str(ss.get("build_request") or res.get("request") or ""), 260)
    ref_text = ", ".join(str(r) for r in refs) if refs else "AI yang menentukan"
    sources = list(res.get("sources") or [])
    attempts = int(ss.get("build_attempts") or 0)
    quota_badge = "Aman" if remaining > 0 else "Habis"
    quota_cls = "" if remaining > 0 else " is-warn"
    # Judul = identitas aplikasi: nama blueprint bila sudah ada, selain itu permintaan.
    title = (str(blueprint.get("nama") or "").strip()
             or clip(str(ss.get("build_request") or res.get("request") or ""), 80)
             or "Belum ada permintaan")
    if step == "result":
        meta = f"Selesai {html_escape(str(ss.get('build_finished_at') or '-'))}"
        head_badge = "Siap"
        head_cls = "bld-badge"
    else:
        meta = f"Reset jatah {html_escape(reset)}"
        head_badge = f"Langkah {pos + 1}/{len(STEP_ORDER)}"
        head_cls = "bld-badge is-soft"
    if sources:
        file_rows = "".join(
            f'<a class="bld-file" href="{html_escape(str(s.get("url") or ""))}" '
            'target="_blank" rel="noopener">'
            '<span class="bld-file-ico"></span>'
            f'<span class="bld-file-name">{html_escape(clip(str(s.get("title") or s.get("url") or ""), 60))}</span>'
            "</a>"
            for s in sources if s.get("url")
        ) or None
    else:
        file_rows = None
    files_html = (
        f'<div class="bld-files">{file_rows}</div>' if file_rows else
        '<div class="bld-files-empty">Berkas &amp; sumber muncul setelah proses '
        "BUILD selesai.</div>"
    )
    st.markdown(
        '<div class="bld-panel">'
        '<div class="bld-kicker">Identitas aplikasi</div>'
        f'<div class="bld-title">{html_escape(title)}</div>'
        '<div class="bld-status">'
        f'<span class="{head_cls}">{head_badge}</span>'
        f'<span class="bld-meta">{meta}</span>'
        "</div>"
        '<div class="bld-subcard">'
        '<div class="bld-subcard-head"><span>Status jatah</span>'
        f'<span class="bld-badge{quota_cls}">{quota_badge}</span></div>'
        f'<div class="bld-big">{remaining}</div>'
        f'<div class="bld-sub">terpakai {used} dari {maximum} BUILD · '
        f"penyimpanan: {html_escape(_backend_label(quota.get('backend', '')))}</div>"
        "</div>"
        '<div class="bld-stats">'
        f'<div class="bld-stat"><div class="bld-stat-num">{used}</div>'
        '<div class="bld-stat-label">BUILD terpakai</div></div>'
        f'<div class="bld-stat"><div class="bld-stat-num">{len(refs)}</div>'
        '<div class="bld-stat-label">Referensi dipilih</div></div>'
        f'<div class="bld-stat"><div class="bld-stat-num">{attempts}/'
        f"{config.BUILD_MAX_REPAIR_ATTEMPTS}</div>"
        '<div class="bld-stat-label">Percobaan proses</div></div>'
        f'<div class="bld-stat"><div class="bld-stat-num">{len(sources)}</div>'
        '<div class="bld-stat-label">Sumber unik</div></div>'
        "</div>"
        '<div class="bld-sec-head">Ringkasan</div>'
        '<div class="bld-note">'
        '<div class="bld-row"><span>Permintaan</span>'
        f"<p>{html_escape(request) or 'Belum ada permintaan.'}</p></div>"
        '<div class="bld-row"><span>Referensi</span>'
        f"<p>{html_escape(ref_text)}</p></div>"
        '<div class="bld-row"><span>Bentuk aplikasi</span>'
        f"<p>{html_escape(form_kind) or '-'}</p></div>"
        "</div>"
        '<div class="bld-sec-head">Berkas &amp; sumber</div>'
        f"{files_html}"
        "</div>",
        unsafe_allow_html=True,
    )


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


def _log_html(events: list, live_text: str = "") -> str:
    """Panel proses AI kumulatif: satu panel per tahap yang sudah selesai."""
    panels = []
    if live_text:
        panels.append(
            '<div class="bld-proc is-live"><span class="bld-proc-dot"></span>'
            '<div class="bld-proc-body"><div class="bld-proc-head">'
            '<span class="bld-proc-stage">Sedang berjalan</span></div>'
            f'<div class="bld-proc-text">{html_escape(clip(str(live_text), 180))}</div>'
            "</div></div>"
        )
    for ev in events:
        stage = str(ev.get("stage") or "").strip() or "Tahap"
        role = str(ev.get("role") or "").strip()
        provider = str(ev.get("provider") or "-")
        role_line = " · ".join(x for x in (role, provider) if x and x != "-") or provider
        text = clip(str(ev.get("text") or ""), 200)
        panels.append(
            '<div class="bld-proc"><span class="bld-proc-dot"></span>'
            '<div class="bld-proc-body"><div class="bld-proc-head">'
            f'<span class="bld-proc-stage">{html_escape(stage)}</span>'
            f'<span class="bld-proc-role">{html_escape(role_line)}</span></div>'
            f'<div class="bld-proc-text">{html_escape(text)}</div>'
            "</div></div>"
        )
    if not panels:
        return ""
    return '<div class="bld-procs">' + "".join(panels) + "</div>"


def _step_running(router, ss) -> None:
    st.markdown("### :material/rocket_launch: Proses BUILD")
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
            log_ph.markdown(_log_html(events), unsafe_allow_html=True)
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
    st.caption(
        f"Selesai: {ss.get('build_finished_at') or '-'} · provider: "
        f"{', '.join(res.get('providers') or []) or '-'} · "
        f"sumber unik: {len(res.get('sources') or [])}"
    )
    # Panel proses AI kumulatif (satu panel per tahap yang sudah selesai).
    log_events = list(ss.get("build_log") or [])
    if log_events:
        st.markdown(_log_html(log_events), unsafe_allow_html=True)
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
    """Titik masuk mode BUILD (dalam AOGx Agent Code) dari app.py.

    Tata letak mengikuti referensi: alur kiri-kanan — inti (orb) → panel tahap
    (muncul progresif) → zona kerja (form / panel proses AI kumulatif) → panel
    identitas & berkas di paling kanan. Kabel penghubung = lapisan SVG dekoratif.
    """
    ss = ss if ss is not None else st.session_state
    ss.setdefault("build_step", "request")
    st.markdown(BUILD_CSS, unsafe_allow_html=True)
    step = str(ss.get("build_step") or "request")
    try:
        quota = build_limits.limit_status(resolve_user_key(ss))
    except Exception:
        quota = {"used": 0, "max": 0, "remaining": 0, "backend": "",
                 "reset_at": "", "error": ""}
    with st.container(key="build-page"):
        _render_header(ss)
        st.caption("Beri satu perintah, tim agen meneliti aplikasi referensi, menganalisis "
                   "kekurangannya, lalu menyusun blueprint aplikasi alternatif. Tahap ini belum "
                   "membuat kode aplikasi.")
        with st.container(key="build-graph"):
            st.markdown(CABLES, unsafe_allow_html=True)
            core_col, steps_col, work_col, ident_col = st.columns(
                [1.6, 2.2, 4.0, 2.2], gap="medium")
            with core_col, st.container(key="build-core"):
                _render_core(ss, quota)
            with steps_col, st.container(key="build-steps-zone"):
                st.markdown(_steps_html(step), unsafe_allow_html=True)
            with work_col, st.container(key="build-work"):
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
            with ident_col, st.container(key="build-identity"):
                _render_identity(ss, step, quota)
