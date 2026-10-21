"""Cek cepat provider mana yang aktif dan benar-benar menjawab.
Jalankan dari folder proyek:  python -m core.selftest
"""
import config
from core.router import Router
from providers.base import ProviderError


def main():
    router = Router()
    print("Provider aktif:", ", ".join(router.active_providers()) or "(tidak ada)")
    print("Tavily:", "aktif" if router.tavily.available() else "tidak aktif")
    for name in router.active_providers():
        try:
            out = router.providers[name].chat(
                config.model_for(name),
                [{"role": "user", "content": "Jawab satu kata: halo"}],
                temperature=0.0, max_tokens=20)
            print(f"[OK]   {name} ({config.model_for(name)}): {out.strip()[:40]}")
        except ProviderError as e:
            print(f"[GAGAL] {name}: {e}")


if __name__ == "__main__":
    main()
