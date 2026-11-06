"""Run: python input.py (keep definition.py and pricing_engine.py alongside).
Reproduces the workbook's issuance assumptions as of 2 November 2026,
with corrected d1 calibration. Inputs are supplied assumptions, not live quotes.
"""

from dataclasses import replace
from datetime import date

from definition import MarketData, ReverseConvertible
from pricing_engine import coupon_for_issue_price, implied_volatility_call, price_breakdown


def main():
    valuation_date, option_expiry, product_maturity = date(2026, 11, 2), date(2027, 9, 17), date(2027, 11, 2)
    option_years = (option_expiry - valuation_date).days / 365
    product_years = (product_maturity - valuation_date).days / 365

    spot, rate, dividend_yield, cds_spread = 303.13, 0.04416, 0.0373, 0.004739
    volatility = implied_volatility_call(call_price=32.25, spot=spot, strike=300, maturity=option_years, rate=rate, dividend_yield=dividend_yield)
    # The annual bond rate below retains the workbook's r + CDS approximation.
    market = MarketData(spot=spot, volatility=volatility, risk_free_rate=rate, dividend_yield=dividend_yield, bond_discount_rate=rate + cds_spread)
    brc = ReverseConvertible(nominal=1000, strike=spot, maturity=product_years, barrier=0.70)
    plain_rc = replace(brc, barrier=None)
    # For later revaluation, retain the original fixing explicitly:
    # issued_brc = replace(brc, reference_spot=market.spot)
    print(f"Calibrated volatility: {volatility:.8%}")

    for name, product in [("Barrier RC", brc), ("Plain RC", plain_rc)]:
        coupon = coupon_for_issue_price(product, market, margin=0.015)
        issued_product = replace(product, coupon_rate=coupon)
        result = price_breakdown(issued_product, market)
        print(f"\n{name}")
        print(f"Annual coupon:             {coupon:.8%}")
        print(f"Coupon payment:            {issued_product.coupon_amount:.6f}")
        print(f"PV principal plus coupon:  {result['bond_including_coupon_pv']:.6f}")
        print(f"Embedded put liability:    {result['embedded_put_value']:.6f}")
        print(f"Fair value:                {result['fair_value']:.6f}")
        print(f"Fair value / nominal:      {result['fair_value_fraction']:.6%}")

    # Independent valuation of a fixed coupon, instead of solving a new coupon.
    fixed_coupon_brc = replace(brc, coupon_rate=0.1175531634888307)
    result = price_breakdown(fixed_coupon_brc, market)
    print(f"\nBRC with original fixed coupon: {result['fair_value']:.6f}")


if __name__ == "__main__":
    main()