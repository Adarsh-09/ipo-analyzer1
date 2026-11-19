"""
IPOVision: RHP evidence -> FundamentalInputs mapper.

Only verified and explicitly approved values can enter scoring.py.
Subjective ratings always remain manual inputs.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from src.fundamental_analysis.scoring import FundamentalInputs


def approved_value(
    fields: Dict[str, Any],
    key: str
) -> Any:

    item = fields.get(key) or {}

    if item.get("status") != "verified":
        return None

    if not item.get("approved", False):
        return None

    return item.get("value")


def approved_series(
    fields: Dict[str, Any],
    key: str
) -> Optional[list]:

    value = approved_value(fields, key)

    if not isinstance(value, list):
        return None

    result = []
    years = []

    for row in value:

        if not isinstance(row, dict):
            continue

        amount = row.get("amount")
        period = row.get("period")

        if isinstance(amount, (int, float)):
            result.append(float(amount))
            if isinstance(period, str):
                match = re.search(r"(?:19|20)\d{2}", period)
                if match:
                    years.append(int(match.group()))

    if len(years) == len(result) and len(years) > 1 and years == sorted(years, reverse=True):
        result = list(reversed(result))

    return result or None


def latest_and_previous(
    fields: Dict[str, Any],
    key: str
):
    values = approved_series(fields, key) or []

    latest = values[-1] if values else None

    previous = (
        values[-2]
        if len(values) >= 2
        else None
    )

    return latest, previous


def numeric_value(
    fields: Dict[str, Any],
    key: str
):

    value = approved_value(fields, key)

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    return None


def derive_ebitda_margin(fields: Dict[str, Any]):

    # Prefer an explicitly reported EBITDA margin.
    explicit = numeric_value(
        fields,
        "ebitda_margin_pct"
    )

    if explicit is not None:
        return explicit

    # Otherwise calculate only when approved EBITDA and revenue
    # figures have matching financial-year labels.
    ebitda = approved_value(fields, "ebitda")
    revenue = approved_value(fields, "revenue")

    if not isinstance(ebitda, list):
        return None

    if not isinstance(revenue, list):
        return None

    ebitda_map = {
        row.get("period"): row.get("amount")
        for row in ebitda
        if isinstance(row, dict)
    }

    revenue_map = {
        row.get("period"): row.get("amount")
        for row in revenue
        if isinstance(row, dict)
    }

    common_periods = [
        period
        for period in ebitda_map
        if period in revenue_map
    ]

    if not common_periods:
        return None

    # Select the latest common period, preserving the source order.
    period = common_periods[-1]

    try:

        rev = float(revenue_map[period])
        ebitda_value = float(ebitda_map[period])

        if rev <= 0:
            return None

        return (ebitda_value / rev) * 100

    except (TypeError, ValueError, ZeroDivisionError):

        return None


def to_fundamental_inputs(
    fields: Dict[str, Any],
    manual: Optional[Dict[str, Any]] = None
) -> FundamentalInputs:
    """
    Build the existing FundamentalInputs dataclass.

    Missing, unverified or unapproved information is represented by None.
    """

    manual = manual or {}

    revenue = approved_series(
        fields,
        "revenue"
    )

    pat = approved_series(
        fields,
        "pat"
    )

    cfo, _ = latest_and_previous(
        fields,
        "cfo"
    )

    inventory_latest, inventory_previous = latest_and_previous(
        fields,
        "inventory_days"
    )

    return FundamentalInputs(

        # Historical financials
        revenue=revenue,
        pat=pat,

        # Profitability
        ebitda_margin_pct=derive_ebitda_margin(fields),

        roe_pct=numeric_value(fields, "roe_pct"),

        roce_pct=numeric_value(fields, "roce_pct"),

        # Debt
        debt_to_equity=numeric_value(
            fields,
            "debt_to_equity"
        ),

        interest_coverage=numeric_value(
            fields,
            "interest_coverage"
        ),

        # Cash flow and working capital
        cfo=cfo,

        inventory_days=inventory_latest,

        inventory_days_prev=inventory_previous,

        # Manual judgements
        business_quality_rating=manual.get(
            "business_quality_rating"
        ),

        management_rating=manual.get(
            "management_rating"
        ),

        litigation_severity=manual.get(
            "litigation_severity"
        ),

        use_of_funds_rating=manual.get(
            "use_of_funds_rating"
        ),

        # Promoters
        promoter_holding_post_pct=numeric_value(
            fields,
            "promoter_holding_post_pct"
        ),

        promoter_pledge_pct=numeric_value(
            fields,
            "promoter_pledge_pct"
        ),

        # Peer comparison
        peer_ebitda_margin_pct=numeric_value(
            fields,
            "peer_ebitda_margin_pct"
        ),

        peer_roe_pct=numeric_value(
            fields,
            "peer_roe_pct"
        ),

        peer_revenue_growth_pct=numeric_value(
            fields,
            "peer_revenue_growth_pct"
        ),

        # Valuation and issue structure
        pe_ratio=numeric_value(
            fields,
            "pe_ratio"
        ),

        peer_pe_ratio=numeric_value(
            fields,
            "peer_pe_ratio"
        ),

        ofs_pct=numeric_value(
            fields,
            "ofs_pct"
        ),
    )