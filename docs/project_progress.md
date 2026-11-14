# IPOVision — Current Project Progress & Phase Roadmap

**Project Name:** IPOVision  
**Tagline:** Data-driven intelligence for Indian Mainboard IPO listing analysis  
**Last Updated:** Phase 2 Completion / Phase 3 Initiation  
**Environment:** Python 3.12 (Virtual Environment: `.venv`), Windows PowerShell  
**Current Test Status:** 38 / 38 Tests Passing (`pytest`)  

---

## 1. Executive Status Across All Phases

| Phase | Phase Name | Status | Key Deliverables & Outcomes |
| :---: | :--- | :---: | :--- |
| **Phase 0** | **Project Setup & Environment** | ✅ **COMPLETED** | Complete modular directory layout, pinned `requirements.txt`, central configuration engine (`src/config.py`), `.gitignore` security rules, architecture & modelling specifications (`docs/modelling_decisions.md`, `docs/sources_and_limitations.md`), and environment verification tests (`tests/test_environment.py`). |
| **Phase 1** | **Data Source Testing & Scraper Prototyping** | ✅ **COMPLETED** | Tested 10 public endpoints across 5 categories. Built resilient `IPOHttpClient` (rate-limiting, exponential backoff), InvestorGain listing performance scraper, Chittorgarh 14-table detail page parser, verified 100% digital selectable text in SEBI RHP PDFs, created Jupyter notebook (`notebooks/01_source_testing.ipynb`), and Phase 1 test suite (`tests/test_phase1.py`). |
| **Phase 2** | **Dataset Construction & Validation Engine** | ✅ **COMPLETED** | Defined 5 dataset schemas in `data/processed/`, implemented canonical `INMAIN-YYYY-NNNN` identifier system and master registry (`src/cleaning/ipo_id.py`), data cleaner (`src/cleaning/cleaner.py`), validation engine with look-ahead leakage audits (`src/cleaning/validators.py`), atomic dataset manager (`src/cleaning/dataset_manager.py`), data quality reporting (`reports/data_quality/data_quality_report.md`), exhaustive data dictionary (`docs/data_dictionary.md`), isolated synthetic test fixtures (`tests/fixtures/`), and Phase 2 test suite (`tests/test_phase2.py`). |
| **Phase 3** | **Historical Mainboard IPO Data Collection** | 🔄 **IN PROGRESS** | Scraping historical Indian Mainboard IPOs (2021–2024), populating master registry, features (`pre_close` and `post_close`), outcomes, GMP history, and provenance datasets. |
| **Phase 4** | **Exploratory Data Analysis (EDA)** | 🔲 *Pending* | Statistical distributions, listing gain analysis, GMP correlation studies, feature correlation heatmaps, and publication-ready visual figures. |
| **Phase 5** | **RHP/DRHP RAG Intelligence Engine** | 🔲 *Pending* | PDF text extraction (PyMuPDF), hybrid retrieval (Sentence Transformers + BM25), vector indexing (ChromaDB), and Gemini-powered prospectus question-answering. |
| **Phase 6** | **Fundamental Analysis Integration** | 🔲 *Pending* | Algorithmic scoring of financial strength, balance sheet risk indicators, valuation benchmarking, and rule-based red flags. |
| **Phase 7** | **Baseline ML Models** | 🔲 *Pending* | Majority class classifier, GMP-implied baseline, median gain regressor, standard linear/logistic models with strict chronological walk-forward validation. |
| **Phase 8** | **Advanced ML & Chronological Validation** | 🔲 *Pending* | Tuned Random Forest and XGBoost models for pre-close and post-close stages, SHAP feature importances, and downside recall optimization. |
| **Phase 9** | **Interactive Streamlit Dashboard** | 🔲 *Pending* | Multi-page dashboard with IPO overview, fundamental drill-downs, live GMP tracker, two-stage predictions, and interactive RAG chat. |
| **Phase 10** | **Testing, Audit & Final Polish** | 🔲 *Pending* | End-to-end integration testing, full documentation review, and portfolio finalization. |

---

## 2. Dataset Architecture & Current Schemas

IPOVision maintains five distinct datasets in `data/processed/` that follow strict data integrity and leakage-prevention guardrails:

```text
data/processed/
├── ipo_registry.csv          (Master directory; assigns unique INMAIN-YYYY-NNNN IDs)
├── ipo_features.csv          (39 columns; pre_close and post_close feature snapshots)
├── ipo_outcomes.csv          (7 columns; ground-truth listing gain % and positive target)
├── ipo_gmp_history.csv       (6 columns; granular time-series grey market quotes)
└── ipo_feature_sources.csv   (12 columns; provenance tracking for future RAG engine)
```

### Critical Data Handling Guardrails:
1. **Pre-Close / Post-Close Separation:**
   - In `pre_close` rows, subscription fields (`qib_subscription`, `nii_subscription`, `retail_subscription`, `overall_subscription`) **MUST BE NaN / None**.
   - If any subscription value is present in `pre_close`, the automated validation engine raises a fatal `LOOK-AHEAD LEAKAGE` error.
