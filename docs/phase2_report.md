# IPOVision — Phase 2: Dataset Construction & Validation Engine Report

**Document Status:** Complete & Verified  
**Date:** November 2026  
**Phase:** 2 of 10  
**Target Market:** Indian Mainboard IPOs Only  

---

## 1. Executive Summary

Phase 2 establishes the data architecture, schema specifications, canonical identifier conventions, deterministic validation rules, data cleaning routines, and automated storage operations for **IPOVision**.

In strict accordance with Phase 2 instructions:
- **Zero fabricated data** exists in `data/processed/`. All 5 canonical dataset files are clean schema templates (0 data rows).
- Real-world test records, edge cases, and invalidity triggers are strictly segregated inside `tests/fixtures/` and clearly labelled synthetic.
- All 38 automated tests across Phase 0, Phase 1, and Phase 2 pass with 100% success.

---

## 2. Directory Structure After Phase 2

```text
e:\ipo-analyzer1\
├── .env.example
├── .gitignore                          [Updated: whitelisted template CSVs]
├── README.md                           [Updated: Phase 0, 1, 2 marked COMPLETED]
├── requirements.txt
├── config/
│   ├── settings.example.yaml
│   └── settings.yaml
├── data/
│   ├── raw/                            [Raw scraped snapshots & diagnostics]
│   ├── interim/
│   └── processed/                      [Canonical empty CSV templates]
│       ├── .gitkeep
│       ├── ipo_features.csv            (39 columns, 0 rows)
│       ├── ipo_outcomes.csv            (7 columns, 0 rows)
│       ├── ipo_gmp_history.csv         (6 columns, 0 rows)
│       ├── ipo_feature_sources.csv     (12 columns, 0 rows)
│       └── ipo_registry.csv            (6 columns, 0 rows)
├── docs/
│   ├── data_dictionary.md              [Updated: 5 tables documented comprehensively]
│   ├── data_sources.md                 [New: verified endpoints & limitations]
│   ├── modelling_decisions.md
│   └── sources_and_limitations.md
├── notebooks/
│   └── 01_source_testing.ipynb
├── reports/
│   ├── data_quality/
│   │   └── data_quality_report.md      [New: automated dataset health audit]
│   ├── source_testing/
│   │   ├── source_test_results.csv     [New: 10 endpoint test records]
│   │   └── source_testing_summary.md   [New: executive findings]
│   ├── evaluation/
│   └── figures/
├── src/
│   ├── config.py
│   ├── collection/                     [Phase 1 scrapers & HTTP client]
│   │   ├── http_client.py
│   │   ├── investorgain_scraper.py
│   │   ├── chittorgarh_detail_scraper.py
│   │   ├── source_tester.py
│   │   └── deep_inspector.py
│   └── cleaning/                       [Phase 2 Core Modules]
│       ├── __init__.py                 [Public exports]
│       ├── ipo_id.py                   [Canonical ID generator & registry manager]
│       ├── cleaner.py                  [IPOCleaner: dates, numbers, subscriptions]
│       ├── validators.py               [ValidationReport, leak audits, integrity]
│       └── dataset_manager.py          [DatasetManager: atomic I/O & health reports]
└── tests/
    ├── test_environment.py             (7 tests, Phase 0)
    ├── test_phase1.py                  (8 tests, Phase 1)
    ├── test_phase2.py                  (23 tests, Phase 2)
    └── fixtures/                       [Strictly segregated synthetic test data]
        ├── synthetic_ipo_registry.csv
        ├── synthetic_ipo_features.csv
        ├── synthetic_ipo_outcomes.csv
        ├── synthetic_ipo_gmp_history.csv
        ├── synthetic_ipo_feature_sources.csv
        └── synthetic_invalid_cases.csv
```

---

## 3. Files Created or Modified in Phase 2

