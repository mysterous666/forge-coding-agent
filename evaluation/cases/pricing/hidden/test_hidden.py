import unittest

from models import CartLine
from pricing import total


class HiddenPricingTests(unittest.TestCase):
    def test_loyalty_is_percentage_not_flat_discount(self):
        self.assertEqual(total([CartLine(20, 2)], True), 44)

    def test_discount_is_applied_before_shipping_threshold(self):
        self.assertEqual(total([CartLine(40, 3)], True), 108)

    def test_exact_discounted_threshold_has_free_shipping(self):
        self.assertEqual(total([CartLine(50, 2), CartLine(11.111, 1)], True), 100.0)

    def test_money_is_rounded(self):
        self.assertEqual(total([CartLine(10.005, 1)], False), 18.01)


if __name__ == "__main__":
    unittest.main()
