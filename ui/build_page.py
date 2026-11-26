"""Halaman BUILD AOGx (Tahap 1): kanvas jaringan node + dialog referensi,
verifikasi limit, lalu pipeline RESEARCH + ANALISIS + PRODUCT PLANNING.

Alur visual kiri → kanan: INTI PROYEK → TAHAPAN (Permintaan, Referensi,
Bentuk, Validasi, Hasil — node berikutnya hanya muncul setelah prasyaratnya
selesai) → PROSES KERJA AI (cermin event pipeline nyata; tanpa angka progres
karangan) → panah ke panel IDENTITAS & FILE di paling kanan. Klik node membuka
drawer detail di bawah kanvas. Modul ini lapisan tampilan; jatah di
build/limits.py, pipeline di build/pipeline.py, snapshot proyek di
build/project_store.py. Tidak ada pembuatan kode aplikasi di tahap ini.
"""
import json
import uuid
from datetime import datetime
from html import escape as html_escape

import streamlit as st

import config
from agent.build_interview import DEFAULT_REFERENCES, suggest
from agent.build_research import TOPICS
from build import limits as build_limits
from build import pipeline as build_pipeline
from build import project_store
from core.utils import clip
from ui import thinking
from ui.build_nodes import (
    FLOW_POS, PREP_NODES, STAGES,
    cables_svg, compute_edges, core_html, live_layer_html,
    live_stage_from_text, node_position_css, prep_html, prep_status,
    prep_summary, process_nodes, proc_html, zoom_css,
)
from ui.build_style import CSS as BUILD_CSS

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


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Persistensi proyek (best-effort — lihat build/project_store.py)
# ---------------------------------------------------------------------------
def _restore_once(ss):
    """Muat snapshot proyek sekali per sesi baru (bila Supabase/memori punya)."""
    if ss.get("_bproj_loaded"):
        return
    ss["_bproj_loaded"] = True
    if ss.get("build_step") is not None:
        return  # sesi sudah punya state sendiri
    try:
        user_key = resolve_user_key(ss)
    except Exception:
        return
    data, err = project_store.load_project(user_key)
    if err:
        ss["build_persist_notice"] = err
    if data:
        project_store.restore_into(ss, data)


def _save_if_changed(ss):
    """Simpan snapshot hanya bila berubah (kanvas → store saat langkah berganti)."""
    snap = project_store.snapshot_from(ss)
    if not snap:
        return
    if set(snap) <= {"build_step"} and snap.get("build_step") == "request" \
            and not ss.get("_bproj_wipe"):
        return  # sesi kosong — jangan menulis baris percuma
    sig = json.dumps(snap, sort_keys=True, default=str, ensure_ascii=False)
    if sig == ss.get("_bproj_sig"):
        return
    ss["_bproj_sig"] = sig
    try:
        user_key = resolve_user_key(ss)
    except Exception:
        return
    err = project_store.save_project(user_key, snap)
    if err:
        ss["build_persist_notice"] = err
    else:
        ss.pop("build_persist_notice", None)
    ss.pop("_bproj_wipe", None)


# ---------------------------------------------------------------------------
# State graf & penyegaran live saat pipeline berjalan
# ---------------------------------------------------------------------------
def _graph(ss, step, quota, events=None, live="", error=None):
    """Bangun node tahapan + node proses + daftar tepi untuk satu render."""
    if events is None:
        events = ss.get("build_log") or []
    if error is None:
        error = ss.get("build_error") or ""
    prep = []
    for i, node in enumerate(PREP_NODES, start=1):
        status = prep_status(i, step)
        if status:
            prep.append({**node, "i": i, "status": status,
                         "summary": prep_summary(i, ss, quota)})
    proc = process_nodes(events, live_text=live, error=error)
    edges = compute_edges(prep, proc)
    return prep, proc, edges


