import unittest

from duration import parse_duration


class HiddenDurationTests(unittest.TestCase):
    def test_units_can_be_reordered(self):
        self.assertEqual(parse_duration("5s 1h"), 3605)

    def test_repeated_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_duration("1h 2h")

    def test_trailing_junk_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_duration("1h later")

    def test_negative_and_empty_are_rejected(self):
        for value in ("-1h", "", "   "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_duration(value)


if __name__ == "__main__":
    unittest.main()
