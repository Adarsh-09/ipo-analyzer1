# IPOVision — Executive Summary & Progress Report

**Project Name:** IPOVision  
**Tagline:** Data-driven intelligence for Indian Mainboard IPO listing analysis  
**Repository:** `e:\ipo-analyzer1`  
**Target Market:** Indian Mainboard IPOs Only (BSE & NSE)  
**Execution Environment:** Python 3.12 (`.venv`), Windows PowerShell  
**Current Test Status:** 38 / 38 Passing Unit & Integration Tests  

---

## 1. Project Overview & Motivation

**IPOVision** is an end-to-end Machine Learning, Data Engineering, and Financial Document Intelligence platform built specifically for Indian Mainboard initial public offerings (IPOs). 

Unlike simple informational websites or naive ML prototypes, IPOVision models the real-world operational reality of an IPO through a **Two-Stage Prediction Lifecycle**:
1. **Pre-Close Prediction (Stage A):** Generated strictly *before* the public bidding window closes. Uses fundamentals (Revenue, PAT, EBITDA, Debt), issue structure (Price, Size, Fresh vs OFS), valuation multiples (P/E, P/B, Peer P/E), and point-in-time Grey Market Premium (GMP). Subscription metrics are strictly forbidden to eliminate look-ahead data leakage.
2. **Post-Close Prediction (Stage B):** Generated *after* subscription closes but *before* listing morning. Incorporates all pre-close features plus final subscription multiples (QIB, NII, Retail, and Total) to estimate final listing outcomes.

### Core Targets:
- **Classification:** Probability of an IPO listing at a premium (`listing_positive = 1`) versus a discount/par (`listing_positive = 0`).
- **Regression:** Expected percentage listing gain or loss on listing-day opening trade:
  $$\text{listing\_gain\_pct} = \frac{\text{listing\_open\_price} - \text{issue\_price}}{\text{issue\_price}} \times 100$$

---

## 2. Progress by Phase

```text
  Phase 0: Project Setup               [COMPLETED]  ██████████ 100%
  Phase 1: Data Source Testing         [COMPLETED]  ██████████ 100%
  Phase 2: Dataset Construction        [COMPLETED]  ██████████ 100%
  Phase 3: Historical Data Collection  [IN PROGRESS] ░░░░░░░░░░   0%
  Phase 4: Exploratory Data Analysis   [PENDING]    ░░░░░░░░░░   0%
  Phase 5: RHP/DRHP RAG Engine         [PENDING]    ░░░░░░░░░░   0%
  Phase 6: Fundamental Analysis        [PENDING]    ░░░░░░░░░░   0%
  Phase 7: Baseline ML Models          [PENDING]    ░░░░░░░░░░   0%
  Phase 8: Advanced ML & Validation    [PENDING]    ░░░░░░░░░░   0%
  Phase 9: Streamlit Dashboard         [PENDING]    ░░░░░░░░░░   0%
  Phase 10: Final Audit & Polish       [PENDING]    ░░░░░░░░░░   0%
```

### Detailed Breakdown:

| Phase | Name | Status | Key Deliverables & Achievements |
| :---: | :--- | :---: | :--- |
| **0** | **Project Setup & Environment** | ✅ **COMPLETED** | Complete modular project structure, `.venv` with Python 3.12, pinned dependencies in `requirements.txt`, central configuration system (`src/config.py`), `.gitignore` security rules, and initial specifications (`docs/modelling_decisions.md`, `docs/sources_and_limitations.md`). Test suite: 7/7 passing (`tests/test_environment.py`). |
| **1** | **Data Source Testing & Scrapers** | ✅ **COMPLETED** | Audited 10 public endpoints across InvestorGain, Chittorgarh, SEBI, NSE, and BSE. Built defensive `IPOHttpClient` with rate-limiting and exponential backoff, working InvestorGain scraper, Chittorgarh 14-table detail page parser, verified SEBI RHP PDF digital text extraction (528 words/page), and generated `notebooks/01_source_testing.ipynb`. Test suite: 8/8 passing (`tests/test_phase1.py`). |
| **2** | **Dataset Construction & Validators** | ✅ **COMPLETED** | Built canonical `INMAIN-YYYY-NNNN` identifier system and master registry (`src/cleaning/ipo_id.py`), five schema templates in `data/processed/`, reusable data cleaner (`src/cleaning/cleaner.py`), validation engine with automated look-ahead leakage audits (`src/cleaning/validators.py`), atomic dataset manager (`src/cleaning/dataset_manager.py`), data quality report generator, exhaustive data dictionary (`docs/data_dictionary.md`), and synthetic test fixtures (`tests/fixtures/`). Test suite: 23/23 passing (`tests/test_phase2.py`). |
| **3** | **Historical Mainboard Data Collection** | 🔄 **IN PROGRESS** | Historical archive extraction across 2021–2024 Indian Mainboard IPOs, cross-referencing InvestorGain subscription/outcomes with Chittorgarh fundamentals and SEBI prospectuses. |
| **4** | **Exploratory Data Analysis (EDA)** | 🔲 *Pending* | Statistical distributions, listing gain analysis, GMP correlation analysis, and publication-quality visual reports. |
| **5** | **RHP/DRHP RAG Intelligence Engine** | 🔲 *Pending* | Hybrid vector + keyword search over prospectus PDFs using PyMuPDF, ChromaDB, Sentence Transformers, and Google Gemini API. |
| **6** | **Fundamental Analysis Integration** | 🔲 *Pending* | Transparent rule-based financial health scoring, debt and cash flow risk flags, and peer valuation benchmarking. |
| **7** | **Baseline Machine Learning Models** | 🔲 *Pending* | Benchmark baselines: Majority Class Classifier, GMP-Implied Listing Gain, and Historical Median Gain Regressor evaluated via Chronological Walk-Forward CV. |
| **8** | **Advanced Machine Learning** | 🔲 *Pending* | Tuned Random Forest, Gradient Boosting, and XGBoost models for pre-close and post-close stages, SHAP explainability, and downside discount recall focus. |
| **9** | **Streamlit Multi-Page Dashboard** | 🔲 *Pending* | 7+ page interactive UI: IPO Overview, Financial Drill-downs, Live GMP Tracker, Prediction Engine, and Prospectus RAG Q&A. |
| **10** | **Testing, Documentation & Packaging** | 🔲 *Pending* | Comprehensive integration test audit, final documentation, and portfolio polish. |

