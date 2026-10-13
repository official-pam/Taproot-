"""Match a scored business to the right financing product and size the loan.

The catalogue below is illustrative: product names, rates and limits are
placeholders to be replaced with the partner bank's real products. Loan size
always comes from what the business can repay out of its own profit, so the
platform never pushes someone into a loan they can't carry.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from app.credit.features import Features
from app.credit.scoring import Score

# Share of average monthly profit that may go to repayments (all lenders).
AFFORDABILITY = Decimal("0.30")
# For seasonal loans, share of expected harvest profit used to repay.
HARVEST_SHARE = Decimal("0.50")


@dataclass(frozen=True)
class Product:
    code: str
    name: str
    for_types: tuple[str, ...]
    bands: tuple[str, ...]
    monthly_rate: Decimal  # flat, illustrative
    months: int
    min_amount: Decimal
    max_amount: Decimal
    seasonal: bool = False  # one repayment after harvest
    description: str = ""


CATALOGUE: tuple[Product, ...] = (
    Product("SEASON", "Seasonal input loan", ("farmer",), ("A", "B", "C"),
            Decimal("0.025"), 6, Decimal("50000"), Decimal("3000000"), seasonal=True,
            description="Seeds, fertilizer and labour before planting; repay once after harvest."),
    Product("STOCK", "Stock finance", ("trader",), ("A", "B", "C"),
            Decimal("0.03"), 6, Decimal("50000"), Decimal("5000000"),
            description="Buy more stock at better prices; repay monthly from sales."),
    Product("ASSET", "Equipment finance", ("manufacturer", "farmer"), ("A", "B"),
            Decimal("0.022"), 12, Decimal("200000"), Decimal("10000000"),
            description="Machines, solar, cold storage or processing equipment."),
    Product("WCAP", "Working capital loan", ("trader", "manufacturer", "farmer"), ("A", "B", "C"),
            Decimal("0.03"), 6, Decimal("50000"), Decimal("5000000"),
            description="Flexible cash for day-to-day running costs."),
    Product("GROUP", "Àjọ group loan", ("trader", "manufacturer", "farmer"), ("C", "D"),
            Decimal("0.025"), 4, Decimal("20000"), Decimal("300000"),
            description="Small loan backed by the member's savings group; grows with each repayment."),
    Product("BUILDER", "Credit builder savings", ("trader", "manufacturer", "farmer"), ("D", "E"),
            Decimal("0"), 3, Decimal("0"), Decimal("0"),
            description="Save a little each week; after 3 months of records, a first loan unlocks."),
)


@dataclass
class Offer:
    product: Product
    amount: Decimal
    repayment: Decimal  # per month, or the single harvest repayment if seasonal
    total_cost: Decimal
    why: str


def _round_down(v: Decimal, step: int = 5000) -> Decimal:
    return (v / step).to_integral_value(rounding=ROUND_DOWN) * step


def size(product: Product, f: Features, existing_debt: Decimal = Decimal("0")) -> Offer | None:
    if product.code == "BUILDER":
        return Offer(product, Decimal("0"), Decimal("0"), Decimal("0"),
                     "Start building a record; a first loan unlocks after 3 months.")

    rate, months = product.monthly_rate, product.months
    if product.seasonal:
        # Expected harvest profit ≈ a year of average profit, repaid once.
        harvest_profit = f.avg_monthly_profit * 12
        repay_capacity = harvest_profit * HARVEST_SHARE
        principal = repay_capacity / (1 + rate * months)
    else:
        monthly_capacity = f.avg_monthly_profit * AFFORDABILITY - existing_debt
        if monthly_capacity <= 0:
            return None
        principal = monthly_capacity * months / (1 + rate * months)

    amount = _round_down(min(principal, product.max_amount))
    if amount < product.min_amount:
        return None
    total = (amount * (1 + rate * months)).quantize(Decimal("1"))
    repayment = total if product.seasonal else (total / months).quantize(Decimal("1"))
    why = (f"Sized so repayment stays within {AFFORDABILITY:.0%} of monthly profit"
           if not product.seasonal else "Repaid once from half of the expected harvest profit")
    return Offer(product, amount, repayment, total - amount, why)


def match(f: Features, s: Score, existing_debt: Decimal = Decimal("0")) -> list[Offer]:
    """Best-fit offers first. Always returns at least the credit builder."""
    offers: list[Offer] = []
    for p in CATALOGUE:
        if f.business_type in p.for_types and s.band in p.bands:
            o = size(p, f, existing_debt)
            if o:
                offers.append(o)
    # Prefer the product built for this type of business, then the bigger offer.
    offers.sort(key=lambda o: (o.product.for_types != (f.business_type,), -o.amount))
    if not offers:
        offers.append(size(CATALOGUE[-1], f))  # credit builder
    return offers
