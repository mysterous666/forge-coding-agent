from models import CartLine


def total(lines: list[CartLine], loyalty_member: bool = False) -> float:
    merchandise = sum(line.unit_price * line.quantity for line in lines)
    if loyalty_member:
        merchandise -= 10
    shipping = 0 if merchandise > 100 else 8
    return merchandise + shipping
