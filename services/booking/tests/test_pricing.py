from decimal import Decimal

import pytest

from pricing import final_price, surcharge_rate


@pytest.mark.parametrize("temp,rate", [
    (20, "0"), (18, "0"), (22, "0"),          # diff 0-2
    (23, "0.10"), (17, "0.10"), (25, "0.10"),  # diff 3-5
    (26, "0.20"), (14, "0.20"), (30, "0.20"),  # diff 6-10
    (31, "0.30"), (9, "0.30"), (0, "0.30"),    # diff 11-20
    (-1, "0.50"), (41, "0.50"), (-5, "0.50"),  # diff 21+
])
def test_surcharge_tiers_at_boundaries(temp, rate):
    assert surcharge_rate(temp) == Decimal(rate)


def test_final_price():
    assert final_price(140, 20) == Decimal("140.00")
    assert final_price(140, 26) == Decimal("168.00")
    assert final_price(99.99, 35) == Decimal("129.99")  # 99.99 * 1.3 = 129.987
    assert final_price(100, -5) == Decimal("150.00")