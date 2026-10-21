# AOGx-Council

Diskusi multi-agen AI: Orchestrator merencanakan, Researcher (Tavily) mencari sumber, tiga agen
(Analis, Skeptis, Pakar) berdiskusi, Penyusun merangkum, Verifier memberi skor, dan gerbang kualitas
mengulang revisi bila skor di bawah ambang.

## Tampilan
Layout dua area: **kiri** chat (riwayat + unduh jawaban), **kanan** kanvas proses yang menyala
langsung saat agen bekerja — node biru = berjalan, hijau = selesai, merah = gagal, abu-abu bergaris
= tahap yang dilewati; tepi garis beranimasi menunjukkan alur, termasuk putaran ulang diskusi dan
lingkaran revisi `Verifier -> Penyusun`. Di bawah kanvas ada jejak langkah (siapa bicara, lewat
provider mana, berapa lama) dan baris ringkasan (mode, putaran, skor, sumber, durasi, provider).

Belum ada API key? Nyalakan **Mode demo** di sidebar: alur yang sama dijalankan dengan teks siap
pakai, tanpa panggilan API. Tombol "🧠 Tampilkan proses ini di kanvas" pada setiap jawaban
memutar ulang kanvas untuk pertanyaan tersebut.

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
  `demo.py` (router tiruan untuk mode demo). `core/` dan `agent/` tidak tahu-menahu soal UI.
