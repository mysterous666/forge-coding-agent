import unittest
from pathlib import Path
from uuid import uuid4

from safe_path import safe_join


class HiddenSafePathTests(unittest.TestCase):
    def make_root(self) -> Path:
        root = Path.cwd() / ".case_tmp" / uuid4().hex
        root.mkdir(parents=True)
        return root

    def test_windows_style_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            safe_join(self.make_root(), "..\\secret.txt")

    def test_windows_drive_and_unc_are_rejected(self):
        root = self.make_root()
        for value in ("C:\\Windows\\win.ini", "\\\\server\\share\\file"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                safe_join(root, value)

    def test_posix_absolute_is_rejected(self):
        with self.assertRaises(ValueError):
            safe_join(self.make_root(), "/etc/passwd")

    def test_prefix_collision_is_rejected(self):
        root = self.make_root() / "work"
        root.mkdir()
        with self.assertRaises(ValueError):
            safe_join(root, "../workspace-evil/file")


if __name__ == "__main__":
    unittest.main()
