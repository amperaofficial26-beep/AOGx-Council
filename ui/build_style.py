"""Gaya visual halaman BUILD AOGx (Tahap 1) mengikuti referensi dashboard gelap.

Referensi (screenshot): kanvas teal-hitam, kartu langkah bernomor dengan aktif
bersudut emas, panel ringkasan di kanan berisi judul + badge status + kartu jatah +
ubin statistik 2x2 + kartu ringkasan. CSS murni dipakai lewat
st.markdown(..., unsafe_allow_html=True) dari ui/build_page.

Semua aturan utama di-scope di bawah .st-key-build-page (container key halaman)
agar halaman lain tak tersentuh; kelas .bld-* hanya dipancarkan build_page.
Tanpa blur/backdrop-filter dan tanpa animasi berat — ikuti aturan performa aplikasi.
"""

CSS = """
<style>
/* ——— Kanvas halaman: latar teal-hitam dengan cahaya lembut ——— */
.st-key-build-page {
    position: relative;
    background:
        radial-gradient(ellipse 60% 44% at 16% 0%, rgba(45, 212, 191, .13), transparent 70%),
        radial-gradient(ellipse 50% 40% at 90% 4%, rgba(224, 180, 110, .07), transparent 72%),
        radial-gradient(ellipse 70% 46% at 50% 104%, rgba(45, 212, 191, .05), transparent 74%),
        linear-gradient(180deg, #0a1213 0%, #060a0a 100%);
    border: 1px solid rgba(148, 163, 184, .12);
    border-radius: 20px;
    padding: 20px 22px 26px;
    box-sizing: border-box;
}

/* ——— Kepala halaman: orb + wordmark + pil konteks ——— */
.bld-head {
    display: flex; align-items: center; gap: 14px;
    margin: 2px 0 16px;
}
.bld-orb {
    flex: 0 0 44px; width: 44px; height: 44px; border-radius: 50%;
    position: relative;
    background: radial-gradient(circle at 34% 30%, #c4b5fd 0%, #8b7cf0 36%, #4c3f9e 68%, #241d55 100%);
    box-shadow: 0 0 18px rgba(139, 124, 240, .55), inset 0 -6px 14px rgba(0, 0, 0, .45);
}
.bld-orb::after {
    content: ""; position: absolute; inset: -7px; border-radius: 50%;
    border: 1px solid rgba(139, 124, 240, .35);
}
.bld-wordmark { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.bld-wordmark strong {
    color: #f4f8f7; font-size: 20px; font-weight: 800;
    letter-spacing: .2px; line-height: 1.1;
}
.bld-wordmark strong em { font-style: normal; color: #e0b46e; }
.bld-wordmark small {
    color: #7d918d; font-size: 10.5px; font-weight: 700;
    letter-spacing: 1.6px; text-transform: uppercase; white-space: nowrap;
}
.bld-pill {
    margin-left: auto; max-width: min(46%, 520px);
    background: rgba(13, 25, 26, .9); border: 1px solid rgba(148, 163, 184, .18);
    color: #9fb3af; font-size: 12.5px; font-weight: 600;
    padding: 8px 14px; border-radius: 999px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* ——— Baris kartu langkah (peta navigasi, aktif = emas) ——— */
.bld-flow {
    display: flex; flex-wrap: wrap; gap: 10px;
    margin: 2px 0 16px;
}
.bld-step {
    position: relative; flex: 1 1 118px; min-width: 0;
    display: flex; flex-direction: column; gap: 4px;
    background: linear-gradient(165deg, rgba(19, 32, 34, .95), rgba(13, 22, 23, .92));
    border: 1px solid rgba(148, 163, 184, .14);
    border-radius: 14px; padding: 10px 14px 11px;
    box-sizing: border-box;
}
.bld-step-num { font-size: 19px; font-weight: 800; color: #5f7370; line-height: 1; }
.bld-step-label {
    font-size: 12px; font-weight: 700; color: #8fa3a0; letter-spacing: .3px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.bld-step.is-done { border-color: rgba(94, 234, 212, .30); }
.bld-step.is-done .bld-step-num { color: #5eead4; }
.bld-step.is-done .bld-step-label { color: #a7c4be; }
.bld-step.is-current {
    border-color: rgba(224, 180, 110, .85);
    background: linear-gradient(165deg, rgba(43, 52, 47, .95), rgba(20, 30, 28, .92));
    box-shadow: 0 0 0 1px rgba(224, 180, 110, .25), 0 0 22px rgba(224, 180, 110, .16);
}
.bld-step.is-current .bld-step-num { color: #e0b46e; }
.bld-step.is-current .bld-step-label { color: #f2e7d3; }
.bld-step:not(:last-child)::after {
    content: ""; position: absolute; right: -9px; top: 50%;
    width: 7px; height: 7px;
    border-top: 2px solid rgba(148, 163, 184, .5);
    border-right: 2px solid rgba(148, 163, 184, .5);
    transform: translateY(-50%) rotate(45deg);
}

/* ——— Kolom utama: tipografi langkah ——— */
.st-key-build-main h3 {
    color: #f2f6f5; font-size: 1.06rem; font-weight: 800;
    letter-spacing: .2px; margin: .25rem 0 .1rem;
}
.st-key-build-main [data-testid="stCaptionContainer"] { color: #8fa3a0 !important; }
.st-key-build-main [data-testid="stMarkdownContainer"] p { color: #c6d4d1; }

/* ——— Widget di dalam halaman BUILD ——— */
.st-key-build-page [data-testid="stTextArea"] textarea,
.st-key-build-page [data-testid="stTextInput"] input {
    background: rgba(9, 17, 18, .9) !important;
    border: 1px solid rgba(148, 163, 184, .2) !important;
    border-radius: 12px !important;
    color: #e7efed !important;
}
.st-key-build-page [data-testid="stTextArea"] textarea:focus,
.st-key-build-page [data-testid="stTextInput"] input:focus {
    border-color: rgba(224, 180, 110, .65) !important;
    box-shadow: 0 0 0 3px rgba(224, 180, 110, .14) !important;
}
.st-key-build-page [data-testid="stSelectbox"] [data-baseweb="select"],
.st-key-build-page [data-testid="stMultiSelect"] [data-baseweb="select"] {
    background: rgba(9, 17, 18, .9) !important;
    border-color: rgba(148, 163, 184, .2) !important;
    border-radius: 12px !important;
}
.st-key-build-page [data-baseweb="tag"] {
    background: rgba(94, 234, 212, .12) !important;
    color: #99f6e4 !important;
    border-color: rgba(94, 234, 212, .35) !important;
    border-radius: 8px !important;
}
.st-key-build-page [data-testid="stRadioOption"] {
    background: rgba(9, 17, 18, .75) !important;
    border: 1px solid rgba(148, 163, 184, .16) !important;
    border-radius: 12px !important;
    padding: 9px 12px !important;
}
.st-key-build-page [data-testid="stRadioOption"] + [data-testid="stRadioOption"] {
    margin-top: 8px !important;
}
.st-key-build-page [data-testid="stRadioOption"]:has(input:checked) {
    border-color: rgba(224, 180, 110, .8) !important;
    background: rgba(43, 52, 47, .85) !important;
    box-shadow: 0 0 16px rgba(224, 180, 110, .14);
}
.st-key-build-page [data-testid="stRadioOption"] input { accent-color: #e0b46e !important; }
.st-key-build-page [data-testid="stCheckbox"] input { accent-color: #e0b46e !important; }

.st-key-build-page [data-testid="stButton"] button {
    border-radius: 11px !important;
    font-weight: 700 !important;
    min-height: 40px !important;
    border: 1px solid rgba(148, 163, 184, .22) !important;
    background: rgba(13, 25, 26, .85) !important;
    color: #cbd5e1 !important;
    transition: background .15s ease, border-color .15s ease !important;
}
.st-key-build-page [data-testid="stButton"] button:hover:not(:disabled) {
    border-color: rgba(224, 180, 110, .5) !important;
    background: rgba(24, 36, 36, .95) !important;
    color: #f0e6d4 !important;
}
.st-key-build-page [data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(180deg, #eec27c, #d3a257) !important;
    border-color: transparent !important;
    color: #1a1408 !important;
    box-shadow: 0 6px 18px rgba(224, 180, 110, .22);
}
.st-key-build-page [data-testid="stButton"] button[kind="primary"]:hover:not(:disabled) {
    background: linear-gradient(180deg, #f5cf90, #dcaf66) !important;
    color: #1a1408 !important;
}
.st-key-build-page [data-testid="stButton"] button:disabled { opacity: .55 !important; }

.st-key-build-page [data-testid="stAlert"] {
    border-radius: 14px !important;
    border: 1px solid rgba(148, 163, 184, .18) !important;
}

.st-key-build-page [data-testid="stTabs"] [role="tab"] {
    color: #8fa3a0 !important; font-weight: 700 !important; font-size: .86rem !important;
}
.st-key-build-page [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #e0b46e !important;
}
.st-key-build-page [data-testid="stTabs"] [role="tablist"] {
    border-bottom-color: rgba(148, 163, 184, .16) !important;
}

/* ——— Panel ringkasan di kanan (gaya kartu detail referensi) ——— */
.st-key-build-side { position: sticky; top: 104px; }
.bld-panel {
    background: linear-gradient(168deg, rgba(18, 32, 34, .96), rgba(10, 18, 19, .96));
    border: 1px solid rgba(148, 163, 184, .16);
    border-radius: 18px;
    padding: 18px 18px 16px;
    box-shadow: 0 18px 40px rgba(0, 0, 0, .35);
}
.bld-kicker {
    color: #86a69c; font-size: 12.5px; font-weight: 700; letter-spacing: .6px;
    display: flex; align-items: center; gap: 8px;
}
.bld-kicker::before {
    content: ""; width: 9px; height: 9px; border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #99f6e4, #2dd4bf 60%, #0f766e);
    box-shadow: 0 0 8px rgba(45, 212, 191, .55);
}
.bld-title {
    color: #f4f8f7; font-size: 1.3rem; font-weight: 800;
    line-height: 1.28; margin: 9px 0 13px;
}
.bld-status {
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    margin-bottom: 14px;
}
.bld-badge {
    background: rgba(16, 52, 40, .95); color: #4ade80;
    border: 1px solid rgba(52, 211, 153, .4);
    font-size: 11px; font-weight: 800; letter-spacing: .8px; text-transform: uppercase;
    padding: 5px 10px; border-radius: 999px; white-space: nowrap;
}
.bld-badge.is-warn {
    background: rgba(69, 26, 26, .95); color: #f87171;
    border-color: rgba(248, 113, 113, .4);
}
.bld-badge.is-soft {
    background: rgba(30, 41, 44, .95); color: #9fb3af;
    border-color: rgba(148, 163, 184, .3);
}
.bld-meta { color: #8fa3a0; font-size: 12px; line-height: 1.45; }
.bld-subcard {
    background: #172224; border: 1px solid rgba(148, 163, 184, .14);
    border-radius: 14px; padding: 14px 15px; margin-bottom: 12px;
}
.bld-subcard-head {
    display: flex; justify-content: space-between; align-items: center; gap: 8px;
    margin-bottom: 9px;
}
.bld-subcard-head span:first-child {
    color: #c9d6d3; font-size: 13.5px; font-weight: 700;
}
.bld-big { color: #f7fbfa; font-size: 2rem; font-weight: 800; line-height: 1; }
.bld-sub { color: #8fa3a0; font-size: 12px; margin-top: 7px; line-height: 1.45; }
.bld-stats {
    display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin-bottom: 14px;
}
.bld-stat {
    background: #101a1c; border: 1px solid rgba(148, 163, 184, .12);
    border-radius: 13px; padding: 11px 13px;
    min-width: 0;
}
.bld-stat-num { color: #f2f6f5; font-size: 1.35rem; font-weight: 800; line-height: 1.1; }
.bld-stat-label {
    color: #8fa3a0; font-size: 11.5px; font-weight: 600;
    margin-top: 3px; line-height: 1.35;
}
.bld-sec-head {
    display: flex; align-items: center; gap: 8px;
    color: #9fb3af; font-size: 12px; font-weight: 800;
    letter-spacing: 1.4px; text-transform: uppercase;
    margin: 2px 0 9px;
}
.bld-sec-head::before {
    content: ""; width: 16px; height: 2px; border-radius: 2px;
    background: linear-gradient(90deg, #e0b46e, transparent);
}
.bld-note {
    background: #172224; border: 1px solid rgba(148, 163, 184, .14);
    border-radius: 14px; padding: 13px 15px;
    display: flex; flex-direction: column; gap: 10px;
}
.bld-row span {
    display: block; color: #7f938f; font-size: 11px; font-weight: 800;
    letter-spacing: .9px; text-transform: uppercase; margin-bottom: 3px;
}
.bld-row p {
    margin: 0; color: #d7e2df; font-size: 13px; line-height: 1.5;
    word-break: break-word;
}

/* ——— Layar sempit: lepas panel lengket, pil konteks ikut menyusut ——— */
@media (max-width: 1000px) {
    .st-key-build-side { position: static !important; }
    .bld-pill { max-width: 40%; }
}
</style>
"""
