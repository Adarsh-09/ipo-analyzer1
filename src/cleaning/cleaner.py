"""
IPOVision — Data Cleaning & Normalization Engine
=================================================

Provides deterministic, reproducible data cleaning routines for Indian Mainboard IPOs:
- Multi-format date parsing (e.g., '11 to 13 Mar, 2024', 'Wed, Dec 13, 2023', '2024-11-06').
- Numeric conversion with unit standardization (₹ Crore for totals, ₹ per share for prices).
- Company entity normalization and SME tag stripping.
- Leakage neutralization (enforces NaN on subscriptions during pre_close).
- Non-destructive processing: never mutates inputs, records audit logs of operations.

Educational Notes:
------------------
Raw web-scraped financial data is messy:
1. Dates appear in colloquial formats: '11-Nov', '29-Oct to 5-Nov', or with timestamps.
2. Financials mix notations: '₹22.98 Cr', '1,234.56', '₹111 per share', '15.5%'.
3. Missing indicators vary: '--', 'N/A', '-', 'None', '[email protected]'.
4. Critical Rule: Missing values must NEVER be imputed with 0.0 during cleaning.
   Missingness must remain explicitly NaN to preserve downstream statistical validity.
"""

from datetime import date, datetime
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

logger = logging.getLogger(__name__)

# Month name mapping for Indian financial portal date strings
MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


