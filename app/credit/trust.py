"""How much can the bank trust a self-reported sales book?

A trader who knows the book feeds a loan could inflate it. These checks don't
accuse anyone; they give the loan officer flags to look at and lower how much
weight the record carries. Pure functions, no database.

Signals:
- Logging habit: on how many days, and for how long in a row, the trader
  logged. Sixty steady days says more than one big week.
- Backfilling: many sales entered in a burst after the fact.
- Spikes: a day far above the trader's usual day.
- Margins: profit margins outside what is normal for small traders.
- Account cross-check: logged sales against inflows seen in the trader's
  Zenith account (when they have one and agree to share it).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from statistics import median

from app.trade.ledger import LAGOS, Entry

ZERO = Decimal("0")

# Typical gross margin range for informal trade; outside it we ask, not reject.
MARGIN_LOW, MARGIN_HIGH = Decimal("-0.05"), Decimal("0.60")
SPIKE_FACTOR = 5  # a day more than 5x the median day
BURST_MINUTES = 10  # sales logged this close together...
BURST_SIZE = 15  # ...this many times in a row looks like backfilling
ACCOUNT_GAP = 1.5  # logged sales more than 1.5x account inflows


@dataclass
class Flag:
    code: str
    severity: str  # "info" | "check" | "serious"
    text: str


@dataclass
class Trust:
    logged_days: int  # distinct days with at least one entry
    days_span: int  # first to last entry, inclusive
    logging_rate: float  # logged_days / days_span (0..1)
    longest_streak: int  # most consecutive days logged
    recent_streak: int  # consecutive logged days ending at the last entry
    avg_daily_revenue: Decimal  # over days with sales
    daily_revenue_cv: float | None  # variability of daily revenue
    account_ratio: float | None  # logged sales / account inflows
    flags: list[Flag] = field(default_factory=list)
    level: str = "low"  # "high" | "medium" | "low": how much weight the record deserves

    def to_dict(self) -> dict:
        return {
            "logged_days": self.logged_days,
            "days_span": self.days_span,
            "logging_rate": round(self.logging_rate, 3),
            "longest_streak": self.longest_streak,
            "recent_streak": self.recent_streak,
            "avg_daily_revenue": float(self.avg_daily_revenue),
            "daily_revenue_cv": None if self.daily_revenue_cv is None else round(self.daily_revenue_cv, 3),
            "account_ratio": None if self.account_ratio is None else round(self.account_ratio, 3),
            "level": self.level,
            "flags": [{"code": f.code, "severity": f.severity, "text": f.text} for f in self.flags],
        }


def _day(e: Entry) -> date:
    return e.created_at.astimezone(LAGOS).date()


def _streaks(days: list[date]) -> tuple[int, int]:
    if not days:
        return 0, 0
    longest = run = 1
    for a, b in zip(days, days[1:]):
        run = run + 1 if b - a == timedelta(days=1) else 1
        longest = max(longest, run)
    return longest, run


def check(entries: list[Entry], account_inflows: Decimal | None = None) -> Trust:
    """``account_inflows``: total money into the trader's Zenith account over the same period."""
    dated = sorted((e for e in entries if e.created_at is not None), key=lambda e: e.created_at)
    sales = [e for e in dated if e.kind == "sale"]
    flags: list[Flag] = []

    days = sorted({_day(e) for e in dated})
    span = (days[-1] - days[0]).days + 1 if days else 0
    longest, recent = _streaks(days)
    rate = len(days) / span if span else 0.0

    daily: dict[date, Decimal] = defaultdict(lambda: ZERO)
    for e in sales:
        daily[_day(e)] += e.amount
    values = list(daily.values())
    avg_daily = (sum(values, ZERO) / len(values)).quantize(Decimal("0.01")) if values else ZERO
    cv = None
    if len(values) >= 5 and avg_daily > 0:
        mean = float(avg_daily)
        cv = (sum((float(v) - mean) ** 2 for v in values) / len(values)) ** 0.5 / mean

    # Logging habit
    if len(days) < 14:
        flags.append(Flag("short_history", "info", f"Only {len(days)} days logged so far"))
    elif rate < 0.3:
        flags.append(Flag("patchy_logging", "check", f"Logged on {rate:.0%} of days since starting"))

    # Spikes
    if len(values) >= 7:
        mid = median(values)
        spikes = [d for d, v in daily.items() if mid > 0 and v > mid * SPIKE_FACTOR]
        if spikes:
            flags.append(Flag("spike_days", "check",
                              f"{len(spikes)} day(s) with sales over {SPIKE_FACTOR}x a normal day"))

    # Backfilling bursts
    run = best = 1
    for a, b in zip(sales, sales[1:]):
        run = run + 1 if (b.created_at - a.created_at) <= timedelta(minutes=BURST_MINUTES) and _day(a) == _day(b) else 1
        best = max(best, run)
    if len(sales) >= BURST_SIZE and best >= BURST_SIZE:
        flags.append(Flag("bulk_entry", "check", f"{best} sales logged within minutes of each other"))

    # Margins
    revenue = sum((e.amount for e in sales), ZERO)
    profit = sum((e.profit for e in sales), ZERO)
    if revenue > 0:
        margin = profit / revenue
        if margin > MARGIN_HIGH:
            flags.append(Flag("margin_high", "check", f"Profit margin of {margin:.0%} is unusually high for trade"))
        elif margin < MARGIN_LOW:
            flags.append(Flag("margin_negative", "check", f"Selling below cost overall ({margin:.0%})"))

    # Account cross-check
    ratio = None
    if account_inflows is not None:
        if account_inflows > 0:
            ratio = float(revenue / account_inflows)
            if ratio > ACCOUNT_GAP:
                flags.append(Flag("account_gap", "serious",
                                  f"Logged sales are {ratio:.1f}x the money seen in the Zenith account"))
        elif revenue > 0:
            flags.append(Flag("account_empty", "check", "No account inflows to match logged sales"))
    else:
        flags.append(Flag("no_account", "info", "No Zenith account linked yet; sales not cross-checked"))

    serious = any(f.severity == "serious" for f in flags)
    checks = sum(f.severity == "check" for f in flags)
    if serious or len(days) < 14:
        level = "low"
    elif len(days) >= 60 and rate >= 0.6 and checks == 0 and ratio is not None:
        level = "high"
    elif len(days) >= 30 and rate >= 0.4 and checks <= 1:
        level = "medium"
    else:
        level = "low"

    return Trust(len(days), span, rate, longest, recent, avg_daily, cv, ratio, flags, level)
