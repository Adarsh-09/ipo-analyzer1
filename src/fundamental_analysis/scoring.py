"""IPOVision scoring (Phase 6): the two 100-point scores from the IPO analysis checklist.

The category weights come from the checklist. The mapping from raw numbers to 0-1 sub-scores is a transparent
heuristic, not a fitted model. A missing input never counts as zero: a category with no data is left out and the
score is rescaled over the weight that could be scored (reported as `coverage`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

FUNDAMENTAL_WEIGHTS: Dict[str, float] = {
    "Business quality": 15, "Revenue and profit growth": 15, "Profitability": 10, "Debt and balance sheet": 10,
    "Cash flow and working capital": 10, "Promoter and management": 10, "Peer comparison": 10,
    "Valuation": 15, "IPO structure and use of funds": 5}
LISTING_WEIGHTS: Dict[str, float] = {
    "GMP": 30, "QIB subscription": 25, "Total subscription": 15, "Market sentiment": 10,
    "IPO valuation": 10, "Sector sentiment": 5, "Issue size and liquidity": 5}
FUNDAMENTAL_BANDS = ((80, "Excellent"), (70, "Good"), (60, "Average"), (50, "Weak"), (float("-inf"), "Avoid / caution"))
LISTING_BANDS = ((80, "Strong listing setup"), (70, "Good"), (60, "Uncertain"), (float("-inf"), "Weak"))
PARTIAL_BELOW = 0.60            # below this share of the checklist, the result is marked partial
GROWTH_POINTS = [(0, 0.0), (10, 0.4), (20, 0.8), (30, 1.0)]


# ------------------------------------------------------------------ helpers
def _missing(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def interp(x, points) -> Optional[float]:
    """Piecewise-linear map of x through (x, score) points; clamps outside the range; None if x is missing."""
    if _missing(x):
        return None
    x, pts = float(x), sorted(points)
    if x <= pts[0][0]:
        return float(pts[0][1])
    if x >= pts[-1][0]:
        return float(pts[-1][1])
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return float(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
    return None


def mean_available(values) -> Optional[float]:
    v = [x for x in values if x is not None]
    return sum(v) / len(v) if v else None


def _wmean(pairs) -> Optional[float]:
    pairs = [(w, s) for w, s in pairs if s is not None]
    total = sum(w for w, _ in pairs)
    return None if total == 0 else sum(w * s for w, s in pairs) / total


def _clean(series) -> List[float]:
    return [float(v) for v in (series or []) if not _missing(v)]


def cagr(series) -> Optional[float]:
    """Compound annual growth in %, oldest value first. Undefined (None) if an end value is not positive."""
    s = _clean(series)
    if len(s) < 2 or s[0] <= 0 or s[-1] <= 0:
        return None
    return ((s[-1] / s[0]) ** (1.0 / (len(s) - 1)) - 1.0) * 100.0


def _rating(x) -> Optional[float]:
    return None if _missing(x) else min(max(float(x), 0.0), 5.0) / 5.0


def _diff(a, b) -> Optional[float]:
    return None if _missing(a) or _missing(b) else float(a) - float(b)


def band_for(score: float, bands) -> str:
    for floor, name in bands:
        if score >= floor:
            return name
    return bands[-1][1]


def _combine(scores: Dict[str, Optional[float]], weights: Dict[str, float], bands) -> dict:
    cats, avail, pts = {}, 0.0, 0.0
    for name, w in weights.items():
        s = scores.get(name)
        s = None if s is None else min(max(s, 0.0), 1.0)
        cats[name] = {"weight": w, "score": s, "points": None if s is None else s * w}
        if s is not None:
            avail += w
            pts += s * w
    coverage = avail / sum(weights.values())
    score = None if avail == 0 else 100.0 * pts / avail
    return {"score": score, "band": None if score is None else band_for(score, bands),
            "coverage": coverage, "partial": coverage < PARTIAL_BELOW, "categories": cats}


# ------------------------------------------------------------------ fundamental score
@dataclass
class FundamentalInputs:
    revenue: Optional[Sequence[float]] = None            # last 3-5 years, oldest first (Rs crore)
    pat: Optional[Sequence[float]] = None                 # profit after tax, same years
    ebitda_margin_pct: Optional[float] = None
    roe_pct: Optional[float] = None
    roce_pct: Optional[float] = None
    debt_to_equity: Optional[float] = None
    interest_coverage: Optional[float] = None
    cfo: Optional[float] = None                           # latest-year operating cash flow
    inventory_days: Optional[float] = None
    inventory_days_prev: Optional[float] = None
    business_quality_rating: Optional[float] = None       # 0-5, your judgement
    management_rating: Optional[float] = None             # 0-5
    promoter_holding_post_pct: Optional[float] = None
    promoter_pledge_pct: Optional[float] = None
    litigation_severity: Optional[float] = None           # 0 none ... 5 severe
    peer_ebitda_margin_pct: Optional[float] = None
    peer_roe_pct: Optional[float] = None
    peer_revenue_growth_pct: Optional[float] = None
    pe_ratio: Optional[float] = None
    peer_pe_ratio: Optional[float] = None
    ofs_pct: Optional[float] = None                       # share of the issue that is an offer for sale
    use_of_funds_rating: Optional[float] = None           # 0-5


def score_fundamental(inp: FundamentalInputs) -> dict:
    flags: List[str] = []
    rev, pat = _clean(inp.revenue), _clean(inp.pat)
    rc, pc = cagr(rev), cagr(pat)

    # growth
    s_rev = interp(rc, GROWTH_POINTS)
    s_pat = None
    if pat:
        if pat[-1] <= 0:
            s_pat = 0.0
            flags.append("Loss-making in the latest year.")
        elif pc is not None:
            s_pat = interp(pc, GROWTH_POINTS)
        elif len(pat) >= 2:
            s_pat = 0.5                                   # turned profitable
    growth = mean_available([s_rev, s_pat])
    profit_weak = (pc is not None and pc <= 2) or (len(pat) >= 2 and pat[-1] <= pat[-2])
    if rc is not None and rc >= 8 and pat and profit_weak:
        flags.append("Revenue is rising but profits are flat or falling.")

    # profitability and balance sheet
    profitability = mean_available([interp(inp.ebitda_margin_pct, [(0, 0), (8, .3), (15, .6), (25, 1)]),
                                    interp(inp.roe_pct, [(0, 0), (8, .3), (15, .7), (25, 1)]),
                                    interp(inp.roce_pct, [(0, 0), (8, .3), (15, .7), (25, 1)])])
    debt = mean_available([interp(inp.debt_to_equity, [(0, 1), (.5, .85), (1, .6), (2, .25), (3, 0)]),
                           interp(inp.interest_coverage, [(1, 0), (2, .3), (4, .7), (8, 1)])])

    # cash flow and working capital
    ratio, s_cfo, s_wc, inv_change = None, None, None, None
    if not _missing(inp.cfo):
        if pat and pat[-1] > 0:
            ratio = float(inp.cfo) / pat[-1]
            s_cfo = interp(ratio, [(0, 0), (.5, .4), (.8, .7), (1.0, 1)])
        elif pat:
            s_cfo = 0.5 if inp.cfo > 0 else 0.0
    if not _missing(inp.inventory_days) and not _missing(inp.inventory_days_prev) and inp.inventory_days_prev > 0:
        inv_change = (inp.inventory_days / inp.inventory_days_prev - 1.0) * 100.0
        s_wc = interp(inv_change, [(0, 1), (25, .5), (60, 0)])
    cashflow = _wmean([(0.7, s_cfo), (0.3, s_wc)])
    if ratio is not None and ratio < 0.5:
        flags.append("Operating cash flow is far below reported profit.")
    if not _missing(inp.debt_to_equity) and inp.debt_to_equity > 2 and \
            ((ratio is not None and ratio < 0.5) or (not _missing(inp.cfo) and inp.cfo <= 0)):
        flags.append("High debt together with weak cash flow.")
    g_last = (rev[-1] / rev[-2] - 1.0) * 100.0 if len(rev) >= 2 and rev[-2] > 0 else None
    if inv_change is not None and inv_change > 25 and g_last is not None and g_last < 10:
        flags.append("Inventory is building up faster than sales.")

    # promoter and management (litigation counts here)
    s_lit = None if _missing(inp.litigation_severity) else 1.0 - _rating(inp.litigation_severity)
    promoter = _wmean([(0.50, _rating(inp.management_rating)),
                       (0.15, interp(inp.promoter_holding_post_pct, [(25, .3), (50, .7), (75, 1)])),
                       (0.20, interp(inp.promoter_pledge_pct, [(0, 1), (10, .6), (30, .2), (50, 0)])),
                       (0.15, s_lit)])
    if not _missing(inp.promoter_pledge_pct) and inp.promoter_pledge_pct > 10:
        flags.append("Promoter shares are pledged.")
    if not _missing(inp.litigation_severity) and inp.litigation_severity >= 4:
        flags.append("Serious litigation or regulatory issues.")

    # peers, valuation, structure
    peers = mean_available([interp(d, [(-10, 0), (0, .6), (10, 1)]) for d in
                            (_diff(inp.ebitda_margin_pct, inp.peer_ebitda_margin_pct),
                             _diff(inp.roe_pct, inp.peer_roe_pct), _diff(rc, inp.peer_revenue_growth_pct))])
    premium = None
    if not _missing(inp.pe_ratio) and not _missing(inp.peer_pe_ratio) and inp.pe_ratio > 0 and inp.peer_pe_ratio > 0:
        premium = (inp.pe_ratio / inp.peer_pe_ratio - 1.0) * 100.0
    valuation = interp(premium, [(-20, 1), (0, .7), (20, .4), (50, .1), (80, 0)])
    if premium is not None and premium > 50:
        flags.append("Valuation is well above listed peers.")
    structure = mean_available([interp(inp.ofs_pct, [(0, 1), (30, .8), (60, .4), (100, .1)]),
                                _rating(inp.use_of_funds_rating)])
    if not _missing(inp.ofs_pct) and inp.ofs_pct > 60:
        flags.append("Mostly an offer for sale: existing holders are selling.")

    res = _combine({"Business quality": _rating(inp.business_quality_rating), "Revenue and profit growth": growth,
                    "Profitability": profitability, "Debt and balance sheet": debt,
                    "Cash flow and working capital": cashflow, "Promoter and management": promoter,
                    "Peer comparison": peers, "Valuation": valuation, "IPO structure and use of funds": structure},
                   FUNDAMENTAL_WEIGHTS, FUNDAMENTAL_BANDS)
    res["red_flags"] = flags
    res["metrics"] = {"revenue_cagr_pct": rc, "pat_cagr_pct": pc, "cfo_to_pat": ratio, "pe_premium_pct": premium}
    return res


# ------------------------------------------------------------------ listing score
@dataclass
class ListingInputs:
    gmp_pct: Optional[float] = None                       # final GMP as % of the issue price
    qib_sub: Optional[float] = None                       # times subscribed
    total_sub: Optional[float] = None
    nifty_ret_20d: Optional[float] = None                 # Nifty 50 return over the previous 20 trading days, %
    pe_premium_pct: Optional[float] = None                # IPO P/E premium to listed peers, %
    sector_sentiment_rating: Optional[float] = None       # 0-5
    issue_size_cr: Optional[float] = None


def score_listing(inp: ListingInputs) -> dict:
    res = _combine({
        "GMP": interp(inp.gmp_pct, [(-5, 0), (0, .1), (10, .4), (25, .75), (50, 1)]),
        "QIB subscription": interp(inp.qib_sub, [(0, 0), (1, .1), (5, .4), (20, .75), (80, 1)]),
        "Total subscription": interp(inp.total_sub, [(0, 0), (1, .1), (3, .35), (10, .65), (50, .9), (100, 1)]),
        "Market sentiment": interp(inp.nifty_ret_20d, [(-6, 0), (0, .5), (6, 1)]),
        "IPO valuation": interp(inp.pe_premium_pct, [(-10, 1), (0, .75), (20, .4), (50, .1), (80, 0)]),
        "Sector sentiment": _rating(inp.sector_sentiment_rating),
        "Issue size and liquidity": interp(inp.issue_size_cr, [(0, .9), (1000, .8), (2500, .5), (5000, .3)]),
    }, LISTING_WEIGHTS, LISTING_BANDS)
    res["red_flags"] = []
    return res