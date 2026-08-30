import unittest

from string_utils import reverse_string, count_vowels, capitalize_words


class StringUtilsTests(unittest.TestCase):
    def test_reverse_string(self) -> None:
        self.assertEqual(reverse_string("hello"), "olleh")

    def test_reverse_string_empty(self) -> None:
        self.assertEqual(reverse_string(""), "")

    def test_count_vowels_lowercase(self) -> None:
        self.assertEqual(count_vowels("hello"), 2)

    def test_count_vowels_uppercase(self) -> None:
        # 'Apple' has two vowels: A, e — both should be counted.
        self.assertEqual(count_vowels("Apple"), 2)

    def test_capitalize_words(self) -> None:
        self.assertEqual(capitalize_words("hello world"), "Hello World")


if __name__ == "__main__":
    unittest.main()