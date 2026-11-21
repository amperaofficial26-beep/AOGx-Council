"""Uji jatah BUILD (build/limits.py): jendela 3 hari, batas, dan penyimpanan Supabase."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from build import limits as bl


class MemoryStoreTest(unittest.TestCase):
    def test_confirm_text_is_exact(self):
        # Kalimat verifikasi wajib persis sesuai spesifikasi fitur BUILD.
        self.assertEqual(
            bl.LIMIT_CONFIRM_TEXT,
            "tindakan ini akan menghabiskan jatah limit aogx anda,"
            "limit akan di reset setelah 3 hari, apakah anda ingin lanjut?",
        )

    def test_consume_increments_and_status_reads(self):
        store = bl.MemoryLimitStore()
        now = datetime(2026, 11, 20, tzinfo=timezone.utc)
        first = bl.limit_consume("u1", store=store, now=now, max_builds=3)
        self.assertTrue(first["consumed"])
        self.assertEqual(first["used"], 1)
        second = bl.limit_consume("u1", store=store, now=now, max_builds=3)
        self.assertEqual(second["used"], 2)
        status = bl.limit_status("u1", store=store, now=now, max_builds=3)
        self.assertEqual(status["used"], 2)
        self.assertEqual(status["remaining"], 1)

    def test_limit_blocks_at_max(self):
        store = bl.MemoryLimitStore()
        now = datetime(2026, 11, 20, tzinfo=timezone.utc)
        for _ in range(3):
            self.assertTrue(bl.limit_consume("u1", store=store, now=now,
                                             max_builds=3)["consumed"])
        blocked = bl.limit_consume("u1", store=store, now=now, max_builds=3)
        self.assertFalse(blocked["consumed"])
        self.assertEqual(blocked["used"], 3)
        self.assertEqual(blocked["remaining"], 0)

    def test_window_resets_after_three_days(self):
        store = bl.MemoryLimitStore()
        t0 = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
        for _ in range(3):
            bl.limit_consume("u1", store=store, now=t0, max_builds=3)
        self.assertFalse(bl.limit_consume("u1", store=store, now=t0,
                                          max_builds=3)["consumed"])
        # Kurang dari 3 hari: masih terblokir.
        later = t0 + timedelta(days=2, hours=23)
        self.assertFalse(bl.limit_consume("u1", store=store, now=later,
                                          max_builds=3)["consumed"])
        # Lewat 3 hari: jatah reset otomatis.
        after = t0 + timedelta(days=3)
        fresh = bl.limit_consume("u1", store=store, now=after, max_builds=3)
        self.assertTrue(fresh["consumed"])
        self.assertEqual(fresh["used"], 1)

    def test_reset_at_is_reported(self):
        store = bl.MemoryLimitStore()
        t0 = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
        status = bl.limit_consume("u1", store=store, now=t0, max_builds=3)
        self.assertIsNotNone(status.get("reset_at"))
        reset = datetime.fromisoformat(status["reset_at"])
        self.assertEqual(reset, t0 + timedelta(days=bl.RESET_DAYS))

    def test_users_are_isolated(self):
        store = bl.MemoryLimitStore()
        now = datetime(2026, 11, 20, tzinfo=timezone.utc)
        bl.limit_consume("a", store=store, now=now, max_builds=1)
        other = bl.limit_consume("b", store=store, now=now, max_builds=1)
        self.assertTrue(other["consumed"])


class SupabaseStoreTest(unittest.TestCase):
    def test_get_store_without_config_returns_none(self):
        with patch.object(bl.config, "get_secret", return_value=""):
            self.assertIsNone(bl.get_store())

    def test_load_uses_postgrest_filter(self):
        store = bl.SupabaseLimitStore("https://proj.supabase.co", "service-key")
        response = MagicMock(status_code=200)
        response.json.return_value = [{"user_key": "gh:budi", "build_count": 2,
                                       "window_start": "2026-11-19T00:00:00+00:00"}]
        with patch.object(bl.requests, "get", return_value=response) as get:
            row = store.load("gh:budi")
        self.assertEqual(row["build_count"], 2)
        url = get.call_args.args[0]
        self.assertIn("/rest/v1/build_limits?", url)
        self.assertIn("user_key=eq.gh%3Abudi", url)
        self.assertEqual(get.call_args.kwargs["headers"]["apikey"], "service-key")

    def test_save_posts_upsert_payload(self):
        store = bl.SupabaseLimitStore("https://proj.supabase.co", "service-key")
        response = MagicMock(status_code=201)
        with patch.object(bl.requests, "post", return_value=response) as post:
            store.save({"user_key": "u", "build_count": 1,
                        "window_start": "2026-11-20T00:00:00+00:00"})
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["user_key"], "u")
        self.assertEqual(payload["build_count"], 1)
        self.assertIn("merge-duplicates", post.call_args.kwargs["headers"]["Prefer"])

    def test_http_error_raises_limit_store_error(self):
        store = bl.SupabaseLimitStore("https://proj.supabase.co", "k")
        response = MagicMock(status_code=404)
        with patch.object(bl.requests, "get", return_value=response):
            with self.assertRaises(bl.LimitStoreError):
                store.load("u")

    def test_status_falls_back_to_memory_when_supabase_down(self):
        store = bl.SupabaseLimitStore("https://proj.supabase.co", "k")
        user = "gh:down-user"  # kunci unik agar tidak terpengaruh uji lain
        with patch.object(bl.requests, "get",
                          side_effect=bl.requests.RequestException("mati")):
            status = bl.limit_status(user, store=store, now=datetime.now(timezone.utc))
        self.assertIsNotNone(status["error"])
        self.assertEqual(status["used"], 0)  # tidak ada data lama: dianggap belum terpakai
        # Konsumsi saat Supabase gagal tetap tercatat di memori proses.
        with patch.object(bl.requests, "post",
                          side_effect=bl.requests.RequestException("mati")), \
             patch.object(bl.requests, "get",
                          side_effect=bl.requests.RequestException("mati")):
            result = bl.limit_consume(user, store=store, now=datetime.now(timezone.utc))
        self.assertTrue(result["consumed"])
        self.assertIsNotNone(result["error"])
        with patch.object(bl.requests, "get",
                          side_effect=bl.requests.RequestException("mati")):
            again = bl.limit_status(user, store=store, now=datetime.now(timezone.utc))
        self.assertEqual(again["used"], 1)  # cadangan memori tetap menghitung

    def test_consume_via_supabase_saves_row(self):
        store = bl.SupabaseLimitStore("https://proj.supabase.co", "k")
        get_resp = MagicMock(status_code=200)
        get_resp.json.return_value = []
        post_resp = MagicMock(status_code=201)
        now = datetime(2026, 11, 20, tzinfo=timezone.utc)
        with patch.object(bl.requests, "get", return_value=get_resp), \
             patch.object(bl.requests, "post", return_value=post_resp) as post:
            result = bl.limit_consume("u1", store=store, now=now, max_builds=5)
        self.assertTrue(result["consumed"])
        self.assertEqual(result["backend"], "supabase")
        self.assertEqual(post.call_args.kwargs["json"]["build_count"], 1)

    def test_invalid_table_name_rejected(self):
        with self.assertRaises(bl.LimitStoreError):
            bl.SupabaseLimitStore("https://x.supabase.co", "k", table="bad-name;drop")

    def test_default_max_builds_env_override(self):
        with patch.object(bl.config, "get_secret", return_value="4"):
            self.assertEqual(bl.default_max_builds(), 4)
        with patch.object(bl.config, "get_secret", return_value="abc"):
            self.assertEqual(bl.default_max_builds(), bl.DEFAULT_MAX_BUILDS)


class UserKeyTest(unittest.TestCase):
    def test_prefers_github_login(self):
        from ui.build_page import resolve_user_key
        ss = {"gh_oauth_user": {"login": "Budi"}}
        self.assertEqual(resolve_user_key(ss), "gh:budi")

    def test_falls_back_to_session_anon_id(self):
        from ui.build_page import resolve_user_key
        ss = {}
        key = resolve_user_key(ss)
        self.assertTrue(key.startswith("anon:"))
        self.assertEqual(resolve_user_key(ss), key)  # stabil dalam sesi yang sama


if __name__ == "__main__":
    unittest.main()
