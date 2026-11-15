"""
IPOVision — Data Validation Engine
===================================

Comprehensive validation rules enforcing relational integrity, temporal precedence,
leakage isolation, financial consistency, and GMP fidelity across IPOVision datasets.

Educational Notes:
------------------
Financial machine learning models often suffer from subtle, invisible failure modes:
1. Target Leakage: Features inadvertently contain information derived from listing day.
2. Temporal Look-Ahead: Pre-close models trained on final subscription figures that
   were not known until after bidding closed.
3. Spurious Zeroes: Missing data (e.g., untracked GMP) replaced with 0.0, falsely
   teaching the model that market sentiment was neutral/par.
4. Entity Misalignment: Foreign keys in outcomes referencing nonexistent IPO records.

This module provides reusable, deterministic validation routines returning structured
`ValidationReport` objects. Invalid records are never silently dropped; errors are
explicitly surfaced with row indices and diagnostic messages.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd

from src.cleaning.ipo_id import is_valid_ipo_id


@dataclass
class ValidationIssue:
    """Represents a specific data quality error or warning."""
    level: str  # 'ERROR' (fatal invalidity) or 'WARNING' (suspicious / incomplete)
    category: str  # 'IPO', 'FINANCIAL', 'GMP', 'OUTCOME', 'STAGE', 'INTEGRITY'
    row_index: Optional[int]
    ipo_id: Optional[str]
    field: Optional[str]
    message: str

    def __str__(self) -> str:
        loc = f"Row {self.row_index}" if self.row_index is not None else "Dataset"
        if self.ipo_id:
            loc += f" [{self.ipo_id}]"
        if self.field:
            loc += f" field='{self.field}'"
        return f"[{self.level}] ({self.category}) {loc}: {self.message}"


@dataclass
class ValidationReport:
    """Structured report returned by all dataset validation routines."""
    dataset_name: str
    total_records: int
    is_valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "total_records": self.total_records,
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [str(e) for e in self.errors],
            "warnings": [str(w) for w in self.warnings],
        }


# ---------------------------------------------------------------------------
# Helper parsers & type checkers
# ---------------------------------------------------------------------------

def _is_empty_or_na(val: Any) -> bool:
    """Checks whether a value is None, NaN, empty string, or whitespace."""
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if pd.isna(val):
        return True
    return False


def _parse_date(val: Any) -> Optional[date]:
    """Attempts to parse an input into a datetime.date."""
    if _is_empty_or_na(val):
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        dt = pd.to_datetime(val, errors="coerce")
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None


def _parse_datetime(val: Any) -> Optional[datetime]:
    """Attempts to parse an input into a timezone-naive datetime."""
    if _is_empty_or_na(val):
        return None
    if isinstance(val, datetime):
        return val
    try:
        dt = pd.to_datetime(val, errors="coerce")
        if pd.isna(dt):
            return None
        return dt.to_pydatetime()
    except Exception:
        return None


def _to_float(val: Any) -> Optional[float]:
    """Safely converts to float or None."""
    if _is_empty_or_na(val):
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Specialized Validators
# ---------------------------------------------------------------------------

def validate_ipo_identification(df: pd.DataFrame, dataset_name: str) -> List[ValidationIssue]:
    """Validates presence and schema of ipo_id and company_name."""
    issues = []
    if "ipo_id" not in df.columns:
        issues.append(
            ValidationIssue(
                level="ERROR",
                category="IPO",
                row_index=None,
                ipo_id=None,
                field="ipo_id",
                message=f"Missing mandatory column 'ipo_id' in {dataset_name}.",
            )
        )
        return issues

    for idx, row in df.iterrows():
        raw_id = row.get("ipo_id")
        if _is_empty_or_na(raw_id):
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="IPO",
                    row_index=int(idx),
                    ipo_id=None,
                    field="ipo_id",
                    message="Missing mandatory 'ipo_id'.",
                )
            )
        elif not is_valid_ipo_id(str(raw_id)):
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="IPO",
                    row_index=int(idx),
                    ipo_id=str(raw_id),
                    field="ipo_id",
                    message=f"Invalid ipo_id format '{raw_id}'. Expected 'INMAIN-YYYY-NNNN'.",
                )
            )

    if "company_name" in df.columns:
        for idx, row in df.iterrows():
            cname = row.get("company_name")
            if _is_empty_or_na(cname) or len(str(cname).strip()) < 2:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="IPO",
                        row_index=int(idx),
                        ipo_id=str(row.get("ipo_id", "")),
                        field="company_name",
                        message=f"Invalid or missing company_name '{cname}'.",
                    )
                )

    return issues


def validate_timeline_dates(df: pd.DataFrame) -> List[ValidationIssue]:
    """
    Validates logical sequence of dates:
    issue_open_date <= issue_close_date <= listing_date.
    """
    issues = []
    for idx, row in df.iterrows():
        ipo_id = str(row.get("ipo_id", ""))
        open_dt = _parse_date(row.get("issue_open_date"))
        close_dt = _parse_date(row.get("issue_close_date"))
        list_dt = _parse_date(row.get("listing_date"))

        if "issue_open_date" in df.columns and open_dt is None and not _is_empty_or_na(row.get("issue_open_date")):
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="IPO",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="issue_open_date",
                    message=f"Unparseable issue_open_date: '{row.get('issue_open_date')}'.",
                )
            )

        if "issue_close_date" in df.columns and close_dt is None and not _is_empty_or_na(row.get("issue_close_date")):
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="IPO",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="issue_close_date",
                    message=f"Unparseable issue_close_date: '{row.get('issue_close_date')}'.",
                )
            )

        if open_dt and close_dt and open_dt > close_dt:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="IPO",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="issue_open_date",
                    message=f"issue_open_date ({open_dt}) is after issue_close_date ({close_dt}).",
                )
            )

        if close_dt and list_dt and close_dt > list_dt:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="IPO",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="listing_date",
                    message=f"issue_close_date ({close_dt}) is after listing_date ({list_dt}).",
                )
            )

    return issues


def validate_issue_pricing_and_size(df: pd.DataFrame) -> List[ValidationIssue]:
    """Validates issue price (> 0), issue size (> 0), fresh issue and OFS components."""
    issues = []
    for idx, row in df.iterrows():
        ipo_id = str(row.get("ipo_id", ""))

        if "issue_price" in df.columns:
            price_val = _to_float(row.get("issue_price"))
            if price_val is None:
                if not _is_empty_or_na(row.get("issue_price")):
                    issues.append(
                        ValidationIssue(
                            level="ERROR",
                            category="IPO",
                            row_index=int(idx),
                            ipo_id=ipo_id,
                            field="issue_price",
                            message=f"Non-numeric issue_price: '{row.get('issue_price')}'.",
                        )
                    )
            elif price_val <= 0.0:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="IPO",
                        row_index=int(idx),
                        ipo_id=ipo_id,
                        field="issue_price",
                        message=f"issue_price must be > 0. Found: {price_val}.",
                    )
                )

        if "issue_size_cr" in df.columns:
            size_val = _to_float(row.get("issue_size_cr"))
            if size_val is None:
                if not _is_empty_or_na(row.get("issue_size_cr")):
                    issues.append(
                        ValidationIssue(
                            level="ERROR",
                            category="IPO",
                            row_index=int(idx),
                            ipo_id=ipo_id,
                            field="issue_size_cr",
                            message=f"Non-numeric issue_size_cr: '{row.get('issue_size_cr')}'.",
                        )
                    )
            elif size_val <= 0.0:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="IPO",
                        row_index=int(idx),
                        ipo_id=ipo_id,
                        field="issue_size_cr",
                        message=f"issue_size_cr must be > 0. Found: {size_val}.",
                    )
                )

        for comp in ("fresh_issue_cr", "ofs_cr"):
            if comp in df.columns:
                comp_val = _to_float(row.get(comp))
                if comp_val is not None and comp_val < 0.0:
                    issues.append(
                        ValidationIssue(
                            level="ERROR",
                            category="IPO",
                            row_index=int(idx),
                            ipo_id=ipo_id,
                            field=comp,
                            message=f"{comp} cannot be negative. Found: {comp_val}.",
                        )
                    )

        if "price_band_low" in df.columns and "price_band_high" in df.columns:
            pb_low = _to_float(row.get("price_band_low"))
            pb_high = _to_float(row.get("price_band_high"))
            if pb_low and pb_high and pb_low > pb_high:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="IPO",
                        row_index=int(idx),
                        ipo_id=ipo_id,
                        field="price_band_low",
                        message=f"price_band_low ({pb_low}) is greater than price_band_high ({pb_high}).",
                    )
                )

    return issues


def validate_financial_consistency(df: pd.DataFrame) -> List[ValidationIssue]:
    """
    Validates company financials:
    - Debt must be non-negative (>= 0).
    - PAT and EBITDA can be negative (loss-making), but must be valid numbers.
    - Warns when financial values are provided without an associated period descriptor.
    """
    issues = []
    for idx, row in df.iterrows():
        ipo_id = str(row.get("ipo_id", ""))

        if "total_debt" in df.columns:
            debt = _to_float(row.get("total_debt"))
            if debt is not None and debt < 0.0:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="FINANCIAL",
                        row_index=int(idx),
                        ipo_id=ipo_id,
                        field="total_debt",
                        message=f"total_debt cannot be negative. Found: {debt}.",
                    )
                )

        for metric, period_col in (
            ("revenue", "revenue_period"),
            ("profit_after_tax", "pat_period"),
            ("ebitda", "ebitda_period"),
        ):
            if metric in df.columns:
                val = _to_float(row.get(metric))
                if val is not None and period_col in df.columns:
                    period_val = row.get(period_col)
                    if _is_empty_or_na(period_val):
                        issues.append(
                            ValidationIssue(
                                level="WARNING",
                                category="FINANCIAL",
                                row_index=int(idx),
                                ipo_id=ipo_id,
                                field=period_col,
                                message=f"Metric '{metric}'={val} provided without explicit '{period_col}'.",
                            )
                        )

        for mult_col in ("pe_ratio", "pb_ratio", "peer_pe_ratio", "peer_pb_ratio"):
            if mult_col in df.columns:
                m_val = _to_float(row.get(mult_col))
                if m_val is not None and m_val <= 0.0:
                    issues.append(
                        ValidationIssue(
                            level="WARNING",
                            category="FINANCIAL",
                            row_index=int(idx),
                            ipo_id=ipo_id,
                            field=mult_col,
                            message=f"Valuation multiple '{mult_col}'={m_val} is non-positive.",
                        )
                    )

    return issues


def validate_gmp_fidelity(df: pd.DataFrame) -> List[ValidationIssue]:
    """
    Enforces the Unofficial Data policy:
    1. Missing GMP is NEVER converted to zero.
    2. gmp_missing flag is synchronized (1 if GMP is NaN, 0 if present).
    3. gmp_recorded_at is a valid timestamp.
    """
    issues = []
    for idx, row in df.iterrows():
        ipo_id = str(row.get("ipo_id", ""))

        if "gmp" in df.columns:
            gmp_raw = row.get("gmp")
            is_missing = _is_empty_or_na(gmp_raw)

            if "gmp_missing" in df.columns:
                raw_flag = row.get("gmp_missing")
                flag_val = int(raw_flag) if str(raw_flag).strip() in ("0", "1") else None
                expected_flag = 1 if is_missing else 0
                if flag_val is not None and flag_val != expected_flag:
                    issues.append(
                        ValidationIssue(
                            level="ERROR",
                            category="GMP",
                            row_index=int(idx),
                            ipo_id=ipo_id,
                            field="gmp_missing",
                            message=(
                                f"gmp_missing flag ({flag_val}) contradicts gmp value "
                                f"('{gmp_raw}'). Expected {expected_flag}."
                            ),
                        )
                    )

            if not is_missing and "gmp_recorded_at" in df.columns:
                rec_dt = _parse_datetime(row.get("gmp_recorded_at"))
                if rec_dt is None and not _is_empty_or_na(row.get("gmp_recorded_at")):
                    issues.append(
                        ValidationIssue(
                            level="ERROR",
                            category="GMP",
                            row_index=int(idx),
                            ipo_id=ipo_id,
                            field="gmp_recorded_at",
                            message=f"Unparseable gmp_recorded_at timestamp: '{row.get('gmp_recorded_at')}'.",
                        )
                    )

    return issues


def validate_prediction_stage_and_leakage(df: pd.DataFrame) -> List[ValidationIssue]:
    """
    CRITICAL LEAKAGE AUDIT:
    1. prediction_stage must be 'pre_close' or 'post_close'.
    2. In 'pre_close', all subscription fields (QIB, NII, Retail, Overall) MUST BE NaN/None.
    3. If data_cutoff is specified, all observation timestamps must be <= data_cutoff.
    4. Outcome columns (listing_open_price, listing_gain_pct) MUST NOT exist in features dataset!
    """
    issues = []
    SUBSCRIPTION_FIELDS = [
        "qib_subscription",
        "nii_subscription",
        "retail_subscription",
        "overall_subscription",
    ]
    OUTCOME_FIELDS = ["listing_open_price", "listing_close_price", "listing_gain_pct", "listing_positive"]

    for col in OUTCOME_FIELDS:
        if col in df.columns:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="STAGE",
                    row_index=None,
                    ipo_id=None,
                    field=col,
                    message=f"TARGET LEAKAGE: Outcome column '{col}' is present in the feature store!",
                )
            )

    if "prediction_stage" not in df.columns:
        issues.append(
            ValidationIssue(
                level="ERROR",
                category="STAGE",
                row_index=None,
                ipo_id=None,
                field="prediction_stage",
                message="Missing mandatory column 'prediction_stage'.",
            )
        )
        return issues

    for idx, row in df.iterrows():
        ipo_id = str(row.get("ipo_id", ""))
        stage = str(row.get("prediction_stage", "")).strip().lower()

        if stage not in ("pre_close", "post_close"):
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="STAGE",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="prediction_stage",
                    message=f"Invalid prediction_stage '{stage}'. Must be 'pre_close' or 'post_close'.",
                )
            )
            continue

        if stage == "pre_close":
            for sub_col in SUBSCRIPTION_FIELDS:
                if sub_col in df.columns:
                    val = _to_float(row.get(sub_col))
                    if val is not None:
                        issues.append(
                            ValidationIssue(
                                level="ERROR",
                                category="STAGE",
                                row_index=int(idx),
                                ipo_id=ipo_id,
                                field=sub_col,
                                message=(
                                    f"LOOK-AHEAD LEAKAGE in pre_close stage: Subscription field "
                                    f"'{sub_col}' has value {val}. Subscription metrics are forbidden before close!"
                                ),
                            )
                        )

        # Temporal Cutoff Check
        if "data_cutoff" in df.columns:
            cutoff_dt = _parse_datetime(row.get("data_cutoff"))
            if cutoff_dt is None:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="STAGE",
                        row_index=int(idx),
                        ipo_id=ipo_id,
                        field="data_cutoff",
                        message=f"Missing or invalid data_cutoff: '{row.get('data_cutoff')}'.",
                    )
                )
            elif "gmp_recorded_at" in df.columns:
                gmp_dt = _parse_datetime(row.get("gmp_recorded_at"))
                if gmp_dt and gmp_dt > cutoff_dt:
                    issues.append(
                        ValidationIssue(
                            level="ERROR",
                            category="STAGE",
                            row_index=int(idx),
                            ipo_id=ipo_id,
                            field="gmp_recorded_at",
                            message=(
                                f"TEMPORAL LEAKAGE: gmp_recorded_at ({gmp_dt}) is strictly after "
                                f"the frozen data_cutoff ({cutoff_dt})."
                            ),
                        )
                    )

    return issues


def validate_outcomes_consistency(df: pd.DataFrame) -> List[ValidationIssue]:
    """
    Verifies mathematical and classification consistency in `ipo_outcomes.csv`:
    1. issue_price > 0 and listing_open_price > 0.
    2. listing_gain_pct = ((listing_open_price - issue_price) / issue_price) * 100.
    3. listing_positive = 1 if listing_gain_pct > 0.0 else 0 (at par/zero gain = 0).
    """
    issues = []
    for idx, row in df.iterrows():
        ipo_id = str(row.get("ipo_id", ""))
        issue_p = _to_float(row.get("issue_price"))
        open_p = _to_float(row.get("listing_open_price"))
        gain_pct = _to_float(row.get("listing_gain_pct"))
        pos_target = row.get("listing_positive")

        if issue_p is None or issue_p <= 0.0:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="OUTCOME",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="issue_price",
                    message=f"Missing or non-positive issue_price: {issue_p}.",
                )
            )
            continue

        if open_p is None or open_p <= 0.0:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="OUTCOME",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="listing_open_price",
                    message=f"Missing or non-positive listing_open_price: {open_p}.",
                )
            )
            continue

        expected_gain = ((open_p - issue_p) / issue_p) * 100.0
        if gain_pct is None:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="OUTCOME",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="listing_gain_pct",
                    message=f"Missing listing_gain_pct (expected {expected_gain:.4f}%).",
                )
            )
        elif abs(gain_pct - expected_gain) > 0.15:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="OUTCOME",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="listing_gain_pct",
                    message=(
                        f"listing_gain_pct mismatch: provided {gain_pct}%, "
                        f"calculated {expected_gain:.4f}% from issue={issue_p}, open={open_p}."
                    ),
                )
            )

        expected_pos = 1 if expected_gain > 0.0 else 0
        try:
            pos_int = int(pos_target)
            if pos_int != expected_pos:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="OUTCOME",
                        row_index=int(idx),
                        ipo_id=ipo_id,
                        field="listing_positive",
                        message=(
                            f"listing_positive inconsistency: provided {pos_int}, "
                            f"expected {expected_pos} for gain of {expected_gain:.4f}%."
                        ),
                    )
                )
        except (ValueError, TypeError):
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="OUTCOME",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="listing_positive",
                    message=f"Non-integer listing_positive target: '{pos_target}'.",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# High-level Dataset Validators
# ---------------------------------------------------------------------------

def validate_features_dataset(df: pd.DataFrame) -> ValidationReport:
    """Validates the entire `ipo_features.csv` DataFrame."""
    issues: List[ValidationIssue] = []

    # 1. Uniqueness check on (ipo_id, prediction_stage, data_cutoff)
    if "ipo_id" in df.columns and "prediction_stage" in df.columns:
        subset = ["ipo_id", "prediction_stage"]
        if "data_cutoff" in df.columns:
            subset.append("data_cutoff")
        dups = df[df.duplicated(subset=subset, keep=False)]
        if not dups.empty:
            for idx in dups.index:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="IPO",
                        row_index=int(idx),
                        ipo_id=str(df.loc[idx, "ipo_id"]),
                        field=None,
                        message=f"Duplicate snapshot record detected for key {subset}.",
                    )
                )

    issues.extend(validate_ipo_identification(df, "ipo_features"))
    issues.extend(validate_timeline_dates(df))
    issues.extend(validate_issue_pricing_and_size(df))
    issues.extend(validate_financial_consistency(df))
    issues.extend(validate_gmp_fidelity(df))
    issues.extend(validate_prediction_stage_and_leakage(df))

    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level == "WARNING"]

    return ValidationReport(
        dataset_name="ipo_features",
        total_records=len(df),
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_outcomes_dataset(df: pd.DataFrame) -> ValidationReport:
    """Validates the entire `ipo_outcomes.csv` DataFrame."""
    issues: List[ValidationIssue] = []

    # 1. Primary key uniqueness: ipo_id must be strictly unique
    if "ipo_id" in df.columns:
        dups = df[df.duplicated(subset=["ipo_id"], keep=False)]
        if not dups.empty:
            for idx in dups.index:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="OUTCOME",
                        row_index=int(idx),
                        ipo_id=str(df.loc[idx, "ipo_id"]),
                        field="ipo_id",
                        message="Duplicate ipo_id in outcomes dataset. Only 1 outcome per IPO allowed.",
                    )
                )

    issues.extend(validate_ipo_identification(df, "ipo_outcomes"))
    issues.extend(validate_outcomes_consistency(df))

    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level == "WARNING"]

    return ValidationReport(
        dataset_name="ipo_outcomes",
        total_records=len(df),
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_gmp_history_dataset(df: pd.DataFrame) -> ValidationReport:
    """Validates the `ipo_gmp_history.csv` time series dataset."""
    issues: List[ValidationIssue] = []

    # Duplicates check on (ipo_id, source, recorded_at)
    if all(c in df.columns for c in ("ipo_id", "source", "recorded_at")):
        dups = df[df.duplicated(subset=["ipo_id", "source", "recorded_at"], keep=False)]
        if not dups.empty:
            for idx in dups.index:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="GMP",
                        row_index=int(idx),
                        ipo_id=str(df.loc[idx, "ipo_id"]),
                        field=None,
                        message="Duplicate GMP observation for same (ipo_id, source, recorded_at).",
                    )
                )

    issues.extend(validate_ipo_identification(df, "ipo_gmp_history"))

    for idx, row in df.iterrows():
        ipo_id = str(row.get("ipo_id", ""))
        gmp_val = _to_float(row.get("gmp"))
        rec_val = row.get("recorded_at")

        if gmp_val is None:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="GMP",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="gmp",
                    message="Missing or non-numeric GMP in history record.",
                )
            )

        if _parse_datetime(rec_val) is None:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="GMP",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="recorded_at",
                    message=f"Missing or unparseable recorded_at: '{rec_val}'.",
                )
            )

        source_val = row.get("source")
        if _is_empty_or_na(source_val) or len(str(source_val).strip()) < 2:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="GMP",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="source",
                    message=f"Missing or invalid GMP source: '{source_val}'.",
                )
            )

    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level == "WARNING"]

    return ValidationReport(
        dataset_name="ipo_gmp_history",
        total_records=len(df),
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_registry_dataset(df: pd.DataFrame) -> ValidationReport:
    """Validates the master `ipo_registry.csv`."""
    issues: List[ValidationIssue] = []

    if "ipo_id" in df.columns:
        dups = df[df.duplicated(subset=["ipo_id"], keep=False)]
        if not dups.empty:
            for idx in dups.index:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="IPO",
                        row_index=int(idx),
                        ipo_id=str(df.loc[idx, "ipo_id"]),
                        field="ipo_id",
                        message="Duplicate ipo_id in master registry.",
                    )
                )

    issues.extend(validate_ipo_identification(df, "ipo_registry"))
    issues.extend(validate_timeline_dates(df))

    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level == "WARNING"]

    return ValidationReport(
        dataset_name="ipo_registry",
        total_records=len(df),
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_feature_sources_dataset(df: pd.DataFrame) -> ValidationReport:
    """Validates the `ipo_feature_sources.csv` data provenance table."""
    issues: List[ValidationIssue] = []

    issues.extend(validate_ipo_identification(df, "ipo_feature_sources"))

    VALID_STATUSES = {"unverified", "llm_extracted", "verified"}

    for idx, row in df.iterrows():
        ipo_id = str(row.get("ipo_id", ""))
        stage = str(row.get("prediction_stage", "")).strip().lower()
        if stage not in ("pre_close", "post_close"):
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="STAGE",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="prediction_stage",
                    message=f"Invalid prediction_stage '{stage}' in provenance row.",
                )
            )

        status = str(row.get("verification_status", "")).strip().lower()
        if status and status not in VALID_STATUSES:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    category="INTEGRITY",
                    row_index=int(idx),
                    ipo_id=ipo_id,
                    field="verification_status",
                    message=f"Invalid verification_status '{status}'. Must be one of {VALID_STATUSES}.",
                )
            )

        for req in ("feature_name", "feature_value", "source_name"):
            if _is_empty_or_na(row.get(req)):
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="INTEGRITY",
                        row_index=int(idx),
                        ipo_id=ipo_id,
                        field=req,
                        message=f"Missing mandatory provenance field '{req}'.",
                    )
                )

    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level == "WARNING"]

    return ValidationReport(
        dataset_name="ipo_feature_sources",
        total_records=len(df),
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def check_referential_integrity(
    features_df: pd.DataFrame,
    outcomes_df: Optional[pd.DataFrame] = None,
    gmp_df: Optional[pd.DataFrame] = None,
    registry_df: Optional[pd.DataFrame] = None,
) -> List[ValidationIssue]:
    """
    Checks that all foreign key ipo_ids exist in the registry/features table.
    """
    issues = []
    registered_ids: Set[str] = set()
    if registry_df is not None and "ipo_id" in registry_df.columns:
        registered_ids.update(registry_df["ipo_id"].dropna().astype(str).str.strip())
    elif "ipo_id" in features_df.columns:
        registered_ids.update(features_df["ipo_id"].dropna().astype(str).str.strip())

    if outcomes_df is not None and "ipo_id" in outcomes_df.columns:
        for idx, val in outcomes_df["ipo_id"].items():
            s_val = str(val).strip()
            if s_val and s_val not in registered_ids:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        category="INTEGRITY",
                        row_index=int(idx),
                        ipo_id=s_val,
                        field="ipo_id",
                        message=f"Foreign key '{s_val}' in outcomes does not exist in master registry/features.",
                    )
                )

    if gmp_df is not None and "ipo_id" in gmp_df.columns:
        for idx, val in gmp_df["ipo_id"].items():
            s_val = str(val).strip()
            if s_val and s_val not in registered_ids:
                issues.append(
                    ValidationIssue(
                        level="WARNING",
                        category="INTEGRITY",
                        row_index=int(idx),
                        ipo_id=s_val,
                        field="ipo_id",
                        message=f"Foreign key '{s_val}' in gmp_history does not exist in master registry/features.",
                    )
                )

    return issues

