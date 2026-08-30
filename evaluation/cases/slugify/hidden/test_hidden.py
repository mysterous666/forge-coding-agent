import unittest

from slug import slugify


class HiddenSlugTests(unittest.TestCase):
    def test_accents_are_normalized(self):
        self.assertEqual(slugify("Crème brûlée déjà vu"), "creme-brulee-deja-vu")

    def test_non_latin_characters_are_separators(self):
        self.assertEqual(slugify("alpha中文beta"), "alpha-beta")

    def test_truncation_drops_trailing_separator(self):
        self.assertEqual(slugify("alpha beta", 6), "alpha")

    def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            slugify("x", 0)


if __name__ == "__main__":
    unittest.main()
