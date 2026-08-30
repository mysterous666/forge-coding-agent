# Pricing rules

- A line subtotal is `unit_price * quantity`.
- Loyalty members receive 10% off the complete merchandise subtotal.
- Convert input prices from their decimal string representation and use decimal arithmetic rather than binary floating-point arithmetic.
- Round the discounted merchandise total to two decimal places with `ROUND_HALF_UP` before comparing it with the shipping threshold.
- Shipping is free when that rounded discounted merchandise total is at least 100; otherwise shipping costs 8.
- Return the final amount rounded to two decimal places with `ROUND_HALF_UP` as a `float`.