---

## 3. Dataset Architecture & Storage Layout

IPOVision separates raw data from cleaned analytical stores. Inside `data/processed/`, five production schema templates are maintained:

```text
data/processed/
├── ipo_registry.csv          (Master directory assigning unique INMAIN-YYYY-NNNN IDs)
├── ipo_features.csv          (39 columns: issue parameters, financials, valuation, subscriptions, GMP)
├── ipo_outcomes.csv          (7 columns: actual listing date, open/close price, gain %, positive binary)
├── ipo_gmp_history.csv       (6 columns: timestamped grey market quotes over time)
└── ipo_feature_sources.csv   (12 columns: document name, page number, and verification status)
```

### Core Data Integrity Rules Enforced:
1. **Zero Look-Ahead Leakage:** In any record where `prediction_stage == "pre_close"`, subscription columns (`qib_subscription`, `nii_subscription`, `retail_subscription`, `overall_subscription`) **MUST BE `NaN`**. The validator flags any populated subscription in pre-close as a fatal error.
2. **Missing GMP Policy:** Unofficial grey market quotes that are missing are **never replaced with 0.0**. They are preserved as `NaN`, synchronized with `gmp_missing = 1`.
3. **Legitimate Startup Losses:** Negative Profit After Tax (PAT), negative EBITDA, or negative operating cash flows are accepted as valid business numbers and never rejected as invalid errors.
4. **Target Calculation Consistency:** `listing_positive` is strictly $1$ if `listing_gain_pct > 0.0` and $0$ if $\le 0.0$ (at-par listings derive $0$).
5. **Atomic Storage Protection:** Datasets are saved using atomic file rename swaps (`.tmp` $\to$ `.csv`) to eliminate corruption risks during process terminations, and `data/raw/` is permanently write-protected.

---

## 4. Automated Testing & Verification Status

IPOVision enforces rigorous test-driven validation. The full test suite passes with **100% success (38 / 38 tests)**:

```powershell
# Virtual environment activation and test execution
cd e:\ipo-analyzer1
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ -v
# Output: ============================= 38 passed in 4.87s ==============================
```

- **Phase 0 (`tests/test_environment.py` - 7 tests):** Directory structure, environment requirements, YAML parsing, and library imports.
- **Phase 1 (`tests/test_phase1.py` - 8 tests):** HTTP client sessions, rate limiting, numeric string cleaning, subscription multiple regex (`12.795th Nov` $\to$ `12.79`), and SME filtering.
- **Phase 2 (`tests/test_phase2.py` - 23 tests):** Canonical `INMAIN-YYYY-NNNN` ID schema, entity normalization, leakage neutralization in pre-close, temporal cutoff enforcement, mathematical target consistency, edge cases (losses, zero-gain listings, missing GMP), and atomic I/O.

---

## 5. Technology Stack Summary

| Layer | Tools & Libraries |
| :--- | :--- |
| **Programming Language** | Python 3.12 |
| **Data Collection** | `requests`, `BeautifulSoup4`, `lxml`, `urllib3` |
| **Data Engineering** | `pandas`, `numpy`, `Pydantic v2`, `PyYAML`, `python-dotenv` |
| **Machine Learning** | `scikit-learn`, `xgboost`, `shap`, `joblib` |
| **Document AI / RAG** | `PyMuPDF` (fitz), `pdfplumber`, `chromadb`, `sentence-transformers`, `google-generativeai` |
| **Visualization & App** | `matplotlib`, `seaborn`, `plotly`, `streamlit` |
| **Testing & Quality** | `pytest`, `pytest-cov`, `unittest` (standard library) |

---

## 6. Immediate Next Steps (Phase 3 Execution)

1. Run the historical collection pipeline to harvest 2021–2024 Indian Mainboard IPOs from verified public endpoints.
2. Cross-reference company financials (Chittorgarh) with subscription bidding breakdowns (InvestorGain) and official filings (SEBI/NSE).
3. Assign canonical `INMAIN-YYYY-NNNN` IDs via `IPORegistryManager` and populate the 5 processed datasets.
4. Execute `validators.py` and `dataset_manager.py` to produce the final Data Quality Audit Report before transitioning to Phase 4 (EDA).

