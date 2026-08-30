import unittest

from duration import parse_duration


class DurationTests(unittest.TestCase):
    def test_combines_hours_and_minutes(self):
        self.assertEqual(parse_duration("1h 30m"), 5400)

    def test_compact_form(self):
        self.assertEqual(parse_duration("2m5s"), 125)


if __name__ == "__main__":
    unittest.main()
