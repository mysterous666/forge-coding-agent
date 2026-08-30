import unittest

from merge import deep_merge


class MergeTests(unittest.TestCase):
    def test_top_level_override(self):
        self.assertEqual(deep_merge({"a": 1}, {"a": 2}), {"a": 2})

    def test_preserves_unique_keys(self):
        self.assertEqual(deep_merge({"a": 1}, {"b": 2}), {"a": 1, "b": 2})


if __name__ == "__main__":
    unittest.main()
