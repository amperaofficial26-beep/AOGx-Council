# AOGx-Council

Diskusi multi-agen AI: Orchestrator merencanakan, Researcher (Tavily) mencari sumber, tiga agen
(Analis, Skeptis, Pakar) berdiskusi, Penyusun merangkum, Verifier memberi skor, dan gerbang kualitas
mengulang revisi bila skor di bawah ambang.

## Tampilan
Tanpa sidebar. Halaman **AOGx Council** menyediakan chat minimal dengan mode **Normal** (satu putaran
dan verifikasi) dan **Flash** (satu panggilan langsung tanpa putaran/verifikasi). Groq GPT-OSS 120B
diprioritaskan untuk perencanaan, riset, sintesis, dan jawaban Flash. Halaman **AOGx Agent Code**
mempertahankan mode **Seimbang** (dua putaran) dan **Mendalam** (tiga putaran) bersama workspace
proses dan GitHub.

Mesin kanan terdiri dari kubus isometrik untuk 7 agen yang tersambung lewat jaringan hub "State",
plus panel **Alur Council** (START, State, Orchestrator, Researcher / Debat 3 agen, Penyusun,
Verifier, Jawaban final, END). Kubus biru = berjalan, hijau = selesai, merah = gagal, abu-abu =
dilewati; garis beranimasi menunjukkan alur, termasuk putaran ulang diskusi dan lingkaran revisi
`Verifier -> Penyusun`. Di bawahnya ada jejak langkah dan baris ringkasan (mode, putaran, skor,
sumber, durasi, provider).

Belum ada API key? App otomatis masuk **mode demo**: alur yang sama dijalankan dengan teks siap
pakai, tanpa panggilan API. Tombol "Tampilkan di mesin" pada setiap jawaban memutar ulang proses
untuk pertanyaan tersebut. Tema gelap diatur di `.streamlit/config.toml`.

## Halaman BUILD (Tahap 1)
Halaman **AOGx Build** (ikon build di top bar) menjalankan alur bantu-buat-aplikasi dalam 6 langkah:
permintaan satu kalimat -> pilihan aplikasi referensi (AI menawarkan pilihan sesuai permintaan,
pengguna boleh memilih satu, menggabungkan beberapa, atau membiarkan AI menentukan; referensi di
luar daftar juga bisa ditambahkan) -> bentuk aplikasi (Web Application, Streamlit + GitHub, Raw
Source Code, Desktop Application) -> verifikasi limit -> proses -> hasil.

- **Limit**: setiap aksi BUILD menghabiskan satu jatah. Hitungan disimpan di **Supabase**
  (bukan session state) dan direset otomatis setelah 3 hari. Tanpa Supabase, hitungan jatuh ke
  memori proses dan UI menampilkan peringatan. Kalimat konfirmasi yang ditampilkan adalah:
  `tindakan ini akan menghabiskan jatah limit aogx anda,limit akan di reset setelah 3 hari, apakah anda ingin lanjut?`
- **RESEARCH** (Tavily + provider): fitur & cara kerja, kelebihan/kekurangan, keluhan pengguna,
  bug publik, tampilan & navigasi, workflow, teknologi & API. Setiap klaim menyimpan URL sumbernya;
  topik tanpa bukti ditulis "tidak ditemukan" (tidak ada karangan).
- **ANALISIS**: kekurangan, titik sulit pengguna, peluang perbaikan, fitur baru, lalu konsep
  aplikasi alternatif dengan identitas desain sendiri.
- **PRODUCT PLANNING**: nama, konsep, target, fitur inti (versi inti lebih dulu), fitur tambahan
  untuk tahap revisi, UI/UX, struktur halaman, alur, backend/database, integrasi AI, teknologi.
- Tampilan hasil memakai tab Ringkasan/Riset/Analisis/Blueprint/Sumber; gagal proses menawarkan
  "Coba lagi" maksimal 3 percobaan (`BUILD_MAX_REPAIR_ATTEMPTS`).

Tahap berikutnya (belum diaktifkan): agen builder + pemeriksaan statis (Tahap 2), testing
otomatis GitHub Actions (Tahap 3), preview/revisi/manajemen proyek (Tahap 4). Kode hasil build
tidak pernah dijalankan di dalam proses Streamlit; di cloud hanya pemeriksaan statis.

Tabel Supabase untuk jatah (buat sekali di SQL Editor):
```sql
create table if not exists build_limits (
  user_key text primary key,
  build_count integer not null default 0,
  window_start timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

## Jalankan lokal
```
pip install -r requirements.txt
cp env.example .env        # isi key yang kamu punya
python -m core.selftest     # cek provider mana yang aktif
streamlit run app.py
```
(File `.env` dibaca otomatis lewat python-dotenv. Alternatif: `.streamlit/secrets.toml`.)

## Deploy ke Streamlit Cloud
Taruh semua key di Settings > Secrets (format TOML). Tambahkan `APP_ACCESS_CODE = "kode-rahasia"`
agar app hanya bisa dibuka orang yang tahu kodenya. Jangan commit `.env` atau `secrets.toml`.

## Tes
```
python -m unittest discover -s tests -t .   # tanpa butuh API key
```
Termasuk uji jatah BUILD (`tests/test_build_limits.py`) dan pipeline BUILD
(`tests/test_build_pipeline.py`) yang berjalan offline dengan router/tavily palsu.

## Mengatur agen
- `config.py`: model default, rute fallback per peran (`ROUTES`), model khusus per peran (`ROLE_MODELS`),
  mode kedalaman (`MODES`), ambang kualitas, batas pemakaian, rute & batas BUILD.
- `agent/`: prompt tiap agen (orchestrator, researcher, debaters, synthesizer, verifier) plus agen
  BUILD (`build_interview`, `build_research`, `build_analyst`, `build_planner`).
  `core/pipeline.py`: urutan lapisan Council; `build/pipeline.py`: urutan tahap BUILD.
- `ui/`: lapisan tampilan saja — `flow.py` (graf proses: status node + HTML/SVG), `theme.py` (CSS),
  `machine.py` (kubus + panel alur), `demo.py` (router tiruan untuk mode demo),
  `build_page.py` (halaman BUILD). `core/` dan `agent/` tidak tahu-menahu soal UI.