class IPOCleaner:
    """
    Standardizes raw financial records into schema-compliant DataFrames.
    """

    # ------------------------------------------------------------------
    # Atomic Field Cleaning Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def clean_number(val: Any) -> Optional[float]:
        """
        Extracts a clean floating point number from messy text representations.

        Handles:
            - '₹22.98 Cr'     -> 22.98
            - '1,234.56'      -> 1234.56
            - '₹111 per share' -> 111.0
            - '15.5%'         -> 15.5
            - '-2,350.50'     -> -2350.50 (negative profit/loss preserved!)
            - '-' or 'N/A'    -> None

        Returns:
            Float value or None if unparseable/missing.
        """
        if val is None or pd.isna(val):
            return None
        if isinstance(val, (int, float)):
            if isinstance(val, float) and math.isnan(val):
                return None
            return float(val)

        s = str(val).strip()
        if not s or s in ("-", "--", "—", "N/A", "NA", "null", "None", "?"):
            return None

        # Remove word suffixes first
        cleaned = re.sub(
            r"\b(cr|crore|crores|shares|per\s+share|times|x|lakh|lakhs)\b",
            "",
            s,
            flags=re.IGNORECASE,
        )

        # Remove currency symbols, commas, percentage signs, and whitespace
        cleaned = re.sub(r"[₹,$%,\s]", "", cleaned)

        # Find first valid floating number (handles leading plus/minus)
        match = re.search(r"[-+]?\d*\.?\d+", cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    @staticmethod
    def parse_subscription_multiple(val: Any) -> Optional[float]:
        """
        Parses subscription rates like '12.79x', '0.95x', or '12.795th Nov'.
        Extracts the leading decimal value up to 2 decimal places.
        """
        if val is None or pd.isna(val):
            return None
        s = str(val).strip().lower().replace("x", "").replace(",", "")
        if not s or s in ("-", "--", "—", "n/a", "na", ""):
            return None

        match = re.match(r"^(\d+(?:\.\d{1,2})?)", s)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def clean_date(val: Any, default_year: Optional[int] = None) -> Optional[str]:
        """
        Normalizes varying date strings into canonical 'YYYY-MM-DD'.

        Handles:
            - '2024-11-06' -> '2024-11-06'
            - 'Wed, Dec 13, 2023' -> '2023-12-13'
            - '11 to 13 Mar, 2024' -> '2024-03-11' (takes start date)
            - '11-Nov' -> 'YYYY-11-11' (if default_year provided)
        """
        if val is None or pd.isna(val):
            return None
        if isinstance(val, (date, datetime)):
            return val.strftime("%Y-%m-%d")

        s = str(val).strip()
        if not s or s in ("-", "--", "—", "N/A", "NA"):
            return None

        # ISO format: YYYY-MM-DD
        iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
        if iso_match:
            try:
                y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
                return date(y, m, d).strftime("%Y-%m-%d")
            except ValueError:
                return None

        # Try pandas parser for other standard formats
        try:
            dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
            if not pd.isna(dt):
                return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

        # Pattern: '11 to 13 Mar, 2024' -> take first day '11 Mar, 2024'
        range_match = re.search(
            r"(\d{1,2})\s+to\s+\d{1,2}\s+([A-Za-z]+),?\s*(\d{4})",
            s,
            re.IGNORECASE,
        )
        if range_match:
            day = int(range_match.group(1))
            month_str = range_match.group(2).lower()
            year = int(range_match.group(3))
            month = MONTH_MAP.get(month_str[:3], 1)
            try:
                return date(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Pattern: '11-Nov' with default_year
        short_match = re.search(r"(\d{1,2})-([A-Za-z]{3})", s, re.IGNORECASE)
        if short_match:
            day = int(short_match.group(1))
            month_str = short_match.group(2).lower()
            year = default_year or datetime.now().year
            month = MONTH_MAP.get(month_str, 1)
            try:
                return date(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                pass

        return None

    @staticmethod
    def clean_datetime(val: Any) -> Optional[str]:
        """Normalizes timestamps into ISO 8601 string 'YYYY-MM-DDTHH:MM:SS'."""
        if val is None or pd.isna(val):
            return None
        if isinstance(val, datetime):
            return val.strftime("%Y-%m-%dT%H:%M:%S")
        if isinstance(val, date):
            return datetime(val.year, val.month, val.day).strftime("%Y-%m-%dT%H:%M:%S")

        s = str(val).strip()
        if not s or s in ("-", "--", "—", "N/A", "NA"):
            return None

        try:
            dt = pd.to_datetime(s, errors="coerce")
            if not pd.isna(dt):
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            pass
        return None

    @staticmethod
    def clean_company_name(raw_name: str) -> Dict[str, Any]:
        """
        Sanitizes company name and checks for SME indicators.
        """
        if not raw_name:
            return {"company_name": "", "is_sme": False}

        is_sme = bool(re.search(r"\b(SME|BSE SME|NSE SME)\b", raw_name, re.I))

        # Strip SME markers and web scraping artifacts like [email protected]
        clean = re.sub(r"(BSE SME|NSE SME|SME|\[email\s*protected\])", "", raw_name, flags=re.I)
        clean = re.sub(r"\s+", " ", clean).strip()

        return {"company_name": clean, "is_sme": is_sme}

    # ------------------------------------------------------------------
    # Dataset Cleaning Routines
    # ------------------------------------------------------------------

    def clean_features_df(self, raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Cleans and standardizes a raw features DataFrame into schema compliance.
        Returns a (cleaned_df, audit_log) tuple.
        """
        df = raw_df.copy()
        log = []
        log.append(f"Starting clean_features_df with {len(df)} rows.")

        # Ensure prediction_stage is standardized
        if "prediction_stage" in df.columns:
            df["prediction_stage"] = (
                df["prediction_stage"].astype(str).str.strip().str.lower()
            )

        # Dates
        date_cols = ["issue_open_date", "issue_close_date", "listing_date"]
        for col in date_cols:
            if col in df.columns:
                df[col] = df[col].apply(self.clean_date)
                log.append(f"Normalized date column: '{col}'.")

        # Datetime
        for col in ("data_cutoff", "gmp_recorded_at"):
            if col in df.columns:
                df[col] = df[col].apply(self.clean_datetime)

        # Monetary and Numerical Columns
        numeric_cols = [
            "issue_price", "price_band_low", "price_band_high", "issue_size_cr",
            "fresh_issue_cr", "ofs_cr", "revenue", "profit_after_tax", "ebitda",
            "total_debt", "net_worth", "cash_flow_from_operations", "eps", "nav",
            "pe_ratio", "pb_ratio", "peer_pe_ratio", "peer_pb_ratio",
            "gmp", "gmp_change",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(self.clean_number)

        # Subscription columns
        sub_cols = [
            "qib_subscription", "nii_subscription",
            "retail_subscription", "overall_subscription",
        ]
        for col in sub_cols:
            if col in df.columns:
                df[col] = df[col].apply(self.parse_subscription_multiple)

        # STRICT LEAKAGE PREVENTION: In pre_close, force subscriptions to NaN!
        if "prediction_stage" in df.columns:
            pre_close_mask = df["prediction_stage"] == "pre_close"
            for col in sub_cols:
                if col in df.columns:
                    leak_count = df.loc[pre_close_mask, col].notna().sum()
                    if leak_count > 0:
                        df.loc[pre_close_mask, col] = None
                        log.append(
                            f"LEAKAGE REMOVED: Cleared {leak_count} subscription values in pre_close stage for '{col}'."
                        )

        # GMP Missing Flag synchronization
        if "gmp" in df.columns:
            df["gmp_missing"] = df["gmp"].apply(lambda v: 1 if (v is None or pd.isna(v)) else 0)
            log.append("Synchronized gmp_missing flag with observed GMP values.")

        # Strip whitespace in text fields
        text_cols = ["company_name", "symbol", "exchange", "gmp_source", "revenue_period", "pat_period", "ebitda_period"]
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].apply(lambda s: str(s).strip() if (s is not None and not pd.isna(s)) else None)

        log.append(f"Completed clean_features_df: {len(df)} records processed.")
        return df, log

    def clean_outcomes_df(self, raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Cleans and verifies `ipo_outcomes.csv`:
        - Calculates listing_gain_pct = ((open - issue) / issue) * 100.
        - Calculates listing_positive = 1 if listing_gain_pct > 0 else 0.
        """
        df = raw_df.copy()
        log = []
        log.append(f"Starting clean_outcomes_df with {len(df)} rows.")

        if "listing_date" in df.columns:
            df["listing_date"] = df["listing_date"].apply(self.clean_date)

        for col in ("issue_price", "listing_open_price", "listing_close_price"):
            if col in df.columns:
                df[col] = df[col].apply(self.clean_number)

        # Deterministic Target Calculation
        if "issue_price" in df.columns and "listing_open_price" in df.columns:
            mask = df["issue_price"].notna() & df["listing_open_price"].notna() & (df["issue_price"] > 0)
            df.loc[mask, "listing_gain_pct"] = (
                ((df.loc[mask, "listing_open_price"] - df.loc[mask, "issue_price"]) / df.loc[mask, "issue_price"]) * 100.0
            ).round(4)

            df.loc[mask, "listing_positive"] = (
                df.loc[mask, "listing_gain_pct"] > 0.0
            ).astype(int)
            log.append(f"Computed deterministic listing_gain_pct and listing_positive for {mask.sum()} records.")

        log.append(f"Completed clean_outcomes_df: {len(df)} records processed.")
        return df, log

    def clean_gmp_history_df(self, raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Cleans and standardizes the time series GMP dataset."""
        df = raw_df.copy()
        log = []
        log.append(f"Starting clean_gmp_history_df with {len(df)} rows.")

        if "recorded_at" in df.columns:
            df["recorded_at"] = df["recorded_at"].apply(self.clean_datetime)

        if "gmp" in df.columns:
            df["gmp"] = df["gmp"].apply(self.clean_number)

        for col in ("source", "notes", "source_url"):
            if col in df.columns:
                df[col] = df[col].apply(lambda s: str(s).strip() if (s is not None and not pd.isna(s)) else None)

        log.append(f"Completed clean_gmp_history_df: {len(df)} records processed.")
        return df, log

    @staticmethod
    def deduplicate(
        df: pd.DataFrame,
        subset: List[str],
        keep: str = "last",
    ) -> Tuple[pd.DataFrame, int]:
        """
        Deduplicates a DataFrame based on key columns, preserving order.
        """
        valid_cols = [c for c in subset if c in df.columns]
        if not valid_cols:
            return df, 0
        before = len(df)
        deduped = df.drop_duplicates(subset=valid_cols, keep=keep).reset_index(drop=True)
        dropped = before - len(deduped)
        return deduped, dropped