def _live_refresh(ss, quota, events, live_text, proc_ph, cables_ph):
    """Perbarui layer node proses + kabel di tengah satu run pipeline."""
    if proc_ph is not None:
        proc_ph.markdown(live_layer_html(events, live_text),
                         unsafe_allow_html=True)
    if cables_ph is not None:
        _, _, edges = _graph(ss, "running", quota, events=events,
                             live=live_text, error="")
        cables_ph.markdown(cables_svg(edges), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Klik node / zoom (callback Streamlit — rerun alami setelah callback)
# ---------------------------------------------------------------------------
def _open_step(ss, target: str):
    ss["build_step"] = target
    ss["build_node_sel"] = None


def _select_node(ss, node_id: str):
    ss["build_node_sel"] = node_id


def _clear_sel(ss):
    ss["build_node_sel"] = None


def _zoom(ss, mode: str):
    if mode == "fit":
        ss["build_zoom"] = None
        return
    try:
        z = float(ss.get("build_zoom") or 1.0)
    except (TypeError, ValueError):
        z = 1.0
    z = z + 0.15 if mode == "in" else z - 0.15
    ss["build_zoom"] = round(min(1.5, max(0.55, z)), 2)


def _backend_label(backend: str) -> str:
    if backend == "supabase":
        return "Supabase"
    if backend == "memory":
        return "memori"
    return "memori (Supabase belum dikonfigurasi)"


# ---------------------------------------------------------------------------
# Kepala halaman, zoom, node inti, node tahapan, zona proses
# ---------------------------------------------------------------------------
def _render_header(ss) -> None:
    """Kepala halaman: wordmark + pil permintaan (gaya referensi)."""
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


def _render_zoom(ss):
    with st.container(key="build-zoomrow"):
        c1, c2, c3, c4 = st.columns([0.5, 0.5, 0.55, 8])
        with c1:
            st.button("Perbesar", key="bzoom-in", icon=":material/zoom_in:",
                      on_click=_zoom, args=(ss, "in"),
                      help="Perbesar tampilan kanvas")
        with c2:
            st.button("Perkecil", key="bzoom-out", icon=":material/zoom_out:",
                      on_click=_zoom, args=(ss, "out"),
                      help="Perkecil tampilan kanvas")
        with c3:
            st.button("Sesuaikan", key="bzoom-fit", icon=":material/fit_screen:",
                      on_click=_zoom, args=(ss, "fit"),
                      help="Paskan kanvas ke lebar layar")
        with c4:
            st.caption("Geser kanvas bila sempit — node dijaga tetap terbaca, "
                       "bukan diperkecil tanpa batas")


def _render_core(ss, step, quota):
    with st.container(key="bnode-core"):
        st.markdown(":material/hub: **INTI PROYEK**")
        st.markdown(core_html(ss, step, quota), unsafe_allow_html=True)
        st.button("Ringkasan proyek", key="btn-core",
                  on_click=_select_node, args=(ss, "core"),
                  help="Buka ringkasan proyek")


def _render_prep(ss, step, quota):
    for i, node in enumerate(PREP_NODES, start=1):
        status = prep_status(i, step)
        if not status:
            continue  # prasyarat belum terpenuhi → node tidak ditampilkan
        with st.container(key=f"bnode-{node['id']}"):
            st.markdown(f":material/{node['icon']}: "
                        f"**{node['no']}. {node['name']}**")
            st.markdown(prep_html(node, status, prep_summary(i, ss, quota)),
                        unsafe_allow_html=True)
            st.button(node["btn"], key=f"btn-{node['id']}",
                      on_click=_open_step, args=(ss, node["step"]),
                      help=f"Buka {node['name']}")


def _render_process_zone(ss, step, proc):
    """Zona C: layer live saat berjalan, kartu proses nyata setelahnya."""
    if step == "running":
        proc_ph = st.empty()
        proc_ph.markdown(live_layer_html(ss.get("build_log") or [], ""),
                         unsafe_allow_html=True)
        return proc_ph
    if proc:
        for node in proc:
            with st.container(key=f"bnode-{node['id']}"):
                st.markdown(f":material/{node['icon']}: "
                            f"**{node['no']}. {node['name']}**")
                st.markdown(proc_html(node), unsafe_allow_html=True)
                st.button(node["name"], key=f"btn-{node['id']}",
                          on_click=_select_node, args=(ss, node["id"]),
                          help=f"Detail {node['name']}")
    else:
        st.markdown('<div class="bld-wait">Proses kerja AI muncul di sini '
                    'setelah tahap Validasi dijalankan.</div>',
                    unsafe_allow_html=True)
    return None


# ---------------------------------------------------------------------------
# Zona D — Identitas & File (panel kanan, permanen)
# ---------------------------------------------------------------------------
def _render_identity(ss, step: str, quota: dict) -> None:
    """Panel paling kanan: identitas aplikasi + status pembangunan + berkas."""
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
    # Status pembangunan (angka nyata dari state; tanpa progres karangan).
    prep_done = sum(1 for i in range(1, 5)
                    if prep_status(i, step) == "completed")
    if step == "result":
        prep_done = 5
    proc_list = process_nodes(ss.get("build_log"),
                              error=ss.get("build_error") or "")
    proc_done = sum(1 for n in proc_list if n["status"] == "completed")
    tekh = blueprint.get("teknologi")
    if isinstance(tekh, (list, tuple)):
        tekh = ", ".join(str(t) for t in tekh)
    tekh = clip(str(tekh or "-"), 70)
    versi = ("Tahap 1 · blueprint" if blueprint
             else "-")
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
        '<div class="bld-sec-head">Status pembangunan</div>'
        '<div class="bld-note">'
        f'<div class="bld-row"><span>Tahapan</span><p>{prep_done}/5 selesai · '
        f"tahap {pos + 1}/{len(STEP_ORDER)} — {html_escape(label)}</p></div>"
        f'<div class="bld-row"><span>Proses AI</span><p>{proc_done}/3 selesai'
        "</p></div>"
        '<div class="bld-row"><span>File aplikasi</span><p>0 · Tahap 2 belum '
        "berjalan</p></div>"
        '<div class="bld-row"><span>Status uji</span><p>Belum — Tahap 2 '
        "(Pengujian)</p></div>"
        f'<div class="bld-row"><span>ID proyek</span><p>{html_escape(str(ss.get("build_project_id") or "-"))}</p></div>'
        f'<div class="bld-row"><span>Dibuat / selesai</span><p>{html_escape(str(ss.get("build_started_at") or "-"))} · '
        f'{html_escape(str(ss.get("build_finished_at") or "-"))}</p></div>'
        f'<div class="bld-row"><span>Versi aplikasi</span><p>{html_escape(versi)}</p></div>'
        f'<div class="bld-row"><span>Teknologi</span><p>{html_escape(tekh)}</p></div>'
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
    # Berkas hasil NYATA: blueprint JSON bisa diunduh begitu tersimpan.
    if blueprint:
        st.download_button(
            "Unduh blueprint (.json)",
            data=json.dumps(blueprint, ensure_ascii=False, indent=2),
            file_name="blueprint_aogx_build.json", mime="application/json",
            key="bld-dl-bp", icon=":material/download:",
            help="Simpan hasil blueprint sebagai berkas")
    proj_backend = "Supabase" if project_store.get_store() else "memori sesi"
    notice = ss.get("build_persist_notice")
    st.caption(f"Penyimpanan proyek: {proj_backend}" +
               (f" · {notice}" if notice else ""))


# ---------------------------------------------------------------------------
# Drawer detail di bawah kanvas (klik node → isi di sini)
# ---------------------------------------------------------------------------
def _drawer_core(ss, step, quota):
    res = ss.get("build_result") or {}
    bp = res.get("blueprint") or {}
    prep_done = sum(1 for i in range(1, 5)
                    if prep_status(i, step) == "completed")
    if step == "result":
        prep_done = 5
    proc_list = process_nodes(ss.get("build_log"),
                              error=ss.get("build_error") or "")
    proc_done = sum(1 for n in proc_list if n["status"] == "completed")
    st.markdown("### :material/hub: Ringkasan proyek")
    st.markdown(
        '<div class="bld-note">'
        '<div class="bld-row"><span>Permintaan</span><p>'
        f"{html_escape(clip(str(ss.get('build_request') or '-'), 120))}</p></div>"
        '<div class="bld-row"><span>Bentuk</span><p>'
        f"{html_escape(str(ss.get('build_form_kind') or '-'))}</p></div>"
        '<div class="bld-row"><span>Referensi</span><p>'
        f"{len(ss.get('build_refs') or ss.get('build_refs_pick') or [])} dipilih</p></div>"
        '<div class="bld-row"><span>Blueprint</span><p>'
        f"{html_escape(clip(str(bp.get('nama') or 'belum ada'), 70))}</p></div>"
        '<div class="bld-row"><span>Progres nyata</span><p>'
        f"{prep_done}/5 tahapan · {proc_done}/3 proses AI</p></div>"
        '<div class="bld-row"><span>Jatah</span><p>'
        f"{int(quota.get('used') or 0)}/{int(quota.get('max') or 0)} terpakai · "
        f"sisa {int(quota.get('remaining') or 0)}</p></div>"
        '<div class="bld-row"><span>ID proyek</span><p>'
        f"{html_escape(str(ss.get('build_project_id') or '-'))}</p></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.button("Tutup ringkasan", key="bnode-drawer-close",
              on_click=_clear_sel, args=(ss,), icon=":material/close:")


def _drawer_process(ss, node_id: str):
    events = ss.get("build_log") or []
    error = ss.get("build_error") or ""
    nodes = process_nodes(events, error=error)
    node = next((n for n in nodes if n["id"] == node_id), None)
    if node is None:
        st.info("Proses ini belum dimulai.")
        return
    stage = next(s for s in STAGES if s["id"] == node_id)
    agent = next((e for e in events
                  if e.get("kind") == "agent"
                  and e.get("stage") == stage["stage"]), None)
    logs = [e for e in events
            if e.get("kind") == "status"
            and live_stage_from_text(e.get("text", "")) == stage["stage"]]
    st.markdown(f"### :material/{stage['icon']}: "
                f"{stage['no']}. {stage['name']}")
    st.markdown(proc_html(node), unsafe_allow_html=True)
    if agent is not None:
        meta = " · ".join(x for x in (
            clip(str(agent.get("role") or ""), 24),
            clip(str(agent.get("provider") or ""), 24),
            str(agent.get("t") or "")) if x)
        if meta:
            st.caption(f"Dihasilkan {meta}")
        st.markdown(str(agent.get("text") or ""))
    if node["status"] == "failed" and error:
        st.error(error)
    if logs:
        with st.expander("Log tahap"):
            for entry in logs:
                st.caption(str(entry.get("text") or ""))
    st.button("Tutup", key="bnode-drawer-close",
              on_click=_clear_sel, args=(ss,), icon=":material/close:")


def _render_drawer(router, ss, step, quota, proc_ph, cables_ph):
    if ss.get("_bnode_seen_step") != step:
        ss["_bnode_seen_step"] = step
        ss["build_node_sel"] = None
    sel = ss.get("build_node_sel") or ""
    if sel == "core":
        _drawer_core(ss, step, quota)
        return
    if sel and sel[:2] in ("p1", "p2", "p3"):
        _drawer_process(ss, sel)
        return
    # Konten langkah aktif (form pengguna — dipisah dari aktivitas AI).
    if step == "reference":
        _step_reference(ss)
    elif step == "form":
        _step_form(ss)
    elif step == "confirm":
        _step_confirm(router, ss)
    elif step == "running":
        _step_running(router, ss, quota, proc_ph, cables_ph)
    elif step == "error":
        _step_error(ss)
    elif step == "result":
        _step_result(ss)
    else:
        _step_request(router, ss)


# ---------------------------------------------------------------------------
# Langkah persiapan (form pengguna)
# ---------------------------------------------------------------------------
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
        ss.setdefault("build_project_id", uuid.uuid4().hex[:12])
        ss.setdefault("build_started_at", _now_stamp())
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


def _step_running(router, ss, quota, proc_ph=None, cables_ph=None) -> None:
    st.markdown("### :material/rocket_launch: Proses BUILD")
    ss["build_attempts"] = int(ss.get("build_attempts") or 0) + 1
    request = str(ss.get("build_request") or "")
    refs = list(ss.get("build_refs") or [])
    form_kind = str(ss.get("build_form_kind") or "")
    live = st.empty()
    events = []
    final = None
    error = None
    for ev in build_pipeline.run(router, request, refs, form_kind):
        stamp = datetime.now().strftime("%H:%M:%S")
        if ev["kind"] == "status":
            # Status ikut dicatat supaya kegagalan tetap punya jejak tahapnya.
            events.append({**ev, "t": stamp})
            live.markdown(thinking.render(ev["text"]), unsafe_allow_html=True)
            _live_refresh(ss, quota, events, str(ev.get("text") or ""),
                          proc_ph, cables_ph)
        elif ev["kind"] == "agent":
            events.append({**ev, "t": stamp})
            live.markdown(
                thinking.render(f"{ev['stage']} selesai · {ev['role']} · {ev['provider']}"),
                unsafe_allow_html=True)
            _live_refresh(ss, quota, events, "", proc_ph, cables_ph)
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
    ss["build_log"] = events          # jejak nyata sampai titik gagal
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
    st.caption("Rincian proses tampil sebagai node di zona PROSES KERJA AI (kanvas); "
               "klik node untuk log & teks lengkap.")
    if st.button("BUILD baru", key="build_btn_new", icon=":material/add_task:",
                 use_container_width=False):
        # Reset state BUILD (bukan key widget yang sedang aktif, kecuali id anonim jatah).
        for key in ("build_step", "build_request", "build_request_input",
                    "build_ref_options", "build_ref_extra", "build_ref_reason",
                    "build_ai_ranked", "build_refs_pick", "build_ref_custom",
                    "build_ai_decide", "build_refs", "build_form_pick",
                    "build_form_kind", "build_result", "build_log", "build_error",
                    "build_attempts", "build_finished_at", "build_node_sel",
                    "build_project_id", "build_started_at"):
            ss.pop(key, None)
        ss["_bproj_wipe"] = True
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


# ---------------------------------------------------------------------------
# Render utama
# ---------------------------------------------------------------------------
def render_build_page(router, ss=None) -> None:
    """Titik masuk mode BUILD (dalam AOGx Agent Code) dari app.py.

    Tata letak: kanvas jaringan node — inti proyek → tahapan (muncul
    progresif) → proses kerja AI (cermin event pipeline) → panah ke panel
    identitas & file di paling kanan; drawer detail di bawah kanvas.
    """
    ss = ss if ss is not None else st.session_state
    _restore_once(ss)
    ss.setdefault("build_step", "request")
    step = str(ss.get("build_step") or "request")
    if step not in [k for k, _ in STEP_ORDER] + ["error"]:
        ss["build_step"] = "request"
        step = "request"
    try:
        quota = build_limits.limit_status(resolve_user_key(ss))
    except Exception:
        quota = {"used": 0, "max": 0, "remaining": 0, "backend": "",
                 "reset_at": "", "error": ""}
    _save_if_changed(ss)
    st.markdown(BUILD_CSS, unsafe_allow_html=True)
    st.markdown(f"<style id='aogx-build-geom'>{node_position_css()}\n"
                f"{zoom_css(ss)}</style>")
    with st.container(key="build-page"):
        _render_header(ss)
        st.caption("Beri satu perintah, tim agen meneliti aplikasi referensi, menganalisis "
                   "kekurangannya, lalu menyusun blueprint aplikasi alternatif. Tahap ini belum "
                   "membuat kode aplikasi.")
        st.caption(":material/account_tree: Kanvas node: inti proyek → tahapan → proses "
                   "kerja AI → identitas & file. Node berikutnya hanya muncul setelah "
                   "prasyaratnya selesai; klik node untuk detail.")
        _render_zoom(ss)
        with st.container(key="build-graph"):
            canvas_col, ident_col = st.columns([7.3, 2.7], gap="medium")
            with canvas_col:
                with st.container(key="build-canvas"):
                    with st.container(key="build-canvas-inner"):
                        prep, proc, edges = _graph(ss, step, quota)
                        cables_ph = st.empty()
                        cables_ph.markdown(cables_svg(edges),
                                           unsafe_allow_html=True)
                        _render_core(ss, step, quota)
                        _render_prep(ss, step, quota)
                        proc_ph = _render_process_zone(ss, step, proc)
            with ident_col, st.container(key="build-identity"):
                _render_identity(ss, step, quota)
        with st.container(key="build-drawer"):
            _render_drawer(router, ss, step, quota, proc_ph, cables_ph)
