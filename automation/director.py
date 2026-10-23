"""Generate a distinct daily video brief through AOGx's configured AI router."""
from __future__ import annotations

import json
import re


class DirectorError(RuntimeError):
    pass


SYSTEM_PROMPT = """You are AOGx Autonomous Video Creative Director.
Create one original vertical-video concept from the user's standing instruction.
Reply with JSON only (no Markdown fences), schema:
{
  "concept": "short unique concept",
  "video_prompt": "production-ready video generation prompt",
  "title": "English YouTube Shorts title, <= 90 chars",
  "description": "English description with relevant hashtags",
  "creative_notes": ["3-5 concrete details that make today's video distinct"]
}
Respect the requested duration and aspect ratio. For faceless miniature-building ASMR, describe hands and miniature construction only, tactile materials, crisp natural ASMR, cinematic close-ups, coherent step-by-step construction, and a satisfying final reveal. Avoid fake claims, logos, copyrighted characters, unnecessary text overlays, and repetitive concepts. Do not claim the video has been generated; this output is only its brief and prompt."""


def parse_brief(raw: str) -> dict:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise DirectorError("AI tidak mengembalikan JSON brief yang valid.")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        raise DirectorError("Brief AI tidak dapat dibaca sebagai JSON.") from None
    prompt = str(data.get("video_prompt", "")).strip()
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    if len(prompt) < 80 or not title:
        raise DirectorError("Brief AI tidak memiliki prompt video atau judul yang memadai.")
    notes = data.get("creative_notes", [])
    return {
        "concept": str(data.get("concept", "")).strip()[:300],
        "video_prompt": prompt[:10000], "title": title[:100],
        "description": description[:5000],
        "creative_notes": notes if isinstance(notes, list) else [],
    }


def create_daily_brief(router, instruction: str, run_date: str) -> dict:
    request = (
        f"Standing creator instruction:\n{instruction}\n\nProduction date: {run_date}.\n"
        "Make today's idea meaningfully different from generic prior-day concepts. "
        "Target: 20-second vertical 9:16 YouTube Shorts for an international English-speaking audience. "
        "The prompt must be directly usable by a video-generation provider."
    )
    try:
        raw, _provider = router.chat(
            "expert",
            [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": request}],
            temperature=0.8, max_tokens=1800,
        )
    except Exception as exc:
        raise DirectorError(f"AI Creative Director gagal ({exc.__class__.__name__}).") from None
    return parse_brief(raw)
