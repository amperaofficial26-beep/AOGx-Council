"""AOGx video studio: preview a user-provided Dola export, then upload with consent."""
import streamlit as st

import config
from providers import youtube


def render():
    st.markdown("### :material/video_library: AOGx Video Studio")
    st.caption(
        "Buat video di Dola secara manual, unduh hasilnya, lalu unggah ke sini untuk "
        "pratinjau dan upload ke YouTube setelah kamu menyetujui."
    )

    client_id = config.get_secret("YOUTUBE_CLIENT_ID")
    client_secret = config.get_secret("YOUTUBE_CLIENT_SECRET")
    redirect_uri = config.get_secret("YOUTUBE_REDIRECT_URI")

    params = st.query_params
    state = params.get("state")
    code = params.get("code")
    oauth_error = params.get("error")
    # Only handle the YouTube state namespace; GitHub OAuth owns its own callback.
    if state and str(state).startswith("yt.") and (code or oauth_error):
        if oauth_error:
            st.error("Login YouTube dibatalkan atau ditolak.")
            st.query_params.clear()
        elif not (client_id and client_secret and redirect_uri and
                  youtube.verify_state(str(state), client_secret) and code):
            st.error("Callback YouTube tidak valid/kedaluwarsa. Hubungkan akun kembali.")
            st.query_params.clear()
        else:
            try:
                tokens = youtube.exchange_code(client_id, client_secret, str(code), redirect_uri)
                st.session_state.yt_access_token = tokens["access_token"]
                if tokens.get("refresh_token"):
                    st.session_state.yt_refresh_token = tokens["refresh_token"]
                st.session_state.yt_connected = True
                st.query_params.clear()
                st.rerun()
            except youtube.YouTubeError as exc:
                st.error(str(exc))
                st.query_params.clear()

    if not (client_id and client_secret and redirect_uri):
        st.info(
            "Tambahkan YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, dan YOUTUBE_REDIRECT_URI "
            "ke Streamlit Secrets untuk mengaktifkan upload."
        )
        return

    if not st.session_state.get("yt_connected"):
        state = youtube.make_state(client_secret)
        st.link_button(
            "Hubungkan akun YouTube",
            youtube.authorization_url(client_id, redirect_uri, state),
            icon=":material/link:",
            use_container_width=True,
        )
    else:
        st.success("Akun YouTube terhubung untuk upload.")
        if st.button("Putuskan YouTube", key="yt_disconnect", icon=":material/link_off:"):
            for key in ("yt_access_token", "yt_refresh_token", "yt_connected"):
                st.session_state.pop(key, None)
            st.rerun()

    st.divider()
    video = st.file_uploader(
        "Unggah hasil video dari Dola (MP4 disarankan)",
        type=["mp4"],
        key="yt_video_file",
    )
    if video:
        video_bytes = video.getvalue()
        st.video(video_bytes)
        st.caption(f"File: {video.name} · {len(video_bytes) / (1024 * 1024):.1f} MB")
        st.warning(
            "Periksa sendiri durasi 20 detik dan rasio vertikal 9:16 sebelum upload. "
            "Studio ini belum mengubah atau memotong video otomatis."
        )
        title = st.text_input("Judul Shorts", value="Video dibuat dengan bantuan AI", max_chars=100)
        description = st.text_area(
            "Deskripsi",
            value="#Shorts\nVideo dibuat dengan bantuan AI.",
            max_chars=5000,
        )
        privacy = st.selectbox("Privasi saat diunggah", ["public", "unlisted", "private"], index=0)
        approved = st.checkbox(
            "Saya sudah menonton pratinjau dan menyetujui video ini diunggah ke YouTube.",
            key="yt_upload_approved",
        )
        if st.button(
            "Unggah ke YouTube",
            type="primary",
            use_container_width=True,
            disabled=not (approved and st.session_state.get("yt_connected")),
            key="yt_upload_button",
        ):
            token = st.session_state.get("yt_access_token", "")
            try:
                if not token and st.session_state.get("yt_refresh_token"):
                    refreshed = youtube.refresh_access_token(
                        client_id, client_secret, st.session_state.yt_refresh_token
                    )
                    token = refreshed.get("access_token", "")
                    st.session_state.yt_access_token = token
                if not token:
                    raise youtube.YouTubeError("Hubungkan ulang akun YouTube sebelum upload.")
                with st.spinner("Mengunggah video ke YouTube…"):
                    result = youtube.upload_video(
                        token, video_bytes, video.name, title, description, privacy
                    )
                st.success("Video berhasil diunggah.")
                st.link_button("Buka video di YouTube", result["url"], icon=":material/open_in_new:")
            except youtube.YouTubeError as exc:
                st.error(str(exc))
