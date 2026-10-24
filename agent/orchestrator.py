from core.utils import clip, str_list
from .common import run_json_agent

SYSTEM = """Kamu adalah Orchestrator dalam sistem multi-agen. Tugasmu menganalisis pertanyaan pengguna dan merencanakan cara menanganinya.
Keluarkan HANYA satu objek JSON (tanpa teks lain) dengan kunci:
- "category": salah satu "fakta", "analisis", "kode", "kreatif", "opini", "lainnya"
- "complexity": "simple" (sapaan atau pertanyaan singkat dengan jawaban jelas), "medium", atau "complex"
- "needs_web": true bila butuh informasi terkini/spesifik yang bisa berubah (berita, harga, hukum, versi, jabatan saat ini)
- "search_queries": maksimal 2 query pencarian singkat (kosong bila needs_web false)
- "focus_points": 2-4 hal kunci yang harus dibahas agar jawaban akurat"""

DEFAULT = {"category": "lainnya", "complexity": "medium", "needs_web": False,
           "search_queries": [], "focus_points": []}


def plan(router, question: str, history: str, role: str = "orchestrator"):
    user = f"Riwayat singkat:\n{history or '(kosong)'}\n\nPertanyaan:\n{clip(question, 3000)}"
    try:
        data, provider = run_json_agent(router, role, SYSTEM, user,
                                        temperature=0.2, max_tokens=400)
    except Exception:
        return dict(DEFAULT), "-"
    result = dict(DEFAULT)
    result["category"] = str(data.get("category", "lainnya"))
    if data.get("complexity") in ("simple", "medium", "complex"):
        result["complexity"] = data["complexity"]
    result["needs_web"] = bool(data.get("needs_web", False))
    result["search_queries"] = str_list(data.get("search_queries"), 2)
    result["focus_points"] = str_list(data.get("focus_points"), 4)
    return result, provider
