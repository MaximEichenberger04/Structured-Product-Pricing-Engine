"""
Assumptions:
- European terminal payoff
- Continuous barrier monitoring
- Zero rebate
- Constant volatility, rates and dividend yield
- One coupon payment at maturity
- Simplified credit treatment through the bond discount rate
"""

from math import erfc, exp, isfinite, log, sqrt
from definition import MarketData, ReverseConvertible

# cumulative standard normal distribution: N(x)
def normal_cdf(x):
    return 0.5 * erfc(-x / sqrt(2.0))


def _check_option_inputs(spot, strike, maturity, volatility, rate, dividend_yield):
    inputs = (spot, strike, maturity, volatility, rate, dividend_yield)

    if not all(isfinite(x) for x in inputs):
        raise ValueError("All option inputs must be finite.")

    if min(spot, strike, maturity, volatility) <= 0:
        raise ValueError("spot, strike, maturity and volatility must be positive.")


def black_scholes_call(spot, strike, maturity, volatility, rate, dividend_yield):
    """European call value per share."""

    _check_option_inputs(spot, strike, maturity, volatility, rate, dividend_yield)

    sigma_sqrt_t = volatility * sqrt(maturity)

    d1 = (
        log(spot / strike)
        + (rate - dividend_yield + volatility**2 / 2) * maturity
        ) / sigma_sqrt_t

    d2 = d1 - sigma_sqrt_t

    # Call price for European option
    return (
        spot * exp(-dividend_yield * maturity) * normal_cdf(d1)
        - strike * exp(-rate * maturity) * normal_cdf(d2) )


def black_scholes_put(spot, strike, maturity, volatility, rate, dividend_yield):
    """European put value per share."""

    _check_option_inputs(spot, strike, maturity, volatility, rate, dividend_yield)

    sigma_sqrt_t = volatility * sqrt(maturity)

    d1 = (
        log(spot / strike)
        + (rate - dividend_yield + volatility**2 / 2) * maturity
        ) / sigma_sqrt_t

    d2 = d1 - sigma_sqrt_t

    # Put price for European option
    return (
        strike * exp(-rate * maturity) * normal_cdf(-d2)
        - spot * exp(-dividend_yield * maturity) * normal_cdf(-d1) )


def down_and_in_put(spot, strike, barrier, maturity, volatility, rate, dividend_yield, barrier_breached=False):
    """
    European down-and-in put value per share.
    This low-level formula receives the absolute barrier PRICE.
    embedded_put() converts the product's percentage into that price.
    Supported case: 0 < barrier <= strike.
    Once breached, the option becomes a vanilla put.
    """

    _check_option_inputs(spot, strike, maturity, volatility, rate, dividend_yield)

    if not isfinite(barrier) or not 0 < barrier <= strike:
        raise ValueError("Supported barrier price range: 0 < barrier <= strike.")

    if barrier_breached or spot <= barrier:
        return black_scholes_put(spot, strike, maturity, volatility, rate, dividend_yield)

    z = volatility * sqrt(maturity)

    lam = (
        rate - dividend_yield + volatility**2 / 2
    ) / volatility**2

    x = log(spot / barrier) / z + lam * z
    y = log(barrier / spot) / z + lam * z
    gamma = log(barrier**2 / (spot * strike)) / z + lam * z

    stock_pv = spot * exp(-dividend_yield * maturity)
    strike_pv = strike * exp(-rate * maturity)
    ratio = barrier / spot

    return (
        -stock_pv * normal_cdf(-x)
        + strike_pv * normal_cdf(-x + z)
        + stock_pv
        * ratio ** (2 * lam)
        * (normal_cdf(gamma) - normal_cdf(y))
        - strike_pv
        * ratio ** (2 * lam - 2)
        * (normal_cdf(gamma - z) - normal_cdf(y - z))
    )


def embedded_put(product: ReverseConvertible, market: MarketData):
    """Select the option formula and return its value per share."""

    kwargs = dict(
        spot=market.spot,
        strike=product.strike,
        maturity=product.maturity,
        volatility=market.volatility,
        rate=market.risk_free_rate,
        dividend_yield=market.dividend_yield,
    )

    if product.barrier is None:
        return black_scholes_put(**kwargs)

    if product.reference_spot is None:
        reference_spot = market.spot
    else:
        reference_spot = product.reference_spot

    # Example: 0.75 * 303.13 = 227.3475
    barrier_price = product.barrier * reference_spot

    return down_and_in_put(**kwargs, barrier=barrier_price, barrier_breached=product.barrier_breached,)


