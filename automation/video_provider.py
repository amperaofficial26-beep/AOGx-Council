"""Safe video-provider adapter boundary.

No undocumented Dola endpoint or browser automation is implemented here. Add a
concrete adapter only when the provider officially supports the API and intended
commercial/automated use.
"""
from __future__ import annotations

import os


class ProviderNotReady(RuntimeError):
    pass


class CreditUnavailable(RuntimeError):
    """Provider explicitly reported that credits/quota are unavailable."""


class VideoGenerationError(RuntimeError):
    pass


def generate_video(prompt: str, *, duration_seconds: int = 20, aspect_ratio: str = "9:16") -> dict:
    provider = os.getenv("VIDEO_PROVIDER", "").strip().lower()
    if not provider:
        raise ProviderNotReady(
            "VIDEO_PROVIDER belum dikonfigurasi. Prompt harian tersimpan, tetapi generasi video belum dijalankan."
        )
    if provider == "dola":
        raise ProviderNotReady(
            "Konektor Dola belum aktif: diperlukan API resmi/dokumentasi dan izin otomasi komersial dari Dola."
        )
    raise ProviderNotReady(
        f"Provider '{provider}' belum memiliki adapter resmi di AOGx. Jangan gunakan endpoint tebakan; "
        "tambahkan adapter setelah dokumentasi resmi tersedia."
    )
