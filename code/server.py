import json
from dataclasses import replace
from math import isfinite

from flask import Flask, render_template, request

from definition import MarketData, ReverseConvertible
from pricing_engine import bond_discount_factor, coupon_for_issue_price, implied_volatility_call, price_breakdown


app = Flask(__name__, template_folder=".")


def number(name, optional=False):
    text = request.form.get(name, "").strip()

    if optional and not text:
        return None

    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"{name}: enter a number.") from None

    if not isfinite(value):
        raise ValueError(f"{name}: enter a finite number.")

    return value


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    status = 200

    if request.method == "POST":
        try:
            form = request.form

            # Read market inputs.
            spot = number("spot")
            rate = number("risk_free_rate")
            dividend = number("dividend_yield")

            # Either calibrate volatility or use the entered value.
            if form["volatility_mode"] == "calibrate":
                volatility = implied_volatility_call(number("call_price"), spot, number("call_strike"), number("call_maturity"), rate, dividend)
            elif form["volatility_mode"] == "direct":
                volatility = number("volatility")
            else:
                raise ValueError("Select a valid volatility source.")

            market = MarketData(spot=spot, volatility=volatility, risk_free_rate=rate, dividend_yield=dividend, bond_discount_rate=number("bond_discount_rate"))

            # Read barrier inputs.
            if form["barrier_enabled"] not in ("yes", "no"):
                raise ValueError("Select whether the product has a barrier.")

            has_barrier = form["barrier_enabled"] == "yes"
            barrier = number("barrier") if has_barrier else None
            reference = number("reference_spot", optional=True) if has_barrier else None

            if has_barrier and form["barrier_breached"] not in ("yes", "no"):
                raise ValueError("Select whether the barrier has been breached.")

            breached = has_barrier and form["barrier_breached"] == "yes"

            # A fixed coupon is only needed in valuation mode.
            if form["mode"] not in ("solve", "value"):
                raise ValueError("Select a valid calculation mode.")

            coupon = number("coupon_rate") if form["mode"] == "value" else 0.0

            product = ReverseConvertible(nominal=number("nominal"), strike=number("strike"), maturity=number("maturity"), coupon_rate=coupon, barrier=barrier, barrier_breached=breached, coupon_accrual_years=number("coupon_accrual_years", optional=True), reference_spot=reference)

            issue_price = number("issue_price_fraction")

            if issue_price <= 0:
                raise ValueError("Issue price fraction must be positive.")

            # Solve the coupon if requested.
            margin = number("margin") if form["mode"] == "solve" else None

            if form["mode"] == "solve":
                coupon = coupon_for_issue_price(product, market, margin, issue_price)
                product = replace(product, coupon_rate=coupon)

            # Calculate the product value.
            result = price_breakdown(product, market)

            reference_price = reference if reference is not None else spot
            barrier_price = barrier * reference_price if has_barrier else None
            activated = has_barrier and (breached or spot <= barrier_price)

            # Add intermediate results to the JSON.
            result["volatility"] = volatility
            result["coupon_rate"] = product.coupon_rate
            result["coupon_payment"] = product.coupon_amount
            result["barrier_price"] = barrier_price
            result["barrier_activated"] = activated
            result["conversion_ratio"] = product.nominal / product.strike
            result["option_formula"] = "vanilla put" if not has_barrier or activated else "down-and-in put"
            result["bond_discount_factor"] = bond_discount_factor(product, market)
            result["fair_value_percent"] = result["fair_value_fraction"] * 100
            result["issue_price"] = product.nominal * issue_price
            result["target_value"] = product.nominal * (issue_price - margin) if margin is not None else None
            result["issue_price_minus_fair_value"] = product.nominal * issue_price - result["fair_value"]

            result = json.dumps(result, indent=2, allow_nan=False)

        except (ValueError, TypeError, OverflowError, ZeroDivisionError, RuntimeError) as error:
            result = json.dumps({"error": str(error)}, indent=2)
            status = 400

    return render_template("index.html", result=result), status


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)