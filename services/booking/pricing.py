"""Weather-based pricing rule (Assessment 1, section 2.4).

final price = base price x (1 + s), where s depends on |T - 20|:
  0-2 -> 0%, 3-5 -> 10%, 6-10 -> 20%, 11-20 -> 30%, 21+ -> 50%
"""
from decimal import ROUND_HALF_UP, Decimal

TARGET_TEMP = 20
TIERS = [(2, Decimal("0")), (5, Decimal("0.10")), (10, Decimal("0.20")), (20, Decimal("0.30"))]
TOP_RATE = Decimal("0.50")


def surcharge_rate(temperature):
    diff = abs(int(temperature) - TARGET_TEMP)
    for upper, rate in TIERS:
        if diff <= upper:
            return rate
    return TOP_RATE


def final_price(base_price, temperature):
    base = Decimal(str(base_price))
    total = base * (1 + surcharge_rate(temperature))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
