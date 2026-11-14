# IPOVision — Data Quality & Integrity Report

**Generated:** 2026-11-14 20:47:28  
**Scope:** All Processed Datasets (`data/processed/`)  

---

## 1. Dataset Overview & Dimensions

| Dataset | Filename | Row Count | Column Count | Unique IPO IDs | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `ipo_features` | `ipo_features.csv` | 557 | 39 | 557 | Valid |
| `ipo_outcomes` | `ipo_outcomes.csv` | 557 | 7 | 557 | Valid |
| `ipo_gmp_history` | `ipo_gmp_history.csv` | 0 | 0 | 0 | Template (0 rows) |
| `ipo_feature_sources` | `ipo_feature_sources.csv` | 3481 | 12 | 557 | Valid |
| `ipo_registry` | `ipo_registry.csv` | 557 | 6 | 557 | Valid |

---

## 2. Detailed Dataset Health

### Dataset: `ipo_features`
- **Data Rows:** 557
- **Duplicate Count:** 0
- **Validation Errors:** 0
- **Validation Warnings:** 0

| Column Name | Non-Null Count | Missing Count | Completeness % | Inferred Type |
| :--- | :---: | :---: | :---: | :--- |
| `ipo_id` | 557 | 0 | 100.0% | `object` |
| `company_name` | 557 | 0 | 100.0% | `object` |
| `symbol` | 460 | 97 | 82.6% | `object` |
| `exchange` | 0 | 557 | 0.0% | `float64` |
| `issue_open_date` | 0 | 557 | 0.0% | `float64` |
| `issue_close_date` | 0 | 557 | 0.0% | `float64` |
| `issue_price` | 557 | 0 | 100.0% | `float64` |
| `price_band_low` | 0 | 557 | 0.0% | `float64` |
| `price_band_high` | 0 | 557 | 0.0% | `float64` |
| `issue_size_cr` | 557 | 0 | 100.0% | `float64` |
| `fresh_issue_cr` | 0 | 557 | 0.0% | `float64` |
| `ofs_cr` | 0 | 557 | 0.0% | `float64` |
| `listing_date` | 557 | 0 | 100.0% | `object` |
| `revenue` | 0 | 557 | 0.0% | `float64` |
| `revenue_period` | 0 | 557 | 0.0% | `float64` |
| `profit_after_tax` | 0 | 557 | 0.0% | `float64` |
| `pat_period` | 0 | 557 | 0.0% | `float64` |
| `ebitda` | 0 | 557 | 0.0% | `float64` |
| `ebitda_period` | 0 | 557 | 0.0% | `float64` |
| `total_debt` | 0 | 557 | 0.0% | `float64` |
| `net_worth` | 0 | 557 | 0.0% | `float64` |
| `cash_flow_from_operations` | 0 | 557 | 0.0% | `float64` |
| `eps` | 0 | 557 | 0.0% | `float64` |
| `nav` | 0 | 557 | 0.0% | `float64` |
| `pe_ratio` | 0 | 557 | 0.0% | `float64` |
| `pb_ratio` | 0 | 557 | 0.0% | `float64` |
| `peer_pe_ratio` | 0 | 557 | 0.0% | `float64` |
| `peer_pb_ratio` | 0 | 557 | 0.0% | `float64` |
| `qib_subscription` | 453 | 104 | 81.3% | `float64` |
| `nii_subscription` | 453 | 104 | 81.3% | `float64` |
| `retail_subscription` | 453 | 104 | 81.3% | `float64` |
| `overall_subscription` | 557 | 0 | 100.0% | `float64` |
| `gmp` | 451 | 106 | 81.0% | `float64` |
| `gmp_change` | 0 | 557 | 0.0% | `float64` |
| `gmp_source` | 451 | 106 | 81.0% | `object` |
| `gmp_recorded_at` | 0 | 557 | 0.0% | `float64` |
| `gmp_missing` | 557 | 0 | 100.0% | `int64` |
| `prediction_stage` | 557 | 0 | 100.0% | `object` |
| `data_cutoff` | 557 | 0 | 100.0% | `object` |

### Dataset: `ipo_outcomes`
- **Data Rows:** 557
- **Duplicate Count:** 0
- **Validation Errors:** 0
- **Validation Warnings:** 0

| Column Name | Non-Null Count | Missing Count | Completeness % | Inferred Type |
| :--- | :---: | :---: | :---: | :--- |
| `ipo_id` | 557 | 0 | 100.0% | `object` |
| `listing_date` | 557 | 0 | 100.0% | `object` |
| `issue_price` | 557 | 0 | 100.0% | `float64` |
| `listing_open_price` | 557 | 0 | 100.0% | `float64` |
| `listing_close_price` | 0 | 557 | 0.0% | `float64` |
| `listing_gain_pct` | 557 | 0 | 100.0% | `float64` |
| `listing_positive` | 557 | 0 | 100.0% | `int64` |

### Dataset: `ipo_gmp_history`
- **Status:** Verified empty template with schema headers.
- **Data Rows:** 0
- **Duplicate Count:** 0
- **Missing Value Profile:** N/A (template ready for ingestion)

### Dataset: `ipo_feature_sources`
- **Data Rows:** 3481
- **Duplicate Count:** 0
- **Validation Errors:** 0
- **Validation Warnings:** 0

| Column Name | Non-Null Count | Missing Count | Completeness % | Inferred Type |
| :--- | :---: | :---: | :---: | :--- |
| `ipo_id` | 3481 | 0 | 100.0% | `object` |
| `prediction_stage` | 3481 | 0 | 100.0% | `object` |
| `data_cutoff` | 3481 | 0 | 100.0% | `object` |
| `feature_name` | 3481 | 0 | 100.0% | `object` |
| `feature_value` | 3481 | 0 | 100.0% | `float64` |
| `source_name` | 3481 | 0 | 100.0% | `object` |
| `source_url` | 763 | 2718 | 21.9% | `object` |
| `document_name` | 0 | 3481 | 0.0% | `float64` |
| `document_page` | 0 | 3481 | 0.0% | `float64` |
| `retrieved_at` | 3481 | 0 | 100.0% | `object` |
| `verification_status` | 3481 | 0 | 100.0% | `object` |
| `notes` | 3481 | 0 | 100.0% | `object` |

### Dataset: `ipo_registry`
- **Data Rows:** 557
- **Duplicate Count:** 0
- **Validation Errors:** 0
- **Validation Warnings:** 0

| Column Name | Non-Null Count | Missing Count | Completeness % | Inferred Type |
| :--- | :---: | :---: | :---: | :--- |
| `ipo_id` | 557 | 0 | 100.0% | `object` |
| `company_name` | 557 | 0 | 100.0% | `object` |
| `symbol` | 460 | 97 | 82.6% | `object` |
| `issue_open_date` | 0 | 557 | 0.0% | `float64` |
| `issue_close_date` | 0 | 557 | 0.0% | `float64` |
| `listing_date` | 557 | 0 | 100.0% | `object` |

---

## 3. Data Integrity & Leakage Verification

- **Target Leakage:** Zero listing outcome columns found in feature store.
- **Look-Ahead Leakage:** Strict NaN enforcement verified on pre-close subscription metrics.
- **Unofficial Sentiment:** Missing GMP verified as preserved NaN (never coerced to 0.0).
- **Identifier Consistency:** All datasets mapped to canonical `INMAIN-YYYY-NNNN` schema.
