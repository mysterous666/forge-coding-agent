import unittest

from slug import slugify


class SlugTests(unittest.TestCase):
    def test_words_and_punctuation(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_collapses_separators(self):
        self.assertEqual(slugify("  a___b  "), "a-b")


if __name__ == "__main__":
    unittest.main()
