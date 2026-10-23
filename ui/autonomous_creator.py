"""UI for saving a persistent, scheduled creator instruction."""
from __future__ import annotations

import hmac
from datetime import time

import streamlit as st

import config
from automation.store import StoreError, SupabaseStore

DEFAULT_INSTRUCTION = (
    "Create an original faceless Miniature Building ASMR video, 20 seconds long, "
    "vertical 9:16, targeting an international English-speaking audience. "
    "Show hands building a tiny detailed structure with satisfying tactile materials "
    "and natural ASMR. Vary the miniature concept and construction sequence each day. "
    "Create an English title and description for YouTube Shorts. Avoid logos, copyrighted "
    "characters, misleading claims, and repetitive videos."
)


def render():
    st.markdown("### :material/auto_awesome: Autonomous Video Creator")
    st.caption("Simpan satu instruksi; worker terjadwal akan menyiapkan brief harian dan memanggil provider video yang sudah diotorisasi.")

    gate = config.get_secret("AUTOMATION_ACCESS_CODE")
    if not gate:
        st.warning("Panel otomatisasi dinonaktifkan sampai AUTOMATION_ACCESS_CODE diatur di Streamlit Secrets.")
        return
    entered = st.text_input("Kode akses otomatisasi", type="password", key="autocreator_access")
    if not hmac.compare_digest(str(entered).encode(), str(gate).encode()):
        st.info("Masukkan kode akses otomatisasi untuk mengelola jadwal.")
        return

    store = None
    current = None
    try:
        store = SupabaseStore(config.get_secret("SUPABASE_URL"),
                              config.get_secret("SUPABASE_SERVICE_ROLE_KEY"))
        current = store.get_job("main")
    except StoreError:
        st.warning("Database belum terhubung. Lengkapi SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY di Streamlit Secrets, lalu jalankan automation/schema.sql.")

    saved_time = (current or {}).get("scheduled_time", "08:00:00")
    try:
        parts = str(saved_time).split(":")
        default_schedule = time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        default_schedule = time(8, 0)

    with st.form("autonomous_creator_form"):
        instruction = st.text_area(
            "Perintah utama AI", value=(current or {}).get("instruction", DEFAULT_INSTRUCTION),
            height=180, max_chars=6000,
            help="Perintah ini menjadi kebijakan konten yang digunakan ulang setiap hari.",
        )
        schedule = st.time_input(
            "Waktu produksi harian (WIB)", value=default_schedule,
            help="Waktu Asia/Jakarta. Worker berjalan melalui GitHub Actions; waktu mulai dapat sedikit terlambat karena antrean scheduler.",
        )
        active = st.checkbox("Aktifkan produksi harian", value=bool((current or {}).get("active", True)))
        submitted = st.form_submit_button("Simpan jadwal otomatis", type="primary", use_container_width=True)
    if submitted:
        try:
            store = SupabaseStore(config.get_secret("SUPABASE_URL"),
                                  config.get_secret("SUPABASE_SERVICE_ROLE_KEY"))
            store.save_job(instruction, schedule.strftime("%H:%M"), "Asia/Jakarta", active)
            st.success(f"Instruksi tersimpan. Jadwal: {schedule.strftime('%H:%M')} WIB.")
            st.rerun()
        except StoreError as exc:
            st.error(str(exc))

    if store is not None:
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            today = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
            run = store.get_run("main", today)
            if run:
                st.caption(f"Status tugas hari ini: {run.get('status', 'unknown')}")
                if run.get("error"):
                    st.warning(run["error"])
                if run.get("video_url"):
                    st.link_button("Buka hasil YouTube", run["video_url"], icon=":material/open_in_new:")
        except StoreError:
            pass

    st.divider()
    st.markdown("**Status integrasi**")
    st.write("AI Creative Director: memakai provider AI yang dikonfigurasi di AOGx.")
    video_provider = config.get_secret("VIDEO_PROVIDER") or "belum dipilih"
    st.write(f"Provider video: `{video_provider}`")
    if video_provider.lower() == "dola":
        st.warning("Generasi Dola belum aktif sampai API resmi dan izin otomasi komersial tersedia.")
    else:
        st.info("Provider video perlu adapter resmi sebelum generasi otomatis aktif.")
    st.caption("Fondasi ini menyimpan jadwal dan brief harian. Generasi video serta upload otomatis belum aktif sampai adapter provider terpasang dan diuji.")
