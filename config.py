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
# Nama model sering berubah: pakai tombol "Cari ID model" di sidebar untuk melihat
# ID yang valid, lalu timpa lewat variabel <PROVIDER>_MODEL di Secrets.
OPENAI_COMPAT = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key": "GROQ_API_KEY",
        "model": "openai/gpt-oss-120b",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.3-70b-instruct",
    },
    "requesty": {
        "base_url": "https://router.requesty.ai/v1",
        "key": "REQUESTY_API_KEY",
        "model": "openai/gpt-4o-mini",
    },
    "aion": {
        "base_url": "https://api.aionlabs.ai/v1",
        "key": "AION_API_KEY",
        "model": "aion-labs/aion-3.0-mini",
    },
    "xkiro": {
        "base_url": "https://api.xkiro.com/v1",
        "key": "XKIRO_API_KEY",
        # Kosong = provider nonaktif sampai kamu mengisi XKIRO_MODEL (format "vendor/model").
        # Model "premium" butuh paket berbayar/saldo asli; pilih model non-premium dari
        # tombol "Cari ID model" di sidebar.
        "model": "",
    },
}

GEMINI = {"key": "GEMINI_API_KEY", "model": "gemini-3.8-flash"}
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


# Pilihan model per peran/provider. Agent Code mempertahankan rute cepat 20B;
# peran Council memakai GPT-OSS 120B secara eksplisit.
ROLE_MODELS = {
    ("orchestrator", "groq"): "openai/gpt-oss-20b",
    ("researcher", "groq"): "openai/gpt-oss-20b",
    ("council_orchestrator", "groq"): "openai/gpt-oss-120b",
    ("council_researcher", "groq"): "openai/gpt-oss-120b",
    ("council_synthesizer", "groq"): "openai/gpt-oss-120b",
    ("flash", "groq"): "openai/gpt-oss-120b",
}

# Rute fallback per peran: provider pertama dicoba dulu, kalau gagal lanjut ke berikutnya.
ROUTES = {
    "orchestrator": ["groq", "openrouter", "gemini"],
    "researcher":   ["groq", "openrouter", "gemini"],
    "analyst":      ["gemini", "openrouter", "groq"],
    "skeptic":      ["aion", "xkiro", "openrouter", "groq"],
    "expert":       ["openrouter", "requesty", "xkiro", "groq"],
    "verifier":     ["aion", "xkiro", "gemini", "openrouter"],
    "synthesizer":  ["gemini", "openrouter", "groq"],
    "council_orchestrator": ["groq", "openrouter", "gemini", "requesty", "aion", "xkiro"],
    "council_researcher":   ["groq", "openrouter", "gemini", "requesty", "aion", "xkiro"],
    "council_synthesizer":  ["groq", "gemini", "openrouter", "requesty", "aion", "xkiro"],
    "flash":                ["groq", "openrouter", "gemini", "requesty", "aion", "xkiro"],
}

# Mode pipeline: putaran diskusi, verifikasi, dan batas percobaan revisi.
# Normal satu putaran; Flash langsung menjawab dalam satu panggilan tanpa putaran/verifikasi.
MODES = {
    "Normal":   {"rounds": 1, "verify": True,  "max_retries": 0},
    "Flash":    {"rounds": 0, "verify": False, "max_retries": 0},
    "Cepat":    {"rounds": 1, "verify": False, "max_retries": 0},
    "Seimbang": {"rounds": 2, "verify": True,  "max_retries": 1},
    "Mendalam": {"rounds": 3, "verify": True,  "max_retries": 2},
}

QUALITY_THRESHOLD = 0.7  # skor verifikasi minimal (0-1) agar jawaban dianggap lolos

# Batas penggunaan (melindungi kuota API kalau app dibuka untuk orang lain)
MAX_QUESTION_CHARS = 3000
MAX_REQUESTS_PER_SESSION = 30
