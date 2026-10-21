"""Konfigurasi pusat AOGx-Council: provider, model, dan rute fallback per peran agen."""
import os

try:  # muat file .env bila python-dotenv terpasang
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_secret(name: str, default: str = "") -> str:
    """Ambil dari environment dulu, lalu st.secrets (untuk Streamlit Cloud)."""
    value = os.environ.get(name)
    if value:
        return value.strip()
    try:
        import streamlit as st
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


# Provider yang kompatibel format OpenAI (/chat/completions).
# Cek ulang base_url dan nama model di dashboard masing-masing provider,
# lalu ubah di sini atau lewat variabel *_MODEL / XKIRO_BASE_URL.
OPENAI_COMPAT = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
    },
    "requesty": {
        "base_url": "https://router.requesty.ai/v1",
        "key": "REQUESTY_API_KEY",
        "model": "openai/gpt-4o-mini",
    },
    "aion": {
        "base_url": "https://api.aionlabs.ai/v1",
        "key": "AION_API_KEY",
        "model": "aion-1.0-mini",
    },
    "xkiro": {
        "base_url": "https://api.xkiro.com/v1",
        "key": "XKIRO_API_KEY",
        # Format ID wajib "vendor/model" (contoh dari docs xKiro). Daftar model aktif:
        # GET https://api.xkiro.com/v1/models. Model yang bisa dipakai tergantung tier akunmu.
        "model": "openai/gpt-5.6-sol",
    },
}

GEMINI = {"key": "GEMINI_API_KEY", "model": "gemini-2.5-flash"}
TAVILY = {"key": "TAVILY_API_KEY"}


def model_for(provider: str) -> str:
    """Model aktif untuk provider (bisa ditimpa lewat env <PROVIDER>_MODEL)."""
    env_name = f"{provider.upper()}_MODEL"
    override = get_secret(env_name)
    if override:
        return override
    if provider == "gemini":
        return GEMINI["model"]
    return OPENAI_COMPAT[provider]["model"]


# Opsional: paksa model tertentu untuk kombinasi (peran, provider).
# Berguna untuk xKiro/OpenRouter yang menyediakan banyak vendor, supaya tiap agen
# memakai "otak" berbeda. Contoh:
#   ("skeptic", "xkiro"): "deepseek/<nama-model>",
#   ("expert", "xkiro"): "anthropic/<nama-model>",
ROLE_MODELS = {}

# Rute fallback per peran: provider pertama dicoba dulu, kalau gagal lanjut ke berikutnya.
# Peran berbeda sengaja diberi provider berbeda supaya sudut pandang model beragam.
ROUTES = {
    "orchestrator": ["groq", "openrouter", "gemini"],
    "researcher":   ["groq", "openrouter", "gemini"],
    "analyst":      ["gemini", "openrouter", "groq"],
    "skeptic":      ["aion", "xkiro", "openrouter", "groq"],
    "expert":       ["openrouter", "requesty", "xkiro", "groq"],
    "verifier":     ["aion", "xkiro", "gemini", "openrouter"],
    "synthesizer":  ["gemini", "openrouter", "groq"],
}

# Mode kedalaman: (putaran diskusi, pakai verifikasi, maks ulang bila skor rendah)
MODES = {
    "Cepat":    {"rounds": 1, "verify": False, "max_retries": 0},
    "Seimbang": {"rounds": 2, "verify": True,  "max_retries": 1},
    "Mendalam": {"rounds": 3, "verify": True,  "max_retries": 2},
}

QUALITY_THRESHOLD = 0.7  # skor verifikasi minimal (0-1) agar jawaban dianggap lolos

# Batas penggunaan (melindungi kuota API kalau app dibuka untuk orang lain)
MAX_QUESTION_CHARS = 3000
MAX_REQUESTS_PER_SESSION = 30
