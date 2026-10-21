from datetime import date
from typing import Tuple

RULES = (
    "Jujur soal ketidakpastian. Jangan mengarang fakta, angka, kutipan, atau sumber. "
    "Gunakan bahasa yang sama dengan pertanyaan pengguna."
)


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
