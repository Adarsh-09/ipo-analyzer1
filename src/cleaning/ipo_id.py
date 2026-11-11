"""
IPOVision — IPO Identifier & Registry System
============================================

Implements the official IPO identifier convention and master registry management
for Indian Mainboard IPOs in IPOVision.

Educational Notes:
------------------
A deterministic, immutable identifier (`ipo_id`) is crucial for financial data pipelines.
Company names change, legal suffixes vary across data providers ('Swiggy Ltd' vs
'Swiggy Limited'), and exchange ticker symbols ('SWIGGY') are not assigned until days
before listing.

IPO ID Format:
    `INMAIN-YYYY-NNNN`
    - `INMAIN`: Indian Mainboard market segment indicator (excludes SME/BSE SME).
    - `YYYY`: 4-digit calendar year of the issue/listing (e.g., 2024, 2025).
    - `NNNN`: 4-digit zero-padded sequential number assigned chronologically (0001, 0002).

Design Guarantees:
    1. Uniqueness: Each IPO receives a permanently unique ID.
    2. Immutability: An ID remains constant even if company name or ticker changes.
    3. No Row Numbers: Row indexes are volatile and must never be used as IDs.
    4. Registry-Backed: All IDs are registered in `data/processed/ipo_registry.csv`.

Usage:
    from src.cleaning.ipo_id import IPORegistryManager, is_valid_ipo_id

    registry = IPORegistryManager()
    ipo_id = registry.get_or_create_ipo_id(
        company_name="Swiggy Limited",
        year=2024,
        symbol="SWIGGY",
        issue_open_date="2024-11-06",
        issue_close_date="2024-11-08"
    )
    # Returns 'INMAIN-2024-0001'
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

from src.config import get_path, get_project_root

logger = logging.getLogger(__name__)

# Canonical Regex: INMAIN-YYYY-NNNN
IPO_ID_REGEX = re.compile(r"^INMAIN-(\d{4})-(\d{4})$")

# Common legal entity structure suffixes in Indian corporate names
CORPORATE_SUFFIXES = [
    r"\bLIMITED\b",
    r"\bLTD\.?\b",
    r"\bPRIVATE\b",
    r"\bPVT\.?\b",
    r"\bINDIA\b",
    r"\(INDIA\)",
    r"\bLLP\b",
    r"\bCORPORATION\b",
    r"\bCORP\.?\b",
    r"\bCOMPANY\b",
    r"\bCO\.?\b",
]

REGISTRY_COLUMNS = [
    "ipo_id",
    "company_name",
    "symbol",
    "issue_open_date",
    "issue_close_date",
    "listing_date",
]


def is_valid_ipo_id(ipo_id: str) -> bool:
    """
    Validates whether an ID matches the canonical format 'INMAIN-YYYY-NNNN'.

    Args:
        ipo_id: String identifier to check.

    Returns:
        True if valid, False otherwise.
    """
    if not isinstance(ipo_id, str):
        return False
    return bool(IPO_ID_REGEX.match(ipo_id.strip()))


def parse_ipo_id(ipo_id: str) -> Tuple[str, int, int]:
    """
    Parses a canonical IPO ID into (market_prefix, year, sequence).

    Args:
        ipo_id: Canonical ID string (e.g. 'INMAIN-2024-0001').

    Returns:
        Tuple of (market: str, year: int, sequence_number: int).

    Raises:
        ValueError: If ipo_id does not match the canonical format.
    """
    match = IPO_ID_REGEX.match(ipo_id.strip())
    if not match:
        raise ValueError(
            f"Invalid ipo_id '{ipo_id}'. Expected format 'INMAIN-YYYY-NNNN' (e.g. 'INMAIN-2024-0001')."
        )
    market = "INMAIN"
    year = int(match.group(1))
    sequence = int(match.group(2))
    return market, year, sequence


def format_ipo_id(year: int, sequence_number: int) -> str:
    """
    Formats a year and sequence number into a canonical IPO ID.

    Args:
        year: 4-digit calendar year (e.g. 2024).
        sequence_number: Positive sequence integer (1 to 9999).

    Returns:
        Canonical string e.g. 'INMAIN-2024-0001'.
    """
    if not (1990 <= year <= 2100):
        raise ValueError(f"Year {year} is out of realistic range (1990-2100).")
    if not (1 <= sequence_number <= 9999):
        raise ValueError(f"Sequence number {sequence_number} must be between 1 and 9999.")
    return f"INMAIN-{year:04d}-{sequence_number:04d}"


def normalize_company_name(name: str) -> str:
    """
    Standardizes a company name for fuzzy/exact matching in the registry.
    Strips corporate legal suffixes, non-alphanumeric characters, and excessive whitespace.

    Examples:
        'Swiggy Limited' -> 'SWIGGY'
        'Tata Technologies Ltd.' -> 'TATA TECHNOLOGIES'
        'Hyundai Motor India Limited' -> 'HYUNDAI MOTOR'
    """
    if not name:
        return ""
    cleaned = name.upper().strip()
    for pattern in CORPORATE_SUFFIXES:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class IPORegistryManager:
    """
    Manages the master IPO registry (`data/processed/ipo_registry.csv`).
    Provides atomic registration, sequence generation, and multi-key lookups.
    """

    def __init__(self, registry_path: Optional[Path] = None):
        if registry_path is None:
            try:
                self.registry_path = get_path("data_processed") / "ipo_registry.csv"
            except Exception:
                self.registry_path = get_project_root() / "data" / "processed" / "ipo_registry.csv"
        else:
            self.registry_path = Path(registry_path)

        self._ensure_registry_exists()

    def _ensure_registry_exists(self) -> None:
        """Creates the registry file with headers if it does not yet exist."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            df = pd.DataFrame(columns=REGISTRY_COLUMNS)
            df.to_csv(self.registry_path, index=False, encoding="utf-8")
            logger.info("Initialized empty IPO registry at %s", self.registry_path)

    def load_registry(self) -> pd.DataFrame:
        """Loads the registry DataFrame, ensuring correct column dtypes."""
        if not self.registry_path.exists() or os.path.getsize(self.registry_path) == 0:
            return pd.DataFrame(columns=REGISTRY_COLUMNS)
        df = pd.read_csv(self.registry_path, dtype=str, keep_default_na=False)
        for col in REGISTRY_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[REGISTRY_COLUMNS]

    def _save_registry(self, df: pd.DataFrame) -> None:
        """Atomically saves the registry file via a temporary swap."""
        tmp_path = self.registry_path.with_suffix(".tmp")
        df.to_csv(tmp_path, index=False, encoding="utf-8")
        tmp_path.replace(self.registry_path)

    def get_next_sequence_number(self, year: int) -> int:
        """
        Determines the next available 1-based sequential number for the specified year.
        """
        df = self.load_registry()
        if df.empty or "ipo_id" not in df.columns:
            return 1

        year_prefix = f"INMAIN-{year:04d}-"
        matching_ids = df[df["ipo_id"].str.startswith(year_prefix)]["ipo_id"]
        if matching_ids.empty:
            return 1

        sequences = []
        for val in matching_ids:
            try:
                seq = int(val.split("-")[2])
                sequences.append(seq)
            except (IndexError, ValueError):
                continue

        return (max(sequences) + 1) if sequences else 1

    def lookup_ipo_id(
        self,
        company_name: Optional[str] = None,
        symbol: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Optional[str]:
        """
        Looks up an existing IPO ID by symbol, company name, or normalized name.

        Args:
            company_name: Full or partial company name.
            symbol: Exchange ticker symbol (e.g. 'SWIGGY').
            year: Optional 4-digit issue year to narrow the search.

        Returns:
            The matched canonical ipo_id string or None if not found.
        """
        df = self.load_registry()
        if df.empty:
            return None

        # 1. Exact Symbol Match (most specific)
        if symbol and symbol.strip():
            sym_clean = symbol.strip().upper()
            match = df[df["symbol"].str.upper() == sym_clean]
            if not match.empty:
                return match.iloc[0]["ipo_id"]

        # 2. Exact Company Name Match
        if company_name and company_name.strip():
            clean_name = company_name.strip().upper()
            match = df[df["company_name"].str.upper() == clean_name]
            if not match.empty:
                return match.iloc[0]["ipo_id"]

            # 3. Normalized Company Name Match
            norm_target = normalize_company_name(clean_name)
            if norm_target:
                for _, row in df.iterrows():
                    existing_norm = normalize_company_name(str(row["company_name"]))
                    if existing_norm and (norm_target == existing_norm):
                        if year is None:
                            return row["ipo_id"]
                        try:
                            _, reg_year, _ = parse_ipo_id(row["ipo_id"])
                            if reg_year == year:
                                return row["ipo_id"]
                        except ValueError:
                            pass

        return None

    def register_ipo(
        self,
        company_name: str,
        year: int,
        symbol: Optional[str] = None,
        issue_open_date: Optional[str] = None,
        issue_close_date: Optional[str] = None,
        listing_date: Optional[str] = None,
    ) -> str:
        """
        Registers a new IPO, assigns the next canonical ID, and saves to the registry.

        Raises:
            ValueError: If the company name is empty, year is invalid, or the IPO
                        is already registered (use get_or_create_ipo_id instead).
        """
        if not company_name or not company_name.strip():
            raise ValueError("company_name must not be empty.")

        existing = self.lookup_ipo_id(company_name=company_name, symbol=symbol, year=year)
        if existing:
            raise ValueError(
                f"IPO for '{company_name}' (symbol='{symbol}') is already registered with ID: {existing}"
            )

        next_seq = self.get_next_sequence_number(year)
        new_id = format_ipo_id(year, next_seq)

        df = self.load_registry()
        new_row = {
            "ipo_id": new_id,
            "company_name": company_name.strip(),
            "symbol": symbol.strip().upper() if symbol and symbol.strip() else "",
            "issue_open_date": issue_open_date or "",
            "issue_close_date": issue_close_date or "",
            "listing_date": listing_date or "",
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        self._save_registry(df)
        logger.info("Registered new IPO %s -> %s", company_name, new_id)
        return new_id

    def get_or_create_ipo_id(
        self,
        company_name: str,
        year: int,
        symbol: Optional[str] = None,
        issue_open_date: Optional[str] = None,
        issue_close_date: Optional[str] = None,
        listing_date: Optional[str] = None,
    ) -> str:
        """
        Idempotent lookup or registration.
        If the IPO is already present in the registry, returns its existing ID.
        Otherwise, registers it with a new sequential ID.
        """
        existing = self.lookup_ipo_id(company_name=company_name, symbol=symbol, year=year)
        if existing:
            return existing
        return self.register_ipo(
            company_name=company_name,
            year=year,
            symbol=symbol,
            issue_open_date=issue_open_date,
            issue_close_date=issue_close_date,
            listing_date=listing_date,
        )
