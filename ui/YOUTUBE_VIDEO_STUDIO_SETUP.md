# AOGx Video Studio — setup

## Batas integrasi Dola

Per 23 Oktober 2026, sumber publik Dola yang diperiksa tidak menunjukkan API publik resmi untuk
mengotomatisasi pembuatan video. Syarat layanan Dola yang ditemukan menyatakan layanan untuk
penggunaan pribadi/non-komersial dan melarang penggunaan otomatis/programatik tertentu. Karena
itu modul ini **tidak mengotomatisasi browser, scraping, atau endpoint internal Dola**. Buat video
di Dola secara manual, unduh hasilnya, lalu gunakan pratinjau/upload YouTube di AOGx. Otomatisasi
Dola hanya boleh ditambahkan jika Dola menyediakan API resmi dan memberi izin untuk use case ini.

## File

- `providers/youtube.py`: OAuth Google dan resumable upload melalui YouTube Data API.
- `ui/video_studio.py`: panel untuk koneksi akun, pratinjau file video, metadata, persetujuan, dan upload.
- `requirements.txt`: dependensi saat ini sudah mencakup `requests`; tidak perlu pustaka Google tambahan.

## Integrasi ke `app.py`

1. Tambahkan import di bagian atas:
   `from ui import video_studio`
2. Di bagian paling bawah, setelah panel GitHub, tambahkan:
   `with left:`
   `    with st.expander("Video Studio · Dola → YouTube Shorts", expanded=False):`
   `        video_studio.render()`

Catatan: panel GitHub saat ini menangani callback OAuth yang punya `code/state`. Callback YouTube
menggunakan state berawalan `yt.`; panel GitHub yang ada mungkin tetap menganggap callback YouTube
sebagai callback GitHub dan menampilkan pesan callback tidak valid. Sebelum deploy, ubah handler
callback GitHub agar hanya memproses state GitHub dan mengabaikan state yang diawali `yt.`. Jangan
gunakan redirect URI yang berbeda dari URI yang didaftarkan di Google Cloud OAuth client.

## Google Cloud / Streamlit Secrets

- Aktifkan **YouTube Data API v3** di Google Cloud project.
- Konfigurasikan OAuth consent screen dan buat OAuth Client ID tipe **Web application**.
- Daftarkan URL aplikasi Streamlit persis sama sebagai Authorized redirect URI, misalnya
  `https://nama-aplikasi.streamlit.app/`.
- Tambahkan ke Streamlit Cloud → App → Settings → Secrets:

  ```toml
  YOUTUBE_CLIENT_ID = "..."
  YOUTUBE_CLIENT_SECRET = "..."
  YOUTUBE_REDIRECT_URI = "https://nama-aplikasi.streamlit.app/"
  ```

- Jangan pernah commit atau membagikan client secret / token.
- Scope yang diminta hanya `youtube.upload`.
- Mode privasi default di panel adalah `public`, sesuai pilihan pemilik aplikasi. Pratinjau dan
  checkbox persetujuan wajib sebelum permintaan upload dilakukan.
- Pengguna harus meninjau hasil video, hak cipta musik/visual, dan pengungkapan konten sintetis
  yang relevan sebelum upload. Pastikan pengaturan privasi dan aturan YouTube sesuai.

## Batasan saat ini

- Pembuatan video Dola masih manual karena tidak ditemukan API publik resmi yang dapat dipastikan
  dan syarat layanan Dola membatasi otomasi.
- Panel menampilkan pratinjau, tetapi tidak otomatis memvalidasi durasi atau rasio 9:16.
- Token disimpan hanya di session state, sehingga koneksi mungkin perlu diulang saat sesi berakhir.
- Google OAuth perlu diuji di deployment nyata; aplikasi OAuth yang belum diverifikasi dapat
  memiliki pembatasan pengguna/tester.
