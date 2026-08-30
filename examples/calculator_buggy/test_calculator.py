import unittest

from calculator import add


class CalculatorTests(unittest.TestCase):
    def test_adds_positive_numbers(self) -> None:
        self.assertEqual(add(7, 5), 12)

    def test_adds_negative_numbers(self) -> None:
        self.assertEqual(add(-3, -4), -7)


if __name__ == "__main__":
    unittest.main()
