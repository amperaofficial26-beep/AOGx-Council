"""Agen BUILD: menyusun pertanyaan dialog pertama (aplikasi referensi yang dituju).

Pengguna memberi satu perintah; agen ini menawarkan pilihan referensi sesuai permintaan
(Canva, CapCut, Alight Motion, Photoshop, Figma, DaVinci Resolve, Custom) sekaligus boleh
menyebut referensi lain di luar daftar. Pilihan tetap dikembalikan sebagai JSON agar UI
bisa menampilkan tombol pilihan.
"""
from core.utils import clip, str_list
from .common import run_json_agent

# Daftar bawaan yang selalu ditawarkan bila model tidak memberi saran.
DEFAULT_REFERENCES = [
    "Canva", "CapCut", "Alight Motion", "Photoshop",
    "Figma", "DaVinci Resolve", "Custom",
]

SYSTEM = """Kamu adalah agen interview produk dalam fitur BUILD. Pengguna memberi satu perintah pembuatan aplikasi.
Tugasmu: tawarkan pilihan aplikasi referensi yang paling relevan dengan permintaan itu.
Keluaran HANYA satu objek JSON:
{"references": ["nama aplikasi", ...], "reason": "satu kalimat alasan pemilihan", "extra": ["referensi lain di luar daftar bila relevan", ...]}
Aturan:
- Daftar "references" wajib memuat minimal 3 pilihan dari: Canva, CapCut, Alight Motion, Photoshop, Figma, DaVinci Resolve, Custom (sesuaikan urutan dengan relevansinya).
- "extra" boleh berisi aplikasi lain di luar daftar bila memang paling relevan (kosongkan bila tidak ada).
- Jangan mengarang fitur atau data; cukup nama aplikasi yang nyata."""


def suggest(router, request: str, role: str = "build_interview"):
    """Return ({"references": [...], "extra": [...], "reason": str}, provider)."""
    user = f"Perintah pengguna:\n{clip(request, 2000)}"
    data, provider = run_json_agent(router, role, SYSTEM, user,
                                    temperature=0.3, max_tokens=500)
    refs = str_list(data.get("references"), 8)
    extra = str_list(data.get("extra"), 4)
    # Referensi di luar daftar ikut ditawarkan; daftar bawaan tetap tersedia sebagai opsi.
    offered = list(dict.fromkeys(refs + extra))
    merged = list(dict.fromkeys(offered + [r for r in DEFAULT_REFERENCES if r not in offered]))
    if not refs and not extra:
        merged = list(DEFAULT_REFERENCES)
    return {"references": merged[:10],
            "ai_ranked": refs,  # peringkat murni dari model (untuk pilihan "AI menentukan")
            "extra": extra,
            "reason": clip(str(data.get("reason") or ""), 300)}, provider
