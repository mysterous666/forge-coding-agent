import unittest

from merge import deep_merge


class HiddenMergeTests(unittest.TestCase):
    def test_nested_dictionaries_merge(self):
        self.assertEqual(
            deep_merge({"db": {"host": "a", "port": 1}}, {"db": {"port": 2}}),
            {"db": {"host": "a", "port": 2}},
        )

    def test_nested_values_are_not_shared(self):
        base = {"items": [1], "nested": {"x": [2]}}
        override = {"extra": {"y": [3]}}
        result = deep_merge(base, override)
        result["items"].append(9)
        result["nested"]["x"].append(9)
        result["extra"]["y"].append(9)
        self.assertEqual(base, {"items": [1], "nested": {"x": [2]}})
        self.assertEqual(override, {"extra": {"y": [3]}})

    def test_none_and_lists_replace(self):
        self.assertEqual(deep_merge({"x": {"a": 1}, "v": [1]}, {"x": None, "v": [2]}), {"x": None, "v": [2]})


if __name__ == "__main__":
    unittest.main()
