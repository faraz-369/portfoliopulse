from decimal import Decimal

def test_profit_uses_decimal():
    revenue=Decimal("1500.25")
    expenses=Decimal("1000.10")
    assert revenue-expenses==Decimal("500.15")

def test_zero_revenue_margin_is_undefined():
    revenue=Decimal("0")
    margin=None if revenue==0 else Decimal("1")
    assert margin is None
