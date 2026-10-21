import json
import re
from typing import Any, Optional


def extract_json(text: str) -> Optional[dict]:
    """Ambil objek JSON dari jawaban model, walau dibungkus ```json atau teks lain."""
    if not text:
        return None
    t = re.sub(r"```(?:json)?", "", text).strip()
    try:
        data = json.loads(t)
        return data if isinstance(data, dict) else None
    except ValueError:
        pass
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else None
        except ValueError:
            return None
    return None


def clip(text: str, n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n].rstrip() + " …"


def to_score(x: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return default


def str_list(x: Any, limit: int) -> list:
    if not isinstance(x, list):
        return []
    return [str(i).strip() for i in x if str(i).strip()][:limit]
