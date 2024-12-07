from decimal import ROUND_UP, Decimal

round_map = {
    0: Decimal("0"),
    1: Decimal("0.1"),
    2: Decimal("0.01"),
    3: Decimal("0.001"),
    4: Decimal("0.0001"),
    5: Decimal("0.00001"),
    6: Decimal("0.000001"),
    7: Decimal("0.0000001"),
    8: Decimal("0.00000001"),
}


def rnd(value, decimals, cls=Decimal, rounding=ROUND_UP):
    try:
        return cls(Decimal(str(value)).quantize(round_map.get(decimals), rounding=rounding))
    except Exception as exc:
        raise RuntimeError(f"Error rounding {value} with {decimals} decimals: {exc}")


def abs_diff(v1, v2):
    return abs(v1 - v2)
