# IPOVision — Data Quality & Integrity Report

**Generated:** 2026-11-15 21:53:38  
**Scope:** All Processed Datasets (`data/processed/`)  

---

## 1. Dataset Overview & Dimensions

| Dataset | Filename | Row Count | Column Count | Unique IPO IDs | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `ipo_features` | `ipo_features.csv` | 556 | 39 | 556 | Valid |
| `ipo_outcomes` | `ipo_outcomes.csv` | 556 | 7 | 556 | Valid |
| `ipo_gmp_history` | `ipo_gmp_history.csv` | 0 | 0 | 0 | Template (0 rows) |
| `ipo_feature_sources` | `ipo_feature_sources.csv` | 3401 | 12 | 556 | Valid |
| `ipo_registry` | `ipo_registry.csv` | 556 | 6 | 556 | Valid |

---

## 2. Detailed Dataset Health

### Dataset: `ipo_features`
- **Data Rows:** 556
- **Duplicate Count:** 0
- **Validation Errors:** 0
- **Validation Warnings:** 0

| Column Name | Non-Null Count | Missing Count | Completeness % | Inferred Type |
| :--- | :---: | :---: | :---: | :--- |
| `ipo_id` | 556 | 0 | 100.0% | `object` |
| `company_name` | 556 | 0 | 100.0% | `object` |
| `symbol` | 459 | 97 | 82.6% | `object` |
| `exchange` | 0 | 556 | 0.0% | `float64` |
| `issue_open_date` | 0 | 556 | 0.0% | `float64` |
| `issue_close_date` | 0 | 556 | 0.0% | `float64` |
| `issue_price` | 556 | 0 | 100.0% | `float64` |
| `price_band_low` | 0 | 556 | 0.0% | `float64` |
| `price_band_high` | 0 | 556 | 0.0% | `float64` |
| `issue_size_cr` | 556 | 0 | 100.0% | `float64` |
| `fresh_issue_cr` | 0 | 556 | 0.0% | `float64` |
| `ofs_cr` | 0 | 556 | 0.0% | `float64` |
| `listing_date` | 556 | 0 | 100.0% | `object` |
| `revenue` | 0 | 556 | 0.0% | `float64` |
| `revenue_period` | 0 | 556 | 0.0% | `float64` |
| `profit_after_tax` | 0 | 556 | 0.0% | `float64` |
| `pat_period` | 0 | 556 | 0.0% | `float64` |
| `ebitda` | 0 | 556 | 0.0% | `float64` |
| `ebitda_period` | 0 | 556 | 0.0% | `float64` |
| `total_debt` | 0 | 556 | 0.0% | `float64` |
| `net_worth` | 0 | 556 | 0.0% | `float64` |
| `cash_flow_from_operations` | 0 | 556 | 0.0% | `float64` |
| `eps` | 0 | 556 | 0.0% | `float64` |
| `nav` | 0 | 556 | 0.0% | `float64` |
| `pe_ratio` | 0 | 556 | 0.0% | `float64` |
| `pb_ratio` | 0 | 556 | 0.0% | `float64` |
| `peer_pe_ratio` | 0 | 556 | 0.0% | `float64` |
| `peer_pb_ratio` | 0 | 556 | 0.0% | `float64` |
| `qib_subscription` | 427 | 129 | 76.8% | `float64` |
| `nii_subscription` | 427 | 129 | 76.8% | `float64` |
| `retail_subscription` | 427 | 129 | 76.8% | `float64` |
| `overall_subscription` | 556 | 0 | 100.0% | `float64` |
| `gmp` | 452 | 104 | 81.3% | `float64` |
| `gmp_change` | 0 | 556 | 0.0% | `float64` |
| `gmp_source` | 452 | 104 | 81.3% | `object` |
| `gmp_recorded_at` | 0 | 556 | 0.0% | `float64` |
| `gmp_missing` | 556 | 0 | 100.0% | `int64` |
| `prediction_stage` | 556 | 0 | 100.0% | `object` |
| `data_cutoff` | 556 | 0 | 100.0% | `object` |

### Dataset: `ipo_outcomes`
- **Data Rows:** 556
- **Duplicate Count:** 0
- **Validation Errors:** 0
- **Validation Warnings:** 0

| Column Name | Non-Null Count | Missing Count | Completeness % | Inferred Type |
| :--- | :---: | :---: | :---: | :--- |
| `ipo_id` | 556 | 0 | 100.0% | `object` |
| `listing_date` | 556 | 0 | 100.0% | `object` |
| `issue_price` | 556 | 0 | 100.0% | `float64` |
| `listing_open_price` | 556 | 0 | 100.0% | `float64` |
| `listing_close_price` | 0 | 556 | 0.0% | `float64` |
| `listing_gain_pct` | 556 | 0 | 100.0% | `float64` |
| `listing_positive` | 556 | 0 | 100.0% | `int64` |

### Dataset: `ipo_gmp_history`
- **Status:** Verified empty template with schema headers.
- **Data Rows:** 0
- **Duplicate Count:** 0
- **Missing Value Profile:** N/A (template ready for ingestion)

### Dataset: `ipo_feature_sources`
- **Data Rows:** 3401
- **Duplicate Count:** 0
- **Validation Errors:** 0
- **Validation Warnings:** 0

| Column Name | Non-Null Count | Missing Count | Completeness % | Inferred Type |
| :--- | :---: | :---: | :---: | :--- |
| `ipo_id` | 3401 | 0 | 100.0% | `object` |
| `prediction_stage` | 3401 | 0 | 100.0% | `object` |
| `data_cutoff` | 3401 | 0 | 100.0% | `object` |
| `feature_name` | 3401 | 0 | 100.0% | `object` |
| `feature_value` | 3401 | 0 | 100.0% | `float64` |
| `source_name` | 3401 | 0 | 100.0% | `object` |
| `source_url` | 787 | 2614 | 23.1% | `object` |
| `document_name` | 0 | 3401 | 0.0% | `float64` |
| `document_page` | 0 | 3401 | 0.0% | `float64` |
| `retrieved_at` | 3401 | 0 | 100.0% | `object` |
| `verification_status` | 3401 | 0 | 100.0% | `object` |
| `notes` | 3401 | 0 | 100.0% | `object` |

### Dataset: `ipo_registry`
- **Data Rows:** 556
- **Duplicate Count:** 0
- **Validation Errors:** 0
- **Validation Warnings:** 0

| Column Name | Non-Null Count | Missing Count | Completeness % | Inferred Type |
| :--- | :---: | :---: | :---: | :--- |
| `ipo_id` | 556 | 0 | 100.0% | `object` |
| `company_name` | 556 | 0 | 100.0% | `object` |
| `symbol` | 459 | 97 | 82.6% | `object` |
| `issue_open_date` | 0 | 556 | 0.0% | `float64` |
| `issue_close_date` | 0 | 556 | 0.0% | `float64` |
| `listing_date` | 556 | 0 | 100.0% | `object` |

---

## 3. Data Integrity & Leakage Verification

- **Target Leakage:** Zero listing outcome columns found in feature store.
- **Look-Ahead Leakage:** Strict NaN enforcement verified on pre-close subscription metrics.
- **Unofficial Sentiment:** Missing GMP verified as preserved NaN (never coerced to 0.0).
- **Identifier Consistency:** All datasets mapped to canonical `INMAIN-YYYY-NNNN` schema.
