from dataclasses import dataclass


@dataclass(frozen=True)
class CartLine:
    unit_price: float
    quantity: int
