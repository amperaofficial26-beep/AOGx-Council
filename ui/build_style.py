"""Gaya visual halaman BUILD AOGx (Tahap 1) mengikuti referensi dashboard gelap.

Referensi: kanvas teal-hitam dengan alur kiri-kanan — inti (orb) → kabel → panel
tahap kecil bertumpuk → area kerja/proses → panel identitas di paling kanan.
CSS murni dipakai lewat st.markdown(..., unsafe_allow_html=True) dari ui/build_page;
kelas .bld-* hanya dipancarkan build_page. Tanpa blur/backdrop-filter dan tanpa
animasi berat — ikuti aturan performa aplikasi.
"""

# Lapisan kabel dekoratif melintasi seluruh baris graf (dipancarkan build_page
# sebagai anak pertama container build-graph). Geometri = patahan bezier antar
# batas kolom (rasio 1.6 / 2.2 / 4.0 / 2.2 + gap medium), presisi dekoratif.
CABLES = """
<svg class="bld-cables" viewBox="0 0 1000 400" preserveAspectRatio="none" aria-hidden="true">
  <defs>
    <linearGradient id="bldCableGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#e0b46e" stop-opacity=".9"/>
      <stop offset=".45" stop-color="#5eead4" stop-opacity=".6"/>
      <stop offset="1" stop-color="#5eead4" stop-opacity=".3"/>
    </linearGradient>
  </defs>
  <path vector-effect="non-scaling-stroke" d="M149,96 C168,96 154,64 174,62"/>
  <path vector-effect="non-scaling-stroke" d="M174,62 C174,170 174,250 174,330"/>
  <path vector-effect="non-scaling-stroke" d="M377,300 C392,300 386,300 402,300"/>
  <path vector-effect="non-scaling-stroke" d="M772,300 C786,300 782,300 797,300"/>
  <circle cx="174" cy="62" r="4.5" fill="#e0b46e"/>
  <circle cx="402" cy="300" r="4.5" fill="#5eead4"/>
  <circle cx="797" cy="300" r="4.5" fill="#5eead4"/>
</svg>
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

/* ——— Kepala halaman: wordmark + pil konteks ——— */
.bld-head {
    display: flex; align-items: center; gap: 14px;
    margin: 2px 0 14px;
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

/* ——— Baris graf: lapisan kabel dekoratif di belakang kolom ——— */
.st-key-build-graph { position: relative; }
.bld-cables {
    position: absolute; left: 0; top: 0; width: 100%; height: 100%;
    pointer-events: none; z-index: 0; overflow: visible;
}
.bld-cables path { fill: none; stroke: url(#bldCableGrad); stroke-width: 1.6;
    stroke-linecap: round; }
.st-key-build-graph [data-testid="stHorizontalBlock"] {
    position: relative; z-index: 1;
}
/* Markdown pembawa kabel tidak boleh menyisakan slot gap. */
.st-key-build-graph [data-testid="stElementContainer"]:has(.bld-cables) {
    height: 0 !important; min-height: 0 !important; margin: 0 !important;
    overflow: visible !important;
}

/* ——— Zona inti (paling kiri): orb + nama proyek + chip jatah ——— */
.st-key-build-core { position: relative; }
.bld-core {
    display: flex; flex-direction: column; gap: 12px; align-items: flex-start;
    background: linear-gradient(168deg, rgba(18, 32, 34, .96), rgba(10, 18, 19, .96));
    border: 1px solid rgba(148, 163, 184, .16);
    border-radius: 18px; padding: 16px 16px 15px;
    box-shadow: 0 18px 40px rgba(0, 0, 0, .35);
    box-sizing: border-box; width: 100%;
}
.bld-zone-kicker {
    color: #7d918d; font-size: 11px; font-weight: 800;
    letter-spacing: 1.4px; text-transform: uppercase; margin-bottom: 10px;
}
.bld-orb {
    flex: 0 0 44px; width: 44px; height: 44px; border-radius: 50%;
    position: relative;
    background: radial-gradient(circle at 34% 30%, #c4b5fd 0%, #8b7cf0 36%, #4c3f9e 68%, #241d55 100%);
    box-shadow: 0 0 18px rgba(139, 124, 240, .55), inset 0 -6px 14px rgba(0, 0, 0, .45);
}
.bld-core .bld-orb {
    width: 64px; height: 64px; flex: 0 0 64px; align-self: center;
    box-shadow: 0 0 26px rgba(139, 124, 240, .6), inset 0 -8px 18px rgba(0, 0, 0, .45);
}
.bld-orb::after {
    content: ""; position: absolute; inset: -7px; border-radius: 50%;
    border: 1px solid rgba(139, 124, 240, .35);
}
.bld-core-name {
    color: #f2f6f5; font-size: 14px; font-weight: 700; line-height: 1.45;
    word-break: break-word; width: 100%; text-align: center;
}
.bld-core-badges { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center;
    width: 100%; }
.bld-chip {
    font-size: 10.5px; font-weight: 800; letter-spacing: .6px; text-transform: uppercase;
    padding: 5px 9px; border-radius: 999px;
    border: 1px solid rgba(94, 234, 212, .35);
    background: rgba(13, 40, 38, .85); color: #5eead4; white-space: nowrap;
}
.bld-chip.is-gold {
    border-color: rgba(224, 180, 110, .45);
    background: rgba(45, 36, 20, .85); color: #e0b46e;
}
.bld-chip.is-warn {
    border-color: rgba(248, 113, 113, .45);
    background: rgba(69, 26, 26, .85); color: #f87171;
}

/* ——— Zona tahapan: kartu kecil bertumpuk + tulang punggung kabel ——— */
.st-key-build-steps-zone { position: relative; }
.bld-steps {
    position: relative; padding-left: 24px;
    display: flex; flex-direction: column; gap: 10px;
}
.bld-spine {
    position: absolute; left: 7px; top: 6px; bottom: 6px; width: 2px;
    background: linear-gradient(180deg, rgba(224, 180, 110, .75),
                rgba(94, 234, 212, .5) 55%, rgba(148, 163, 184, .22));
    border-radius: 2px;
}
.bld-stepcard {
    position: relative; display: flex; align-items: center; gap: 10px;
    background: linear-gradient(165deg, rgba(19, 32, 34, .95), rgba(13, 22, 23, .92));
    border: 1px solid rgba(148, 163, 184, .14);
    border-radius: 13px; padding: 9px 12px;
    box-sizing: border-box;
}
.bld-stepcard::before {
    content: ""; position: absolute; left: -17px; top: 50%;
    width: 17px; height: 2px; background: rgba(148, 163, 184, .45);
    transform: translateY(-50%);
}
.bld-stepcard::after {
    content: ""; position: absolute; left: -21px; top: 50%;
    width: 8px; height: 8px; border-radius: 50%;
    background: #0e1718; border: 2px solid rgba(148, 163, 184, .55);
    transform: translateY(-50%);
    box-sizing: border-box;
}
.bld-stepcard.is-current {
    border-color: rgba(224, 180, 110, .85);
    background: linear-gradient(165deg, rgba(43, 52, 47, .95), rgba(20, 30, 28, .92));
    box-shadow: 0 0 0 1px rgba(224, 180, 110, .25), 0 0 18px rgba(224, 180, 110, .15);
}
.bld-stepcard.is-current::before { background: rgba(224, 180, 110, .75); }
.bld-stepcard.is-current::after {
    border-color: #e0b46e; box-shadow: 0 0 9px rgba(224, 180, 110, .65);
}
.bld-stepcard.is-done::after { border-color: #5eead4; }
.bld-step-num {
    font-size: 16px; font-weight: 800; color: #5f7370; line-height: 1;
    min-width: 12px;
}
.bld-stepcard.is-current .bld-step-num { color: #e0b46e; }
.bld-stepcard.is-done .bld-step-num { color: #5eead4; }
.bld-step-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.bld-step-label {
    font-size: 12.5px; font-weight: 700; color: #a7b8b4;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.bld-stepcard.is-current .bld-step-label { color: #f2e7d3; }
.bld-step-state {
    font-size: 9.5px; font-weight: 800; letter-spacing: .8px;
    text-transform: uppercase; color: #6d817d; white-space: nowrap;
}
.bld-stepcard.is-current .bld-step-state { color: #e0b46e; }
.bld-stepcard.is-done .bld-step-state { color: #5eead4; }

/* ——— Zona kerja: tipografi langkah ——— */
.st-key-build-work h3 {
    color: #f2f6f5; font-size: 1.06rem; font-weight: 800;
    letter-spacing: .2px; margin: .25rem 0 .1rem;
}
.st-key-build-work [data-testid="stCaptionContainer"] { color: #8fa3a0 !important; }
.st-key-build-work [data-testid="stMarkdownContainer"] p { color: #c6d4d1; }

/* ——— Panel proses AI (akumulatif saat pipeline berjalan) ——— */
.bld-procs { display: flex; flex-direction: column; gap: 8px; margin: 4px 0 10px; }
.bld-proc {
    display: flex; gap: 10px; align-items: flex-start;
    background: #101a1c; border: 1px solid rgba(148, 163, 184, .14);
    border-radius: 12px; padding: 9px 12px;
    box-sizing: border-box;
}
.bld-proc-dot {
    width: 9px; height: 9px; border-radius: 50%; margin-top: 4px; flex: 0 0 9px;
    background: #5eead4; box-shadow: 0 0 8px rgba(94, 234, 212, .5);
}
.bld-proc.is-live .bld-proc-dot {
    background: #e0b46e; box-shadow: 0 0 9px rgba(224, 180, 110, .7);
}
.bld-proc.is-fail .bld-proc-dot {
    background: #f87171; box-shadow: 0 0 8px rgba(248, 113, 113, .55);
}
.bld-proc-body { min-width: 0; flex: 1; }
.bld-proc-head { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; }
.bld-proc-stage {
    font-size: 11px; font-weight: 800; letter-spacing: 1px;
    text-transform: uppercase; color: #e0b46e;
}
.bld-proc-role { font-size: 11px; color: #8fa3a0; }
.bld-proc-text {
    font-size: 12px; color: #c6d4d1; line-height: 1.45; margin-top: 3px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden; word-break: break-word;
}

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

/* ——— Panel identitas & berkas (paling kanan) ——— */
.st-key-build-identity { position: sticky; top: 104px; }
.bld-panel {
    background: linear-gradient(168deg, rgba(18, 32, 34, .96), rgba(10, 18, 19, .96));
    border: 1px solid rgba(148, 163, 184, .16);
    border-radius: 18px;
    padding: 18px 18px 16px;
    box-shadow: 0 18px 40px rgba(0, 0, 0, .35);
    box-sizing: border-box;
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
    color: #f4f8f7; font-size: 1.24rem; font-weight: 800;
    line-height: 1.3; margin: 9px 0 13px;
    word-break: break-word;
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
    margin-bottom: 13px;
}
.bld-row span {
    display: block; color: #7f938f; font-size: 11px; font-weight: 800;
    letter-spacing: .9px; text-transform: uppercase; margin-bottom: 3px;
}
.bld-row p {
    margin: 0; color: #d7e2df; font-size: 13px; line-height: 1.5;
    word-break: break-word;
}

/* Berkas & sumber: daftar berkas gaya panel identitas */
.bld-files { display: flex; flex-direction: column; gap: 7px; }
.bld-file {
    display: flex; align-items: center; gap: 9px;
    background: #172224; border: 1px solid rgba(148, 163, 184, .14);
    border-radius: 11px; padding: 9px 12px;
    text-decoration: none; box-sizing: border-box;
    transition: border-color .15s ease;
}
.bld-file:hover { border-color: rgba(224, 180, 110, .5); }
.bld-file-ico {
    flex: 0 0 13px; width: 13px; height: 16px; position: relative;
    border: 1.5px solid #5eead4; border-radius: 3px;
    background: rgba(94, 234, 212, .08);
}
.bld-file-ico::after {
    content: ""; position: absolute; top: -1.5px; right: -1.5px;
    width: 5px; height: 5px; background: #0e1718;
    border-left: 1.5px solid #5eead4; border-bottom: 1.5px solid #5eead4;
    border-radius: 0 3px 0 2px;
}
.bld-file-name {
    color: #cbd5e1; font-size: 12.5px; font-weight: 600; min-width: 0;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.bld-file:hover .bld-file-name { color: #f0e6d4; }
.bld-files-empty {
    color: #7f938f; font-size: 12.5px; line-height: 1.5;
    background: #172224; border: 1px dashed rgba(148, 163, 184, .22);
    border-radius: 11px; padding: 11px 13px;
}

/* ——— Layar sempit: lepas panel lengket ——— */
@media (max-width: 1000px) {
    .st-key-build-identity { position: static !important; }
    .bld-pill { max-width: 40%; }
}
</style>
"""
