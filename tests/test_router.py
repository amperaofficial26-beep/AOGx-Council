import os
import time
import unittest
from unittest.mock import patch

import config
from core.router import AllProvidersFailed, Router
from providers.base import ProviderError


class FakeProvider:
    def __init__(self, name, reply="ok", error=None, status=None):
        self.name = name
        self.reply = reply
        self.error = error
        self.status = status
        self.calls = 0

    def available(self):
        return True

    def chat(self, model, messages, temperature=0.7, max_tokens=1500):
        self.calls += 1
        if self.error:
            raise ProviderError(self.error, self.status)
        return self.reply

    def list_models(self):
        return ["m1", "m2"]


class RouterTest(unittest.TestCase):
    def make_router(self):
        router = Router()
        router.providers = {}
        router.tavily = type("T", (), {"available": lambda self: False})()
        return router

    def test_fallback_to_next_provider(self):
        router = self.make_router()
        router.providers = {"groq": FakeProvider("groq", error="down", status=500),
                            "gemini": FakeProvider("gemini", reply="halo")}
        with patch.dict(config.ROUTES, {"orchestrator": ["groq", "gemini"]}, clear=False):
            text, used = router.chat("orchestrator", [{"role": "user", "content": "x"}])
        self.assertEqual((text, used), ("halo", "gemini"))

    def test_all_failed_raises_with_role(self):
        router = self.make_router()
        router.providers = {"groq": FakeProvider("groq", error="down", status=500)}
        with patch.dict(config.ROUTES, {"orchestrator": ["groq"]}, clear=False):
            with self.assertRaises(AllProvidersFailed) as ctx:
                router.chat("orchestrator", [{"role": "user", "content": "x"}])
        self.assertIn("orchestrator", str(ctx.exception))

    def test_empty_answer_counts_as_failure(self):
        router = self.make_router()
        router.providers = {"groq": FakeProvider("groq", reply="   "),
                            "gemini": FakeProvider("gemini", reply="isi")}
        with patch.dict(config.ROUTES, {"orchestrator": ["groq", "gemini"]}, clear=False):
            text, used = router.chat("orchestrator", [{"role": "user", "content": "x"}])
        self.assertEqual((text, used), ("isi", "gemini"))

    def test_cooldown_skips_provider(self):
        router = self.make_router()
        bad = FakeProvider("groq", error="limit", status=429)
        router.providers = {"groq": bad, "gemini": FakeProvider("gemini", reply="isi")}
        with patch.dict(config.ROUTES, {"orchestrator": ["groq", "gemini"]}, clear=False):
            router.chat("orchestrator", [{"role": "user", "content": "x"}])
            router.chat("orchestrator", [{"role": "user", "content": "x"}])
        self.assertEqual(bad.calls, 1)  # panggilan kedua dilewati karena jeda
        self.assertTrue(router._is_cooling("groq"))
        self.assertIn("groq", router.last_error)

    def test_cooldown_expires(self):
        router = self.make_router()
        router.providers = {"groq": FakeProvider("groq", reply="pulih")}
        router._cooldown_until["groq"] = time.time() - 1
        with patch.dict(config.ROUTES, {"orchestrator": ["groq"]}, clear=False):
            self.assertEqual(router.chat("orchestrator", [{"role": "user", "content": "x"}])[1], "groq")

    def test_status_400_gets_longer_cooldown(self):
        router = self.make_router()
        router.providers = {"groq": FakeProvider("groq", error="key salah", status=401)}
        with patch.dict(config.ROUTES, {"orchestrator": ["groq"]}, clear=False):
            with self.assertRaises(AllProvidersFailed):
                router.chat("orchestrator", [{"role": "user", "content": "x"}])
        wait = router._cooldown_until["groq"] - time.time()
        self.assertGreater(wait, 100)

    def test_base_url_env_override(self):
        with patch.dict(os.environ, {"AION_BASE_URL": "https://proxy.local/v1"}):
            router = Router()
        self.assertEqual(router.providers["aion"].base_url, "https://proxy.local/v1")

    def test_inactive_provider_without_model(self):
        router = Router()
        self.assertNotIn("xkiro", router.active_providers())  # model kosong = nonaktif

    def test_council_roles_use_gpt_oss_120b_on_groq(self):
        class ModelProvider(FakeProvider):
            def chat(self, model, messages, temperature=0.7, max_tokens=1500):
                self.model = model
                return super().chat(model, messages, temperature, max_tokens)

        router = self.make_router()
        groq = ModelProvider("groq")
        router.providers = {"groq": groq}
        roles = ("council_orchestrator", "council_researcher", "council_synthesizer", "flash")
        for role in roles:
            with patch.dict(config.ROUTES, {role: ["groq"]}, clear=False):
                router.chat(role, [{"role": "user", "content": "uji"}])
            self.assertEqual(groq.model, "openai/gpt-oss-120b", role)

        # Provider alternatif tetap bisa melayani Council jika Groq/Gemini tidak aktif.
        aion = FakeProvider("aion", reply="fallback")
        router.providers = {"aion": aion}
        for role in roles:
            _, used = router.chat(role, [{"role": "user", "content": "uji"}])
            self.assertEqual(used, "aion", role)

        # Rute lama untuk Agent Code tetap mempertahankan model dan kedalaman semula.
        self.assertEqual(config.ROLE_MODELS[("orchestrator", "groq")], "openai/gpt-oss-20b")
        self.assertEqual(config.ROLE_MODELS[("researcher", "groq")], "openai/gpt-oss-20b")
        self.assertEqual(config.MODES["Seimbang"],
                         {"rounds": 2, "verify": True, "max_retries": 1})
        self.assertEqual(config.MODES["Mendalam"],
                         {"rounds": 3, "verify": True, "max_retries": 2})


if __name__ == "__main__":
    unittest.main()
