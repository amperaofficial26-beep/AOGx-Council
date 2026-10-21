# AOGx-Council

Diskusi multi-agen AI: Orchestrator merencanakan, Researcher (Tavily) mencari sumber, tiga agen
(Analis, Skeptis, Pakar) berdiskusi, Penyusun merangkum, Verifier memberi skor, dan gerbang kualitas
mengulang revisi bila skor di bawah ambang.

## Jalankan lokal
```
pip install -r requirements.txt
cp .env.example .env        # isi key yang kamu punya
python -m core.selftest     # cek provider mana yang aktif
streamlit run app.py
```
(File `.env` dibaca otomatis lewat python-dotenv. Alternatif: `.streamlit/secrets.toml`.)

## Deploy ke Streamlit Cloud
Taruh semua key di Settings > Secrets (format TOML). Tambahkan `APP_ACCESS_CODE = "kode-rahasia"`
agar app hanya bisa dibuka orang yang tahu kodenya. Jangan commit `.env` atau `secrets.toml`.

## Mengatur agen
- `config.py`: model default, rute fallback per peran (`ROUTES`), model khusus per peran (`ROLE_MODELS`),
  mode kedalaman (`MODES`), ambang kualitas, batas pemakaian.
- `agents/`: prompt tiap agen. `core/pipeline.py`: urutan lapisan.
