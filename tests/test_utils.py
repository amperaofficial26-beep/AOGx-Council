import unittest

from core.utils import clip, extract_json, str_list, to_score


class ExtractJsonTest(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(extract_json('{"score": 0.8}'), {"score": 0.8})

    def test_fenced_json(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_json_inside_prose(self):
        self.assertEqual(extract_json('Hasilnya: {"a": 1} selesai.'), {"a": 1})

    def test_rejects_non_object_and_garbage(self):
        self.assertIsNone(extract_json("[1, 2, 3]"))
        self.assertIsNone(extract_json("tidak ada json"))
        self.assertIsNone(extract_json(""))


class HelpersTest(unittest.TestCase):
    def test_clip_short_text_untouched(self):
        self.assertEqual(clip("halo", 10), "halo")

    def test_clip_truncates_with_ellipsis(self):
        out = clip("x" * 50, 10)
        self.assertEqual(len(out), 12)
        self.assertTrue(out.endswith("…"))

    def test_clip_handles_none(self):
        self.assertEqual(clip(None, 5), "")

    def test_to_score_clamps_and_defaults(self):
        self.assertEqual(to_score(1.7), 1.0)
        self.assertEqual(to_score(-2), 0.0)
        self.assertEqual(to_score("0.4"), 0.4)
        self.assertEqual(to_score("bukan angka"), 0.5)
        self.assertEqual(to_score(None, 0.2), 0.2)

    def test_str_list_filters_and_limits(self):
        self.assertEqual(str_list(["a", " ", "b", "c"], 2), ["a", "b"])
        self.assertEqual(str_list("bukan list", 3), [])
        self.assertEqual(str_list([1, 2], 5), ["1", "2"])


if __name__ == "__main__":
    unittest.main()
