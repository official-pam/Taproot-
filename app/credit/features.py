"""Turn a business's everyday records into credit features.

Pure functions: no database, no network, no language model. Inputs are the
trader ledger (``app.trade.ledger.Entry``) plus optional alternative data the
owner has agreed to share (àjọ/esusu contributions, utility and airtime
payments, mobile-money inflows).

Farm income is lumpy: a maize farmer may earn most of the year's money in two
months. So for farmers we judge consistency over the season, not month by
month, and we never punish an empty dry-season month on its own.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from statistics import mean, pstdev

from app.trade.ledger import Entry

ZERO = Decimal("0")

BUSINESS_TYPES = ("trader", "farmer", "manufacturer")


@dataclass
class Contribution:
    """One àjọ/esusu (rotating savings group) contribution."""

    day: date
    amount: Decimal
    on_time: bool = True


@dataclass
class AltData:
    """Consented alternative data beyond the sales book."""

    business_type: str = "trader"
    months_in_business: int = 0
    # àjọ / esusu / cooperative
    ajo_contributions: list[Contribution] = field(default_factory=list)
    ajo_expected: int = 0  # contributions the group expected in the window
    # utility, airtime and rent payments: (paid on time, total due)
    bills_on_time: int = 0
    bills_total: int = 0
    # mobile money / bank transfers received from customers: (day, amount)
    inflows: list[tuple[date, Decimal]] = field(default_factory=list)
    # monthly repayments already owed to other lenders
    existing_monthly_debt: Decimal = ZERO
    # times the owner used the growth / farm advice (shows engagement)
    advice_sessions: int = 0
    # self-declared; used ONLY to route to support programmes, never to score
    women_led: bool | None = None


@dataclass
class Features:
    business_type: str
    months_of_records: int  # calendar months from first to last record
    active_months: int  # months with at least one sale or inflow
    monthly_revenue: list[Decimal]  # oldest first, one per month in span
    avg_monthly_revenue: Decimal
    avg_monthly_profit: Decimal
    margin: float | None  # profit / revenue on recorded sales
    consistency: float  # 0..1, higher is steadier (season-aware for farms)
    growth: float | None  # recent 3 months vs previous 3, e.g. 0.2 = +20%
    loss_sale_share: float  # share of sales made at a loss
    restock_months: int  # months with a restock (business keeps investing)
    ajo_rate: float | None  # contributions made / expected
    ajo_on_time: float | None
    bills_rate: float | None
    debt_to_profit: float | None
    advice_sessions: int
    months_in_business: int


def _month(d: datetime | date) -> tuple[int, int]:
    return (d.year, d.month)


def _months_between(first: tuple[int, int], last: tuple[int, int]) -> list[tuple[int, int]]:
    out, (y, m) = [], first
    while (y, m) <= last:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def build_features(entries: list[Entry], alt: AltData | None = None) -> Features:
    alt = alt or AltData()
    if alt.business_type not in BUSINESS_TYPES:
        raise ValueError(f"business_type must be one of {BUSINESS_TYPES}")

    revenue: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
    profit: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
    restock: set[tuple[int, int]] = set()
    sales = losses = 0
    sales_revenue = sales_profit = ZERO

    for e in entries:
        if e.created_at is None:
            continue
        key = _month(e.created_at)
        if e.kind == "sale":
            revenue[key] += e.amount
            profit[key] += e.profit
            sales += 1
            sales_revenue += e.amount
            sales_profit += e.profit
            if e.profit < 0:
                losses += 1
        elif e.kind == "restock":
            restock.add(key)
            revenue.setdefault(key, ZERO)

    # Customer payments seen in mobile money / bank data that the sales book
    # missed still count as revenue, but not as profit.
    for day, amount in alt.inflows:
        key = _month(day)
        if not any(_month(e.created_at) == key for e in entries if e.created_at and e.kind == "sale"):
            revenue[key] += Decimal(amount)

    keys = sorted(revenue)
    span = _months_between(keys[0], keys[-1]) if keys else []
    monthly = [revenue.get(k, ZERO) for k in span]
    monthly_profit = [profit.get(k, ZERO) for k in span]
    n = len(span)

    avg_rev = (sum(monthly, ZERO) / n).quantize(Decimal("0.01")) if n else ZERO
    avg_profit = (sum(monthly_profit, ZERO) / n).quantize(Decimal("0.01")) if n else ZERO
    active = sum(1 for v in monthly if v > 0)

    consistency = _consistency(monthly, alt.business_type)

    growth = None
    if n >= 6:
        recent, before = sum(monthly[-3:], ZERO), sum(monthly[-6:-3], ZERO)
        if before > 0:
            growth = float((recent - before) / before)

    ajo_rate = ajo_on_time = None
    if alt.ajo_expected > 0:
        ajo_rate = min(1.0, len(alt.ajo_contributions) / alt.ajo_expected)
        if alt.ajo_contributions:
            ajo_on_time = sum(c.on_time for c in alt.ajo_contributions) / len(alt.ajo_contributions)

    bills_rate = alt.bills_on_time / alt.bills_total if alt.bills_total else None
    debt_ratio = float(alt.existing_monthly_debt / avg_profit) if avg_profit > 0 else (
        None if alt.existing_monthly_debt == 0 else 9.99
    )

    return Features(
        business_type=alt.business_type,
        months_of_records=n,
        active_months=active,
        monthly_revenue=monthly,
        avg_monthly_revenue=avg_rev,
        avg_monthly_profit=avg_profit,
        margin=float(sales_profit / sales_revenue) if sales_revenue > 0 else None,
        consistency=consistency,
        growth=growth,
        loss_sale_share=losses / sales if sales else 0.0,
        restock_months=len(restock),
        ajo_rate=ajo_rate,
        ajo_on_time=ajo_on_time,
        bills_rate=bills_rate,
        debt_to_profit=debt_ratio,
        advice_sessions=alt.advice_sessions,
        months_in_business=max(alt.months_in_business, n),
    )


def _consistency(monthly: list[Decimal], business_type: str) -> float:
    """0..1. Traders: steady monthly sales. Farmers: steady season to season."""
    values = [float(v) for v in monthly]
    if len(values) < 2 or sum(values) == 0:
        return 0.0
    if business_type == "farmer":
        # Compare rolling 3-month totals: a harvest spike followed by quiet
        # months is normal, a whole quarter of nothing is not.
        windows = [sum(values[i:i + 3]) for i in range(0, max(1, len(values) - 2))]
        active_share = sum(1 for w in windows if w > 0) / len(windows)
        return round(active_share, 3)
    avg = mean(values)
    cv = pstdev(values) / avg if avg else 9.0
    active_share = sum(1 for v in values if v > 0) / len(values)
    steadiness = max(0.0, 1.0 - min(cv, 1.5) / 1.5)
    return round(0.5 * active_share + 0.5 * steadiness, 3)
