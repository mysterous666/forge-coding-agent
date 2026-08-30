import unittest
from pathlib import Path
from uuid import uuid4

from safe_path import safe_join


class SafePathTests(unittest.TestCase):
    def make_root(self) -> Path:
        root = Path.cwd() / ".case_tmp" / uuid4().hex
        root.mkdir(parents=True)
        return root

    def test_nested_relative_path(self):
        root = self.make_root()
        self.assertEqual(safe_join(root, "src/app.py"), (root / "src/app.py").resolve())

    def test_parent_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            safe_join(self.make_root(), "../secret.txt")


if __name__ == "__main__":
    unittest.main()
