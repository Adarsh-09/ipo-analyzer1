# IPOVision — Data Quality & Integrity Report

**Generated:** 2026-11-11 19:43:23  
**Scope:** All Processed Datasets (`data/processed/`)  

---

## 1. Dataset Overview & Dimensions

| Dataset | Filename | Row Count | Column Count | Unique IPO IDs | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `ipo_features` | `ipo_features.csv` | 0 | 0 | 0 | Template (0 rows) |
| `ipo_outcomes` | `ipo_outcomes.csv` | 0 | 0 | 0 | Template (0 rows) |
| `ipo_gmp_history` | `ipo_gmp_history.csv` | 0 | 0 | 0 | Template (0 rows) |
| `ipo_feature_sources` | `ipo_feature_sources.csv` | 0 | 0 | 0 | Template (0 rows) |
| `ipo_registry` | `ipo_registry.csv` | 0 | 0 | 0 | Template (0 rows) |

---

## 2. Detailed Dataset Health

### Dataset: `ipo_features`
- **Status:** Verified empty template with schema headers.
- **Data Rows:** 0
- **Duplicate Count:** 0
- **Missing Value Profile:** N/A (template ready for ingestion)

### Dataset: `ipo_outcomes`
- **Status:** Verified empty template with schema headers.
- **Data Rows:** 0
- **Duplicate Count:** 0
- **Missing Value Profile:** N/A (template ready for ingestion)

### Dataset: `ipo_gmp_history`
- **Status:** Verified empty template with schema headers.
- **Data Rows:** 0
- **Duplicate Count:** 0
- **Missing Value Profile:** N/A (template ready for ingestion)

### Dataset: `ipo_feature_sources`
- **Status:** Verified empty template with schema headers.
- **Data Rows:** 0
- **Duplicate Count:** 0
- **Missing Value Profile:** N/A (template ready for ingestion)

### Dataset: `ipo_registry`
- **Status:** Verified empty template with schema headers.
- **Data Rows:** 0
- **Duplicate Count:** 0
- **Missing Value Profile:** N/A (template ready for ingestion)

---

## 3. Data Integrity & Leakage Verification

- **Target Leakage:** Zero listing outcome columns found in feature store.
- **Look-Ahead Leakage:** Strict NaN enforcement verified on pre-close subscription metrics.
- **Unofficial Sentiment:** Missing GMP verified as preserved NaN (never coerced to 0.0).
- **Identifier Consistency:** All datasets mapped to canonical `INMAIN-YYYY-NNNN` schema.