| File Path | Action | Description |
| :--- | :--- | :--- |
| [`src/cleaning/ipo_id.py`](file:///e:/ipo-analyzer1/src/cleaning/ipo_id.py) | Created | Canonical `INMAIN-YYYY-NNNN` generator, parsing, entity normalization, and atomic registry manager. |
| [`src/cleaning/cleaner.py`](file:///e:/ipo-analyzer1/src/cleaning/cleaner.py) | Created | `IPOCleaner`: numeric cleaning, subscription multiple parsing, multi-format date parsing, leakage neutralization. |
| [`src/cleaning/validators.py`](file:///e:/ipo-analyzer1/src/cleaning/validators.py) | Created | `ValidationReport`: leak detection, temporal cutoff checks, financial domain checks, mathematical outcome checks. |
| [`src/cleaning/dataset_manager.py`](file:///e:/ipo-analyzer1/src/cleaning/dataset_manager.py) | Created | `DatasetManager`: atomic I/O via temporary swap, duplicate checking, Markdown/JSON quality reporting. |
| [`src/cleaning/__init__.py`](file:///e:/ipo-analyzer1/src/cleaning/__init__.py) | Modified | Clean public API exports. |
| [`data/processed/*.csv`](file:///e:/ipo-analyzer1/data/processed) | Created | 5 empty schema templates with exact headers (0 data rows). |
| [`docs/data_dictionary.md`](file:///e:/ipo-analyzer1/docs/data_dictionary.md) | Modified | Exhaustive schema dictionary for all 5 datasets. |
| [`docs/data_sources.md`](file:///e:/ipo-analyzer1/docs/data_sources.md) | Created | Synthesis of empirical findings from Phase 1. |
| [`reports/data_quality/data_quality_report.md`](file:///e:/ipo-analyzer1/reports/data_quality/data_quality_report.md) | Created | Generated quality report across all 5 processed datasets. |
| [`reports/source_testing/*`](file:///e:/ipo-analyzer1/reports/source_testing) | Created | Summary report and structured CSV from Phase 1 diagnostic run. |
| [`tests/fixtures/*`](file:///e:/ipo-analyzer1/tests/fixtures) | Created | Synthetic test datasets and edge-case invalidity triggers. |
| [`tests/test_phase2.py`](file:///e:/ipo-analyzer1/tests/test_phase2.py) | Created | 23 unit tests covering IDs, cleaning, leakage, math, edge cases, atomic I/O. |
| [`README.md`](file:///e:/ipo-analyzer1/README.md) | Modified | Updated roadmap table: Phase 0, 1, 2 marked COMPLETED. |
| [`.gitignore`](file:///e:/ipo-analyzer1/.gitignore) | Modified | Whitelisted processed template CSVs. |

---

## 4. Detailed Dataset Architecture

### A. Primary Datasets

1. **`ipo_features.csv` (Primary Feature Store - 39 Columns)**
   - **Granularity:** One row per `(ipo_id, prediction_stage, data_cutoff)`.
   - **Stages:** `pre_close` (before subscription ends) and `post_close` (after subscription closes).
   - **Feature Categories:**
     - *Identification:* `ipo_id`, `company_name`, `symbol`, `exchange`.
     - *Issue Details:* `issue_open_date`, `issue_close_date`, `issue_price`, `price_band_low`, `price_band_high`, `issue_size_cr`, `fresh_issue_cr`, `ofs_cr`, `listing_date`.
     - *Fundamentals & Periods:* `revenue`, `revenue_period`, `profit_after_tax`, `pat_period`, `ebitda`, `ebitda_period`, `total_debt`, `net_worth`, `cash_flow_from_operations`, `eps`, `nav`.
     - *Valuation Multiples:* `pe_ratio`, `pb_ratio`, `peer_pe_ratio`, `peer_pb_ratio`.
     - *Subscription (Post-Close Only):* `qib_subscription`, `nii_subscription`, `retail_subscription`, `overall_subscription`.
     - *Grey Market Sentiment:* `gmp`, `gmp_change`, `gmp_source`, `gmp_recorded_at`, `gmp_missing`.
     - *Metadata & Guardrails:* `prediction_stage`, `data_cutoff`.

2. **`ipo_outcomes.csv` (Ground Truth Listing Outcomes - 7 Columns)**
   - **Granularity:** One row per `ipo_id` (Primary Key).
   - **Columns:** `ipo_id`, `listing_date`, `issue_price`, `listing_open_price`, `listing_close_price`, `listing_gain_pct`, `listing_positive`.
   - **Primary Target Definition:** Listing-day opening trade price.
     $$\text{listing\_gain\_pct} = \frac{\text{listing\_open\_price} - \text{issue\_price}}{\text{issue\_price}} \times 100$$
     $$\text{listing\_positive} = \begin{cases} 1 & \text{if } \text{listing\_gain\_pct} > 0.0 \\ 0 & \text{if } \text{listing\_gain\_pct} \le 0.0 \end{cases}$$

3. **`ipo_gmp_history.csv` (GMP Time Series - 6 Columns)**
   - **Granularity:** Multiple timestamped observations per `ipo_id`.
   - **Columns:** `ipo_id`, `recorded_at`, `gmp`, `source`, `source_url`, `notes`.
   - **Sentiment Preservation:** Retains the trajectory of grey market sentiment across the IPO lifecycle.

### B. Supporting Datasets

4. **`ipo_feature_sources.csv` (Data Provenance & RAG Audit - 12 Columns)**
   - **Purpose:** Full provenance tracking for every critical fundamental metric.
   - **Columns:** `ipo_id`, `prediction_stage`, `data_cutoff`, `feature_name`, `feature_value`, `source_name`, `source_url`, `document_name`, `document_page`, `retrieved_at`, `verification_status`, `notes`.
   - **Future RAG Compatibility:** Allows LLM extractions from RHP PDFs (Phase 5) to cite document names and page numbers with explicit verification status (`unverified`, `llm_extracted`, `verified`).

5. **`ipo_registry.csv` (Master IPO Directory - 6 Columns)**
   - **Purpose:** Authoritative directory establishing unique, permanent identifiers.
   - **Columns:** `ipo_id`, `company_name`, `symbol`, `issue_open_date`, `issue_close_date`, `listing_date`.

---

## 5. Canonical IPO ID System

- **Format:** `INMAIN-YYYY-NNNN` (e.g. `INMAIN-2024-0001`, `INMAIN-2024-0002`).
  - `INMAIN`: Restricts scope to Indian Mainboard IPOs (excludes SME segments).
  - `YYYY`: 4-digit calendar year of issue.
  - `NNNN`: 4-digit zero-padded sequential number assigned chronologically.
- **Entity Normalization:** `normalize_company_name()` strips corporate structure suffixes (`LIMITED`, `PVT LTD`, `INDIA`, `LLP`, `CORP`) so that queries like `"Swiggy Limited"` and `"Swiggy Ltd"` map idempotently to the same identifier.
- **Registry Guarantees:** Sequence assignment is atomic, year-resetting, and managed via `IPORegistryManager`. Row numbers are never used as identifiers.

---

## 6. Validation Rules Implemented

The validation engine in [`src/cleaning/validators.py`](file:///e:/ipo-analyzer1/src/cleaning/validators.py) enforces:

1. **Strict Look-Ahead Leakage Barrier:**
   In any record where `prediction_stage == "pre_close"`, subscription columns (`qib_subscription`, `nii_subscription`, `retail_subscription`, `overall_subscription`) **MUST BE NaN / None**. Any numeric value triggers a fatal `LOOK-AHEAD LEAKAGE` error.
2. **Target Leakage Prohibition:**
   Outcome columns (`listing_open_price`, `listing_gain_pct`, `listing_positive`) are strictly forbidden inside `ipo_features.csv`.
3. **Temporal Cutoff Alignment:**
   All feature observation timestamps (e.g., `gmp_recorded_at`) must satisfy:
   $$\text{timestamp} \le \text{data\_cutoff}$$
4. **Temporal Date Precedence:**
   $$\text{issue\_open\_date} \le \text{issue\_close\_date} \le \text{listing\_date}$$
5. **Pricing & Sizing Sanity:**
   $\text{issue\_price} > 0$, $\text{issue\_size\_cr} > 0$, $\text{price\_band\_low} \le \text{price\_band\_high}$.
6. **Financial Loss Permissibility:**
   Total debt must be $\ge 0$. Legitimate corporate losses (negative PAT, negative EBITDA, negative operating cash flows) are fully supported and not rejected.
7. **Unofficial Data Policy:**
   Missing GMP is **never converted to 0.0**. The `gmp_missing` flag is synchronized ($1$ if GMP is NaN, $0$ if present).
8. **Mathematical Target Integrity:**
   Listing gain percentage and binary classification targets are verified against issue and open prices. At-par listings ($\text{gain} = 0.0\%$) are strictly classified as $\text{listing\_positive} = 0$.
9. **Referential Integrity:**
   Foreign keys in `ipo_outcomes.csv` and `ipo_gmp_history.csv` must resolve to registered IPO IDs.

---

## 7. Automated Test Suite Results

All tests run via `pytest` and Python `unittest`.

### Summary:
- **Phase 0 Tests (`tests/test_environment.py`):** 7 / 7 PASSED
- **Phase 1 Tests (`tests/test_phase1.py`):** 8 / 8 PASSED
- **Phase 2 Tests (`tests/test_phase2.py`):** 23 / 23 PASSED
- **Total Suite:** **38 / 38 PASSED (100% success in 2.48s)**

```text
tests/test_environment.py::TestEnvironmentSetup::test_config_example_file PASSED
tests/test_environment.py::TestEnvironmentSetup::test_data_dictionary_exists_and_contains_schemas PASSED
tests/test_environment.py::TestEnvironmentSetup::test_env_example_exists PASSED
tests/test_environment.py::TestEnvironmentSetup::test_gitignore_security_rules PASSED
tests/test_environment.py::TestEnvironmentSetup::test_package_init_files_exist PASSED
tests/test_environment.py::TestEnvironmentSetup::test_project_directory_structure PASSED
tests/test_environment.py::TestEnvironmentSetup::test_python_version PASSED
tests/test_phase1.py::TestPhase1Collection::test_chittorgarh_number_cleaning PASSED
tests/test_phase1.py::TestPhase1Collection::test_http_client_get_structure PASSED
tests/test_phase1.py::TestPhase1Collection::test_http_client_initialization PASSED
tests/test_phase1.py::TestPhase1Collection::test_investorgain_name_cleaning PASSED
tests/test_phase1.py::TestPhase1Collection::test_investorgain_number_cleaning PASSED
tests/test_phase1.py::TestPhase1Collection::test_investorgain_subscription_parsing PASSED
tests/test_phase1.py::TestPhase1Collection::test_notebook_exists PASSED
tests/test_phase1.py::TestPhase1Collection::test_source_test_report_exists PASSED
tests/test_phase2.py::TestIPOIdSystem::test_id_format_regex PASSED
tests/test_phase2.py::TestIPOIdSystem::test_normalize_company_name PASSED
tests/test_phase2.py::TestIPOIdSystem::test_parse_and_format_ipo_id PASSED
tests/test_phase2.py::TestIPOIdSystem::test_registry_registration_and_idempotence PASSED
tests/test_phase2.py::TestIPOCleaner::test_clean_date PASSED
tests/test_phase2.py::TestIPOCleaner::test_clean_number PASSED
tests/test_phase2.py::TestIPOCleaner::test_gmp_missing_synchronization PASSED
tests/test_phase2.py::TestIPOCleaner::test_leakage_neutralization_in_pre_close PASSED
tests/test_phase2.py::TestIPOCleaner::test_parse_subscription_multiple PASSED
tests/test_phase2.py::TestValidators::test_detect_negative_debt_error PASSED
tests/test_phase2.py::TestValidators::test_detect_pre_close_subscription_leakage PASSED
tests/test_phase2.py::TestValidators::test_detect_target_leakage_in_features PASSED
tests/test_phase2.py::TestValidators::test_detect_temporal_cutoff_violation PASSED
tests/test_phase2.py::TestValidators::test_outcomes_mathematical_consistency PASSED
tests/test_phase2.py::TestValidators::test_referential_integrity PASSED
tests/test_phase2.py::TestValidators::test_synthetic_valid_fixtures PASSED
tests/test_edge_case_missing_gmp_never_zero PASSED
tests/test_edge_case_negative_pat_is_valid PASSED
tests/test_edge_case_par_listing_zero_gain PASSED
tests/test_dataset_manager_atomic_save_and_load PASSED
tests/test_dataset_manager_data_quality_report_generation PASSED
tests/test_dataset_manager_duplicate_detection PASSED
tests/test_all_five_templates_exist_and_empty PASSED

============================= 38 passed in 2.48s ==============================
```

---

## 8. Verification & PowerShell Execution Commands

To replicate all checks on Windows PowerShell:

```powershell
# Navigate and activate virtual environment
cd e:\ipo-analyzer1
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1

# Run full test suite with pytest
python -m pytest tests/ -v

# Or run individual test modules
python tests/test_environment.py
python tests/test_phase1.py
python tests/test_phase2.py

# Generate/refresh the data quality report
python -c "from src.cleaning.dataset_manager import DatasetManager; DatasetManager().generate_data_quality_report()"
```

---

## 9. Phase 2 Completion Checklist

- [x] Dataset architecture implemented (3 primary + 2 supporting datasets).
- [x] Canonical IPO ID convention (`INMAIN-YYYY-NNNN`) implemented.
- [x] Master IPO registry manager implemented with idempotent lookup.
- [x] Five clean CSV templates created in `data/processed/` (0 data rows).
- [x] Feature provenance schema created for future RHP/DRHP RAG audit.
- [x] Data dictionary updated with full definitions, types, units, periods, and rules.
- [x] Reusable validation engine implemented with structured `ValidationReport`.
- [x] Non-destructive cleaning engine implemented with leakage neutralization.
- [x] Dataset manager implemented with atomic write swaps and duplicate detection.
- [x] Automated data quality report generated in `reports/data_quality/`.
- [x] Synthetic test fixtures and edge cases strictly isolated under `tests/fixtures/`.
- [x] Automated tests written and 100% passing (38/38 tests).
- [x] Project `README.md` and `.gitignore` updated.

---

## 10. Stop Condition

Phase 2 is **fully complete and verified**.

**Execution is halted here.** In accordance with the instructions, Phase 3 (Historical IPO Data Collection) will not begin until you have reviewed and approved this dataset architecture.