def bond_discount_factor(product: ReverseConvertible, market: MarketData):
    return (1 + market.bond_discount_rate) ** (-product.maturity)


def price_breakdown(product: ReverseConvertible, market: MarketData):
    """
    Value the fixed contractual coupon.
    Fair Value = PV(principal + coupon) - (nominal / strike) * embedded put price
    The margin is not subtracted again here.
    """

    discount_factor = bond_discount_factor(product, market)

    principal_pv = product.nominal * discount_factor
    coupon_pv = product.coupon_amount * discount_factor

    put_per_share = embedded_put(product, market)

    embedded_put_value = (product.nominal / product.strike * put_per_share)

    value = principal_pv + coupon_pv - embedded_put_value

    return {
        "principal_pv": principal_pv,
        "coupon_pv": coupon_pv,
        "bond_including_coupon_pv": principal_pv + coupon_pv,
        "put_per_share": put_per_share,
        "embedded_put_value": embedded_put_value,
        "fair_value": value,
        "fair_value_fraction": value / product.nominal,
    }


def fair_value(product: ReverseConvertible, market: MarketData):
    return price_breakdown(product, market)["fair_value"]


def coupon_for_issue_price(product: ReverseConvertible, market: MarketData, margin=0.015, issue_price_fraction=1.0):
    """
    Solve the annual coupon so that:
    FV = nominal * (issue_price_fraction - margin)
    margin is an upfront fraction of nominal, not an annual fee.
    The existing coupon_rate is ignored; the product is not modified.
    A negative calculated coupon is returned without flooring it.
    """

    if not all(isfinite(x) for x in (margin, issue_price_fraction)):
        raise ValueError("Issue price and margin must be finite.")

    if not 0 <= margin < issue_price_fraction:
        raise ValueError("Require 0 <= margin < issue_price_fraction.")

    discount_factor = bond_discount_factor(product, market)

    embedded_put_value = (
        product.nominal
        / product.strike
        * embedded_put(product, market)
    )

    target_value = (product.nominal * (issue_price_fraction - margin))

    coupon_amount = (
        (target_value + embedded_put_value) / discount_factor
        - product.nominal
    )

    coupon = coupon_amount / (product.nominal * product.accrual_years)

    return coupon


def implied_volatility_call(call_price, spot, strike, maturity, rate, dividend_yield, price_tolerance=1e-10, max_iterations=200):
    """
    Calibrate volatility to a European call using bisection.
    Applying the result to a different strike or maturity assumes
    a flat volatility surface. American options may require an
    American-option model.
    """

    _check_option_inputs(spot, strike, maturity, 1.0, rate, dividend_yield)

    if (not isfinite(call_price) or not isfinite(price_tolerance) or price_tolerance <= 0):
        raise ValueError("Price must be finite and tolerance finite and positive.")

    if (not isinstance(max_iterations, int) or max_iterations <= 0):
        raise ValueError("max_iterations must be a positive integer.")

    # European call no-arbitrage price bounds.
    lower_bound = max( # ct, Ct
        spot * exp(-dividend_yield * maturity)
        - strike * exp(-rate * maturity),
        0.0)

    upper_bound = spot * exp(-dividend_yield * maturity) # Pt

    # sanity check that bound holds
    if not lower_bound < call_price < upper_bound:
        raise ValueError(
            "Call price must lie strictly between its "
            "European no-arbitrage bounds.")

    low = 0.0
    high = 1.0

    while black_scholes_call(spot, strike, maturity, high, rate, dividend_yield) < call_price:
        high *= 2

        if high > 128:
            raise ValueError(
                "Could not bracket implied volatility.")

    for _ in range(max_iterations):
        mid = (low + high) / 2

        model_price = black_scholes_call(spot, strike, maturity, mid, rate, dividend_yield)

        if abs(model_price - call_price) <= price_tolerance:
            return mid

        if model_price < call_price:
            low = mid
        else:
            high = mid

    raise RuntimeError("Implied volatility did not converge.")