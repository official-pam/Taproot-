"""Synthetic businesses for demos and tests. No real customer data.

Personas tell the story in the pitch; ``portfolio`` makes a few hundred
random SMEs for the bank dashboard. Everything is seeded so it's repeatable.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.credit.features import AltData, Contribution
from app.trade.ledger import LAGOS, Entry

TODAY = date(2026, 10, 1)


def _sale(day: date, name: str, qty: int, price: int, cost: int) -> Entry:
    q, p, c = Decimal(qty), Decimal(price), Decimal(cost)
    return Entry(kind="sale", product_name=name, qty=q, unit_price=p, unit_cost=c, set_price=p,
                 amount=q * p, profit=q * (p - c),
                 created_at=datetime(day.year, day.month, day.day, 12, tzinfo=LAGOS))


def _restock(day: date, name: str, qty: int, cost: int) -> Entry:
    q, c = Decimal(qty), Decimal(cost)
    return Entry(kind="restock", product_name=name, qty=q, unit_price=c, unit_cost=c, set_price=c,
                 amount=q * c, created_at=datetime(day.year, day.month, day.day, 9, tzinfo=LAGOS))


def _months_back(n: int) -> list[date]:
    out, d = [], TODAY.replace(day=1)
    for _ in range(n):
        out.append(d)
        d = (d - timedelta(days=1)).replace(day=1)
    return list(reversed(out))


def _ajo(months: int, missed: int = 0, late: int = 0, amount: int = 5000) -> tuple[list[Contribution], int]:
    weeks = months * 4
    paid = []
    for i in range(weeks - missed):
        paid.append(Contribution(TODAY - timedelta(weeks=weeks - i), Decimal(amount), on_time=i >= late))
    return paid, weeks


def hauwa(rng: random.Random | None = None) -> tuple[list[Entry], AltData]:
    """Maize farmer near Zaria: two harvest peaks, quiet planting months."""
    rng = rng or random.Random(1)
    entries = []
    for d in _months_back(14):
        if d.month in (9, 10, 11):  # main harvest sales
            for _ in range(rng.randint(4, 7)):
                entries.append(_sale(d + timedelta(days=rng.randint(0, 25)), "maize (bag)",
                                     rng.randint(5, 12), 52000, 30000))
        elif d.month in (1, 2, 3):  # stored grain sold as price rises
            for _ in range(rng.randint(1, 3)):
                entries.append(_sale(d + timedelta(days=rng.randint(0, 25)), "maize (bag)",
                                     rng.randint(3, 6), 60000, 30000))
        if d.month in (5, 6):
            entries.append(_restock(d, "fertilizer (bag)", 6, 38000))
    ajo, expected = _ajo(12, missed=1)
    return entries, AltData(business_type="farmer", months_in_business=96, ajo_contributions=ajo,
                            ajo_expected=expected, bills_on_time=11, bills_total=12,
                            advice_sessions=9, women_led=True)


def ngozi(rng: random.Random | None = None) -> tuple[list[Entry], AltData]:
    """Fabric trader in Onitsha: steady, growing."""
    rng = rng or random.Random(2)
    entries = []
    for i, d in enumerate(_months_back(12)):
        entries.append(_restock(d, "ankara (6 yards)", 40, 9000))
        for _ in range(rng.randint(14, 20) + i):
            entries.append(_sale(d + timedelta(days=rng.randint(0, 27)), "ankara (6 yards)",
                                 rng.randint(1, 3), 12500, 9000))
    ajo, expected = _ajo(12)
    return entries, AltData(business_type="trader", months_in_business=60, ajo_contributions=ajo,
                            ajo_expected=expected, bills_on_time=12, bills_total=12,
                            advice_sessions=6, women_led=True)


def tunde(rng: random.Random | None = None) -> tuple[list[Entry], AltData]:
    """Small garri processor in Ogun: growing, ready for equipment."""
    rng = rng or random.Random(3)
    entries = []
    for i, d in enumerate(_months_back(18)):
        entries.append(_restock(d, "cassava (tonne)", 3 + i // 4, 70000))
        for _ in range(8 + i):
            entries.append(_sale(d + timedelta(days=rng.randint(0, 27)), "garri (50kg bag)",
                                 rng.randint(2, 4), 38000, 26000))
    return entries, AltData(business_type="manufacturer", months_in_business=48,
                            bills_on_time=17, bills_total=18, advice_sessions=3, women_led=False)


def bisi(rng: random.Random | None = None) -> tuple[list[Entry], AltData]:
    """Pepper and tomato seller, new to Taproot: thin file, strong àjọ."""
    rng = rng or random.Random(4)
    entries = []
    for d in _months_back(2):
        for _ in range(rng.randint(15, 20)):
            entries.append(_sale(d + timedelta(days=rng.randint(0, 27)), "tomato (basket)",
                                 1, 18000, 14000))
    ajo, expected = _ajo(24)
    return entries, AltData(business_type="trader", months_in_business=72, ajo_contributions=ajo,
                            ajo_expected=expected, bills_on_time=10, bills_total=10, women_led=True)


def musa(rng: random.Random | None = None) -> tuple[list[Entry], AltData]:
    """Phone accessories trader: falling sales, selling below cost, existing debt."""
    rng = rng or random.Random(5)
    entries = []
    for i, d in enumerate(_months_back(9)):
        for _ in range(max(2, 22 - i * 3)):
            price = rng.choice([2500, 3000, 3500])
            entries.append(_sale(d + timedelta(days=rng.randint(0, 27)), "charger", rng.randint(1, 4),
                                 price, 3200))
    ajo, expected = _ajo(6, missed=8)
    return entries, AltData(business_type="trader", months_in_business=18, ajo_contributions=ajo,
                            ajo_expected=expected, bills_on_time=4, bills_total=9,
                            existing_monthly_debt=Decimal("60000"), women_led=False)


PERSONAS = {
    "hauwa": ("Hauwa", "Maize farmer, Zaria (Kaduna)", hauwa),
    "ngozi": ("Ngozi", "Fabric trader, Onitsha (Anambra)", ngozi),
    "tunde": ("Tunde", "Garri processor, Abeokuta (Ogun)", tunde),
    "bisi": ("Bisi", "Tomato seller, Mile 12 (Lagos)", bisi),
    "musa": ("Musa", "Phone accessories, Kano", musa),
}

STATES = ["Lagos", "Kano", "Kaduna", "Oyo", "Ogun", "Anambra", "Rivers", "Benue", "Plateau",
          "Enugu", "Abuja (FCT)", "Niger", "Kwara", "Delta", "Katsina"]


def portfolio(n: int = 300, seed: int = 42) -> list[dict]:
    """Random SMEs built from persona templates with noise, for the dashboard."""
    rng = random.Random(seed)
    makers = [hauwa, ngozi, tunde, bisi, musa]
    weights = [3, 4, 2, 2, 2]
    out = []
    for i in range(n):
        maker = rng.choices(makers, weights)[0]
        entries, alt = maker(random.Random(rng.random()))
        scale = Decimal(str(round(rng.uniform(0.3, 2.5), 2)))
        for e in entries:
            e.amount *= scale
            e.profit *= scale
        # Vary the record length, drop some sales, add some below-cost ones.
        keep_months = rng.randint(2, 18)
        cutoff = datetime(TODAY.year, TODAY.month, 1, tzinfo=LAGOS) - timedelta(days=30 * keep_months)
        drop = rng.uniform(0, 0.5)
        entries = [e for e in entries if e.created_at >= cutoff and rng.random() > drop]
        if rng.random() < 0.3:
            for e in entries:
                if e.kind == "sale" and rng.random() < 0.3:
                    e.profit = -abs(e.profit) * Decimal("0.3")
        alt.months_in_business = rng.randint(6, 120)
        if alt.ajo_expected and rng.random() < 0.4:
            alt.ajo_contributions = alt.ajo_contributions[: int(len(alt.ajo_contributions) * rng.uniform(0.5, 1))]
        if alt.bills_total:
            alt.bills_on_time = round(alt.bills_total * rng.uniform(0.4, 1))
        alt.advice_sessions = rng.randint(0, 12)
        if rng.random() < 0.25:
            alt.existing_monthly_debt = Decimal(rng.randrange(0, 120000, 5000))
        out.append({"id": f"SME-{1000 + i}", "state": rng.choice(STATES), "entries": entries, "alt": alt})
    return out
