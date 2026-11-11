"""
IPOVision — Data Cleaning, Validation & Registry Package
========================================================

Exported Symbols:
-----------------
Identifiers & Registry:
    - is_valid_ipo_id: Regex validator for 'INMAIN-YYYY-NNNN'.
    - parse_ipo_id: Deconstructs an ID into (market, year, sequence).
    - format_ipo_id: Formats year and sequence into canonical ID.
    - normalize_company_name: Strips legal corporate suffixes for entity matching.
    - IPORegistryManager: Manages master IPO directory and atomic registration.

Data Cleaning:
    - IPOCleaner: Robust numeric, date, datetime, and subscription parsing.

Dataset Management:
    - DatasetManager: Safe atomic I/O, deduplication, and quality reporting.

Validation:
    - ValidationIssue, ValidationReport
    - validate_features_dataset
    - validate_outcomes_dataset
    - validate_gmp_history_dataset
    - validate_registry_dataset
    - validate_feature_sources_dataset
    - check_referential_integrity
"""

from src.cleaning.ipo_id import (
    is_valid_ipo_id,
    parse_ipo_id,
    format_ipo_id,
    normalize_company_name,
    IPORegistryManager,
)
from src.cleaning.cleaner import (
    IPOCleaner,
)
from src.cleaning.dataset_manager import (
    DatasetManager,
)
from src.cleaning.validators import (
    ValidationIssue,
    ValidationReport,
    validate_features_dataset,
    validate_outcomes_dataset,
    validate_gmp_history_dataset,
    validate_registry_dataset,
    validate_feature_sources_dataset,
    check_referential_integrity,
)

__all__ = [
    "is_valid_ipo_id",
    "parse_ipo_id",
    "format_ipo_id",
    "normalize_company_name",
    "IPORegistryManager",
    "IPOCleaner",
    "DatasetManager",
    "ValidationIssue",
    "ValidationReport",
    "validate_features_dataset",
    "validate_outcomes_dataset",
    "validate_gmp_history_dataset",
    "validate_registry_dataset",
    "validate_feature_sources_dataset",
    "check_referential_integrity",
]
