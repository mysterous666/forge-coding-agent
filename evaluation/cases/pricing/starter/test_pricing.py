import unittest

from models import CartLine
from pricing import total


class PricingTests(unittest.TestCase):
    def test_regular_order_pays_shipping(self):
        self.assertEqual(total([CartLine(20, 2)]), 48)

    def test_large_regular_order_has_free_shipping(self):
        self.assertEqual(total([CartLine(50, 3)]), 150)


if __name__ == "__main__":
    unittest.main()
