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

## Mengatur agen
- `config.py`: model default, rute fallback per peran (`ROUTES`), model khusus per peran (`ROLE_MODELS`),
  mode kedalaman (`MODES`), ambang kualitas, batas pemakaian.
- `agent/`: prompt tiap agen (orchestrator, researcher, debaters, synthesizer, verifier). `core/pipeline.py`: urutan lapisan.
- `ui/`: lapisan tampilan saja — `flow.py` (graf proses: status node + HTML/SVG), `theme.py` (CSS),
  `machine.py` (kubus + panel alur), `demo.py` (router tiruan untuk mode demo). `core/` dan `agent/` tidak tahu-menahu soal UI.