2. **Deterministic Target Math:**
   $$\text{listing\_gain\_pct} = \frac{\text{listing\_open\_price} - \text{issue\_price}}{\text{issue\_price}} \times 100$$
   $$\text{listing\_positive} = \begin{cases} 1 & \text{if } \text{listing\_gain\_pct} > 0.0 \\ 0 & \text{if } \text{listing\_gain\_pct} \le 0.0 \end{cases}$$
3. **Unofficial Sentiment Policy:**
   - Missing Grey Market Premium (GMP) is **never replaced with zero (`0.0`)**.
   - It is stored explicitly as `NaN`, synchronized with `gmp_missing = 1`.
4. **Legitimate Financial Losses:**
   - Negative Profit After Tax (PAT), negative EBITDA, or negative operating cash flow are valid startup realities and are never dropped as invalid errors.
5. **Zero Synthetic Pollution:**
   - Processed production files in `data/processed/` are clean schema templates.
   - All synthetic mock records and edge-case invalidity tests are strictly quarantined under `tests/fixtures/`.

---

## 3. Implemented Modules & Directory Map

```text
e:\ipo-analyzer1\
├── config/
│   ├── settings.example.yaml
│   └── settings.yaml
├── data/
│   ├── raw/                            [Raw scraped snapshots & diagnostics]
│   ├── interim/
│   └── processed/                      [Canonical dataset files & templates]
│       ├── ipo_features.csv
│       ├── ipo_outcomes.csv
│       ├── ipo_gmp_history.csv
│       ├── ipo_feature_sources.csv
│       └── ipo_registry.csv
├── docs/
│   ├── data_dictionary.md              [Complete 5-table schema specifications]
│   ├── data_sources.md                 [Empirical findings from 10 public sources]
│   ├── modelling_decisions.md          [ML problem framing & walk-forward CV strategy]
│   └── sources_and_limitations.md      [Provenance & market risk disclaimers]
├── notebooks/
│   └── 01_source_testing.ipynb         [Phase 1 interactive documentation]
├── reports/
│   ├── data_quality/
│   │   └── data_quality_report.md      [Dataset completeness and integrity audit]
│   └── source_testing/
│       ├── source_test_results.csv     [HTTP diagnostic results for 10 endpoints]
│       └── source_testing_summary.md   [Phase 1 findings summary]
├── src/
│   ├── config.py                       [Settings loader & path resolution]
│   ├── collection/
│   │   ├── http_client.py              [IPOHttpClient: rate limiter, retry adapter]
│   │   ├── investorgain_scraper.py     [Subscription & listing performance scraper]
│   │   ├── chittorgarh_detail_scraper.py [14-table financial & valuation parser]
│   │   ├── source_tester.py            [Endpoint diagnostic runner]
│   │   └── deep_inspector.py           [DOM inspection & React detection]
│   └── cleaning/
│       ├── __init__.py                 [Clean package exports]
│       ├── ipo_id.py                   [INMAIN-YYYY-NNNN generator & registry manager]
│       ├── cleaner.py                  [IPOCleaner: date, numeric, and subscription cleaning]
│       ├── validators.py               [ValidationReport, leakage & sanity audits]
│       └── dataset_manager.py          [DatasetManager: atomic I/O & quality reports]
└── tests/
    ├── test_environment.py             [Phase 0: 7 tests passing]
    ├── test_phase1.py                  [Phase 1: 8 tests passing]
    ├── test_phase2.py                  [Phase 2: 23 tests passing]
    └── fixtures/                       [Strictly segregated synthetic test data]
        ├── synthetic_ipo_registry.csv
        ├── synthetic_ipo_features.csv
        ├── synthetic_ipo_outcomes.csv
        ├── synthetic_ipo_gmp_history.csv
        ├── synthetic_ipo_feature_sources.csv
        └── synthetic_invalid_cases.csv
```

---

## 4. Test Verification Status

All 38 automated tests pass with 100% success:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ -v
# Output: ============================= 38 passed in 2.48s ==============================
```

- **Phase 0 (`test_environment.py`):** 7 tests validating directory structure, configuration keys, YAML parsing, and dependency imports.
- **Phase 1 (`test_phase1.py`):** 8 tests validating HTTP client sessions, numeric parsing (`₹22.98 Cr` $\to$ `22.98`), subscription string extraction (`12.795th Nov` $\to$ `12.79`), and SME tag filtering.
- **Phase 2 (`test_phase2.py`):** 23 tests validating canonical ID regex, entity normalization, leakage neutralization in pre-close, temporal cutoff checking, mathematical target consistency, edge cases (losses, zero gain, missing GMP), and atomic I/O.

---

## 5. Next Steps for Phase 3 Execution

1. Ingest historical Indian Mainboard IPOs (2021–2024) across verified public endpoints.
2. Cross-reference company fundamentals (Chittorgarh) with subscription multiples and listing performance (InvestorGain).
3. Assign canonical `INMAIN-YYYY-NNNN` identifiers in `ipo_registry.csv`.
4. Generate paired `pre_close` and `post_close` snapshots in `ipo_features.csv`, actual listing results in `ipo_outcomes.csv`, and chronological quotes in `ipo_gmp_history.csv`.
5. Run the Phase 2 validation engine on the completed dataset to ensure 100% compliance before proceeding to Phase 4 (EDA).

