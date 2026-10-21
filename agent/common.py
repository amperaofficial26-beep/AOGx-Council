from datetime import date
from typing import Tuple

from core.utils import extract_json

RULES = (
    "Jujur soal ketidakpastian. Jangan mengarang fakta, angka, kutipan, atau sumber. "
    "Gunakan bahasa yang sama dengan pertanyaan pengguna."
)

JSON_NUDGE = "\n\nPENTING: keluarkan HANYA satu objek JSON valid, tanpa penjelasan atau pagar kode."


def today() -> str:
    return date.today().strftime("%d %B %Y")


def run_agent(router, role: str, system: str, user: str,
              temperature: float = 0.6, max_tokens: int = 1200) -> Tuple[str, str]:
    """Panggil satu agen lewat router. Return (teks, provider)."""
    text, provider = router.chat(
        role,
        [{"role": "system", "content": f"{system}\n\nTanggal hari ini: {today()}."},
         {"role": "user", "content": user}],
        temperature=temperature, max_tokens=max_tokens)
    return text.strip(), provider


def run_json_agent(router, role: str, system: str, user: str, temperature: float = 0.2,
                   max_tokens: int = 500, attempts: int = 2) -> Tuple[dict, str]:
    """Agen yang wajib membalas JSON. Dicoba ulang sekali bila JSON tidak bisa dibaca.

    Return (data atau {}, provider). Tanpa retry, satu jawaban berantakan membuat
    orchestrator memakai rencana default dan verifier memberi skor asal-asalan.
    """
    provider = "-"
    for i in range(max(1, attempts)):
        prompt = user if i == 0 else user + JSON_NUDGE
        text, provider = run_agent(router, role, system, prompt,
                                   temperature=temperature, max_tokens=max_tokens)
        data = extract_json(text)
        if data:
            return data, provider
    return {}, provider
