
# ---------- Kiri: chat ----------
CHAT_TAIL = '<div style="height:64px"></div>'

with left:
    chat_box = st.container(height=440, border=False, key="chat-history")
    try:
        submitted = st.chat_input(
            "Kirim pesan ke AOGx Council…",
            accept_file="multiple",
            file_type=["pdf", "png", "jpg", "jpeg", "webp", "txt", "md"],
        )
    except TypeError:
        submitted = st.chat_input("Kirim pesan ke AOGx Council…")
    question = ""
    if submitted is not None:
        if hasattr(submitted, "text"):
            question = (submitted.text or "").strip()
            attachments = list(submitted.files or [])
            if attachments:
                names = ", ".join(f.name for f in attachments)
                question = (question + "\n\n" if question else "") + f"Lampiran: {names}"
        else:
            question = str(submitted).strip()

with chat_box:
    if not ss.messages and not question:
        st.markdown('<div class="aog-warn">Belum ada pertanyaan. Kirim satu pertanyaan, lalu '
                    'lihat mesin di kanan: kubus menyala biru saat agen bekerja, hijau saat '
                    'selesai, dan abu-abu saat tahapannya dilewati.</div>',
                    unsafe_allow_html=True)
    for i, m in enumerate(ss.messages):
        with st.chat_message(m["role"]):
            if m["role"] == "user":
                st.markdown('<span class="aog-user-marker"></span>', unsafe_allow_html=True)
                st.markdown(m["content"])
            else:
                render_answer(m, i)

if question:
    question = question.strip()
    usable = demo or bool(active)
    if len(question) > config.MAX_QUESTION_CHARS:
        with chat_box:
            st.error(f"Pertanyaan terlalu panjang (maks {config.MAX_QUESTION_CHARS} karakter).")
    elif ss.n_requests >= config.MAX_REQUESTS_PER_SESSION:
        with chat_box:
            st.error("Batas permintaan sesi ini tercapai. Klik \"Chat baru\" atau muat ulang halaman.")
    elif not usable:
        with chat_box:
            st.error("Belum ada provider aktif. Isi API key di `.env` atau Streamlit secrets "
                     "(lihat `env.example`).")
    else:
        history = history_text(ss.messages)
        ss.messages.append({"role": "user", "content": question})
        ss.n_requests += 1
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
                st.markdown('<span class="aog-user-marker"></span>', unsafe_allow_html=True)
                st.markdown(question)
            ph_live = st.empty()
        ph_live.markdown(thinking.render(flow.stage_text or "Council mulai bekerja") + CHAT_TAIL,
                         unsafe_allow_html=True)
        log, final, error = [], None, None
        for ev in pipeline.run(run_router, question, mode, history):
            action = flow.consume(ev)
            if ev["kind"] == "agent":
                log.append({"role": ev["role"], "provider": ev["provider"],
                            "stage": ev["stage"], "text": ev["text"]})
                ph_live.markdown(thinking.render(ev["stage"], ev["role"]) + CHAT_TAIL,
                                 unsafe_allow_html=True)
            elif ev["kind"] == "status":
                ph_live.markdown(thinking.render(ev["text"]) + CHAT_TAIL, unsafe_allow_html=True)
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
                    st.markdown('<span class="aog-assistant-marker"></span>', unsafe_allow_html=True)
                    st.error(error or "Pipeline berhenti tanpa hasil.")
                    if getattr(run_router, "last_error", None):
                        with st.expander("Detail error provider"):
                            for n, e in run_router.last_error.items():
                                st.text(f"{n}: {e}")
                    ss.messages.pop()
                    ss.n_requests -= 1
        draw()

with chat_box:
    st.markdown(CHAT_TAIL, unsafe_allow_html=True)

# Panel GitHub dan Video Studio diletakkan di bawah kolom chat.
with left:
    github_pr_panel()
    with st.expander("Video Studio · Dola → YouTube Shorts", expanded=False):
        video_studio.render()
    with st.expander("Autonomous Creator · Jadwal Video Harian", expanded=False):
        autonomous_creator.render()
