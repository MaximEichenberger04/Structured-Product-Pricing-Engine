from dataclasses import dataclass
from math import isfinite
from typing import Optional

# Product terms and market inputs. All rates are decimals, e.g. 0.12 = 12%.

@dataclass(frozen=True)
class ReverseConvertible:
    """
    Single-underlying reverse convertible.
    barrier=None: plain RC.
    barrier=0.75: barrier at 75% of current spot.
    For an already-issued product, supply reference_spot to keep
    the barrier fixed at a percentage of the original fixing.
    Assumes one unconditional coupon payment at maturity.
    """

    nominal: float
    strike: float
    maturity: float
    coupon_rate: float = 0.0
    barrier: Optional[float] = None
    barrier_breached: bool = False
    coupon_accrual_years: Optional[float] = None
    reference_spot: Optional[float] = None

    def __post_init__(self):
        for name in ("nominal", "strike", "maturity"):
            value = getattr(self, name)

            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive.")

        if not isfinite(self.coupon_rate):
            raise ValueError("coupon_rate must be finite.")

        if self.barrier is not None:
            if not isfinite(self.barrier) or not 0 < self.barrier <= 1:
                raise ValueError("barrier must be a fraction in (0, 1], \ne.g. 0.75 for 75%.")
            
        elif self.barrier_breached:
            raise ValueError("barrier_breached requires a barrier.")

        if self.reference_spot is not None:
            if (not isfinite(self.reference_spot) or self.reference_spot <= 0):
                raise ValueError("reference_spot must be finite and positive.")

        if self.coupon_accrual_years is not None:
            if (not isfinite(self.coupon_accrual_years) or self.coupon_accrual_years <= 0):
                raise ValueError("coupon_accrual_years must be finite and positive.")

    @property
    def accrual_years(self):
        if self.coupon_accrual_years is None:
            return self.maturity

        return self.coupon_accrual_years

    @property
    def coupon_amount(self):
        return self.nominal * self.coupon_rate * self.accrual_years


@dataclass(frozen=True)
class MarketData:
    """
    Rates are decimals, e.g. 0.04 = 4%.
    risk_free_rate and dividend_yield: continuously compounded.
    bond_discount_rate: effective annual issuer discount rate.
    The example uses risk-free rate + CDS spread as a simplified bond discount rate.
    """

    spot: float
    volatility: float
    risk_free_rate: float
    dividend_yield: float
    bond_discount_rate: float

    def __post_init__(self):
        data =  ["spot", "volatility", "risk_free_rate", "dividend_yield", "bond_discount_rate"]
        for name in data:
            if not isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite.")

        if self.spot <= 0 or self.volatility <= 0:
            raise ValueError("spot and volatility must be positive.")

        if self.bond_discount_rate <= -1:
            raise ValueError("bond_discount_rate must exceed -1.")