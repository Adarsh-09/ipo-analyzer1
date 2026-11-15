# IPOVision — Overall Progress Report & Development Roadmap

**Report date:** 12 November 2026  
**Project:** IPOVision  
**Market scope:** Indian Mainboard IPOs (NSE/BSE)  
**Historical dataset target:** 2020–2026 (2026 collection cut-off: 11 November 2026)  
**Current phase:** Phase 3 — Historical IPO Data Collection  
**Current sub-phase:** P3.1 — Build and verify the IPO master list  

---

## 1. Executive summary

IPOVision is being developed as an Indian mainboard IPO research and listing-performance prediction platform. Its intended workflow is to collect historical IPO information, preserve source evidence, analyse company fundamentals and market sentiment, read RHP/DRHP documents with a retrieval-augmented generation (RAG) system, and train models to estimate listing-day performance.

The project has completed **Phase 0 (Project Setup), Phase 1 (Data Source Testing), and Phase 2 (Dataset Construction & Validation Engine)** according to the progress reports shared so far. Phase 2 reports 38 passing automated tests across Phases 0–2.

The project is currently in **Phase 3: Historical IPO Data Collection**. Work has focused on the 2020 IPO master list as the pilot year. A historical InvestorGain report returned 16 candidate instruments. Two were identified for exclusion from the ordinary company-IPO dataset (Yes Bank FPO and Mindspace REIT), leaving 14 IPO candidates. Individual detail-page URLs were extracted for all 16 original records, and opening, closing, and listing dates were successfully extracted for all 14 remaining candidates.

**Important status distinction:** successful extraction and matching between InvestorGain pages do not, by themselves, constitute independent official verification. The last confirmed verification-ledger output showed **1 verified record (Rossari Biotech) and 13 pending records**. A batch-verification approach was subsequently requested, but no completed batch run or updated ledger output has been shared in the project progress recorded here. Therefore, do not report all 14 records as officially verified yet.

---

## 2. Overall phase status

| Phase | Name | Current status | Notes |
|---|---|---|---|
| 0 | Project Setup | **Completed** | Project structure, environment, configuration, documentation and baseline tests established. |
| 1 | Data Source Testing | **Completed** | Candidate sources tested; source findings documented. |
| 2 | Dataset Construction & Validation Engine | **Completed** | Five canonical CSV templates, data dictionary, ID system, cleaning/validation modules and dataset manager created. Reported test result: 38/38 passed. |
| 3 | Historical IPO Data Collection | **In progress** | 2020 master-list pilot and date extraction underway; official verification and registry population remain pending. |
| 4 | Data Cleaning & Preprocessing | **Pending** | Apply cleaning and quality controls to collected historical data; do not confuse this with Phase 2's reusable cleaning-engine implementation. |
| 5 | Exploratory Data Analysis (EDA) | **Pending** | Understand distributions, relationships, outliers, missingness and possible leakage. |
| 6 | RHP/DRHP Intelligence Engine (RAG) | **Pending** | PDF ingestion, extraction, retrieval, document-grounded Q&A and structured prospectus analysis. |
| 7 | Fundamental Analysis Engine | **Pending** | Financial ratios, valuation comparisons, risk analysis and transparent fundamental scoring. |
| 8 | Machine Learning Engine | **Pending** | Pre-close/post-close classification and regression models, chronological evaluation and model selection. |
| 9 | Dashboard & Application Integration | **Pending** | Streamlit application connecting the data, RAG, fundamental and ML engines. |
| 10 | Testing, Backtesting, Deployment & Documentation | **Pending** | End-to-end validation, historical backtesting, deployment and final project documentation. |

---

# 3. Completed phases — detail

## Phase 0 — Project Setup

**Status: Completed (according to the project report).**

### Scope and deliverables
- Created the IPOVision project workspace and initial directory structure.
- Set up the Python environment and dependency-management files.
- Added `README.md`, `requirements.txt`, `.gitignore`, configuration examples and environment-variable example files.
- Established initial tests for environment and project structure.
- Created the initial data, source-code, test, documentation and report directories.

### Evidence / reported result
- Phase 0 test module: 7 tests passed in the combined test run reported after Phase 2.

## Phase 1 — Data Source Testing

**Status: Completed (according to the project report).**

### Sources selected in `docs/data_sources.md`

| Source | Intended role | Findings recorded in Phase 1/2 source report |
|---|---|---|
| InvestorGain | Primary candidate for subscription, outcomes and GMP; also used in the current master-list pilot | Server-side HTML; table selector reported as `table#reportTable`. |
| Chittorgarh individual IPO detail pages | Company fundamentals, valuation and issue details | Individual detail pages are server-rendered; summary/report pages were reported to use client-side rendering and return an HTML shell with no data tables. |
| SEBI | RHP/DRHP and statutory disclosures | Public prospectus documents; used for issue details and future RAG analysis. |
| NSE / BSE | Secondary verification, tickers and official listing information | Accessibility reported as moderate; some endpoints require session cookies. |

### Additional limitations documented
- Chittorgarh summary/report pages were not selected for direct raw-HTML scraping because they use React/client-side rendering.
- Chittorgarh individual IPO detail pages were selected instead.
- Chittorgarh subscription tables were reported as paywalled; InvestorGain was selected for subscription figures.
- GMP is unofficial and must be retained with a source and timestamp.
- Missing GMP must remain missing (`NaN`/empty), not be converted to zero.
- Mainboard and SME records must be distinguished.

### Evidence / reported result
- Phase 1 test module: 8 tests passed in the combined test run reported after Phase 2.
- Source test output and summary were saved under `reports/source_testing/`.

## Phase 2 — Dataset Construction & Validation Engine

**Status: Completed and reported verified.**

### Five canonical datasets

| File | Intended grain / purpose |
|---|---|
| `data/processed/ipo_features.csv` | One feature snapshot per `(ipo_id, prediction_stage, data_cutoff)`; 39 columns according to the Phase 2 report. |
| `data/processed/ipo_outcomes.csv` | One actual listing-outcome record per IPO; 7 columns. |
| `data/processed/ipo_gmp_history.csv` | Multiple timestamped GMP observations per IPO; 6 columns. |
| `data/processed/ipo_feature_sources.csv` | Feature-level provenance, including source URL, document/page, retrieval timestamp and verification status; 12 columns. |
| `data/processed/ipo_registry.csv` | Authoritative IPO directory and canonical identifier; 6 columns. |

### Core implementation reported
- `src/cleaning/ipo_id.py`: canonical IPO ID generation and registry management.
- `src/cleaning/cleaner.py`: numeric/date/subscription cleaning and leakage handling.
- `src/cleaning/validators.py`: schema, financial, temporal, target and leakage validation.
- `src/cleaning/dataset_manager.py`: dataset loading/saving, duplicate checks and quality reporting.
- `docs/data_dictionary.md`: comprehensive field definitions, units, periods, sources, eligibility and missing-value rules.
- Five processed CSV templates created with headers only and zero data rows.
- Synthetic fixtures isolated under `tests/fixtures/`.

### Canonical ID convention

`INMAIN-YYYY-NNNN`

The year component is based on the issue year, with sequential numbering managed through the registry manager. IDs must not be created from dataframe row numbers and must remain stable once assigned.

### Important modelling and data-integrity rules
1. **Pre-close vs post-close:** pre-close feature rows must not contain final subscription figures. Post-close rows may contain final subscription multiples, but must still be timestamped before listing.
2. **No target leakage:** listing opening price, listing gain and positive/negative outcome belong in `ipo_outcomes.csv`, not as model features.
3. **Point-in-time features:** every feature observation must be available on or before its `data_cutoff`.
4. **GMP missingness:** missing GMP is not zero; retain missingness and synchronise `gmp_missing`.
5. **Financial periods:** financial values must retain their reporting period. Do not mix annual and interim periods without metadata.
6. **Legitimate losses:** negative PAT, EBITDA or operating cash flow can be valid financial observations.
7. **Outcome definition:** listing gain is calculated from the listing-day opening price relative to the issue price. A zero or negative gain maps to `listing_positive = 0`.
8. **Provenance:** sourced values should retain source URL and, where relevant, document name/page and verification state.

### Evidence / reported result
- Phase 0 tests: 7 passed.
- Phase 1 tests: 8 passed.
- Phase 2 tests: 23 passed.
- **Combined test suite: 38/38 passed**, as reported in the Phase 2 completion report.

---

# 4. Phase 3 — Historical IPO Data Collection

**Status: In progress.**  
**Target period:** 2020–2026.  
**Pilot year:** 2020.

## 4.1 Phase 3 objective

Build a historical dataset of eligible Indian mainboard IPOs and collect the underlying information required for future analysis and prediction:
- IPO identity and issue dates;
- issue details and issue size;
- listing outcomes;
- GMP observations with timestamps and source URLs;
- subscription figures by investor category;
- financial and valuation metrics with reporting periods and provenance.

The collection process must preserve raw source snapshots, keep extracted candidates separate from verified records, and use the Phase 2 canonical schema and validation components when data is ready to be registered.

## 4.2 P3.1 — Build the IPO master list: work completed so far

### A. Historical source inspection
- The initial historical IPO performance page returned HTTP 200 but contained an empty placeholder table (`No data available`).
- A separate InvestorGain GMP Performance Tracker page returned populated server-side HTML.
- The populated table used `table#reportTable` and contained columns including IPO name, symbol, listing date, size, subscription, GMP, issue price and listing price.
- The 2020 inspection found 17 potential data rows in the tracker table, including a header/empty row in the HTML structure; the extraction script produced 16 candidate records.

### B. Candidate extraction
Created and ran:
- `inspect_investorgain_gmp_tracker.py`
- `collect_ipo_master_candidates.py`

Output:
- `data/raw/ipo_master/investorgain_gmp_tracker_2020.html`
- `data/interim/ipo_master/ipo_master_candidates_2020.csv`

Result:
- **16 candidate instrument records extracted** for 2020.
- Dates were normalised to `YYYY-MM-DD` where available.
- The source row was preserved in `raw_row_json`.
- No canonical IDs were assigned at this stage.

### C. Initial classification and symbol normalisation
Created and ran:
- `review_ipo_master_candidates.py`

Output:
- `data/interim/ipo_master/ipo_master_review_2020.csv`

Result:
- Yes Bank identified as an FPO and excluded from the ordinary IPO candidate set.
- Mindspace identified as a REIT and excluded from the ordinary company IPO candidate set.
- **14 IPO candidates remained pending verification.**
- Combined source symbol values were split into an NSE ticker symbol and a BSE scrip code where the pattern was recognised.
- Route Mobile's missing listing date was filled in the review data from a company annual-report source, while the original scrape was preserved separately.

### D. Detail-page URL discovery
Created and ran:
- `inspect_ipo_detail_links.py`
- Updated the candidate collector and review script to retain `detail_url`.
- Created and ran `verify_detail_urls.py`.

Result:
- **16/16 candidate instrument records had valid HTTPS detail-page URLs.**
- No missing detail URLs were reported.
- The two excluded instruments remain preserved in raw/interim records for audit purposes.

### E. Pilot date extraction
Created and ran:
- `extract_ipo_issue_dates.py`

Pilot company: Rossari Biotech.

Extracted dates:
- Opening: `2020-07-13`
- Closing: `2020-07-15`
- Listing/trading date: `2020-07-23`

Output:
- `data/interim/ipo_master/rossari_issue_dates_test.json`
- Raw HTML saved under `data/raw/ipo_master/`.

### F. Bulk date extraction
Created and ran:
- `bulk_ipo_date_collector.py`

Output:
- `data/interim/ipo_master/ipo_dates_2020.csv`
- Individual raw HTML snapshots under `data/raw/ipo_master/detail_pages/`.

Result reported in terminal:
- Total candidate records read: 16.
- Eligible candidates processed: 14.
- Excluded records skipped: 2.
- Successful date extractions: 14.
- Partial records: 0.
- Failed records: 0.
- Records flagged for review by the script: 0.
- All 14 extracted date sequences passed the script's chronological check.
- All 14 detail-page listing dates matched the historical reference values in the candidate data.

**Caution:** the 14/14 listing-date match is an internal source-consistency check, not independent official verification, because both values came from InvestorGain pages.

### G. Official verification ledger
Created and ran:
- `create_date_verification_ledger.py`

Output:
- `data/interim/ipo_master/ipo_date_verification_2020.csv`

The generated ledger contains 14 rows and separate fields for scraped values, official values, source names, source URLs, verification status and notes.

The last confirmed ledger output was:
- Rossari Biotech: `verified` (the RHP was used for issue dates and an NSE-hosted company filing/annual report was used for listing-date evidence).
- Remaining records: `pending`.
- **Last confirmed count: 1 verified, 13 pending.**

A correction to Rossari's listing evidence URL was suggested. SBI Cards evidence and a batch update for the remaining records were also prepared/proposed in the conversation, but no successful execution output or updated ledger has been provided after those steps. Treat SBI Cards and the other 12 as pending until the actual CSV confirms otherwise.

## 4.3 Current Phase 3 working files

| File | Role | Status |
|---|---|---|
| `data/raw/ipo_master/investorgain_gmp_tracker_2020.html` | Original 2020 tracker snapshot | Created |
| `data/interim/ipo_master/ipo_master_candidates_2020.csv` | 16 extracted instrument candidates | Created |
| `data/interim/ipo_master/ipo_master_review_2020.csv` | Classification, cleaned symbols and detail URLs | Created |
| `data/interim/ipo_master/ipo_dates_2020.csv` | 14 extracted date records | Created |
| `data/interim/ipo_master/ipo_date_verification_2020.csv` | Evidence-backed verification ledger | Created; 1 verified / 13 pending at last confirmed output |
| `data/raw/ipo_master/detail_pages/` | Individual detail-page HTML snapshots | Created |

Temporary exploration/collection scripts created in the project root include:
- `inspect_investorgain_history.py`
- `inspect_investorgain_gmp_tracker.py`
- `collect_ipo_master_candidates.py`
- `review_ipo_master_candidates.py`
- `verify_detail_urls.py`
- `inspect_ipo_detail_links.py`
- `extract_ipo_issue_dates.py`
- `bulk_ipo_date_collector.py`
- `create_date_verification_ledger.py`
- `correct_rossari_verification_sources.py` (proposed; execution not confirmed)
- `verify_sbi_cards.py` (proposed individual update; execution not confirmed)

These exploratory scripts should eventually be consolidated into tested modules under `src/collection/` rather than remaining as many independent root-level scripts.

## 4.4 Remaining work in Phase 3

### P3.1 — Finish the IPO master list
1. Complete independent official verification for all 14 eligible 2020 IPOs.
2. Resolve discrepancies between scraped data and official prospectuses/exchange records. Do not silently overwrite the scraped values.
3. Confirm first trading/listing date consistently. For the listing-day opening-price target, use the date on which trading actually commenced.
4. Verify historical NSE/BSE symbols and retain historical symbol changes separately from current symbols where needed.
5. Check completeness against official exchange/issuer issue records to determine whether the InvestorGain report missed any eligible 2020 mainboard IPOs.
6. Verify that every candidate is an ordinary mainboard IPO and not an FPO, REIT, InvIT, SME issue, or another instrument outside the project's defined scope.
7. Assign canonical IDs through the existing Phase 2 `IPORegistryManager`; do not manually generate IDs or use row numbers.
8. Populate `data/processed/ipo_registry.csv` only after records meet the project's registration rules. Preserve pending/uncertain records outside the canonical registry.

### P3.2 — Collect issue and listing details
- Confirm company legal name, historical trading symbol, exchange, issue opening/closing dates, listing/trading date, issue price/price band, issue size, fresh issue and OFS where available.
- Use prospectuses, allotment/issue documents and official exchange information as primary evidence.
- Retain source URL, source name, retrieval time and verification status.

### P3.3 — Collect actual listing outcomes
- Collect issue price, listing-day opening price and listing-day closing price.
- Calculate `listing_gain_pct = ((listing_open_price - issue_price) / issue_price) * 100` using the Phase 2 definition.
- Calculate `listing_positive = 1` only when listing gain is greater than zero; otherwise `0`.
- Store outcome targets only in `ipo_outcomes.csv`, not as input features.
- Prefer official exchange records for listing prices; record source and unresolved cases.

### P3.4 — Collect subscription data
- Collect QIB, NII, retail and overall subscription multiples, plus other categories when available and useful.
- Preserve category definitions and source timestamps.
- Keep final subscription values out of `pre_close` feature snapshots.
- Use them only in post-close snapshots when captured after issue close and before listing.

### P3.5 — Collect GMP history
- Collect multiple observations per IPO where historical data is available.
- Retain quoted GMP, recorded timestamp/date, source name, source URL and notes.
- Treat GMP as unofficial sentiment data.
- Never interpret missing GMP as zero; retain missingness explicitly.
- Do not invent historical timestamps where the source only provides a date or an undated value.

### P3.6 — Collect financial and valuation information
- Collect revenue, PAT, EBITDA, debt, net worth, operating cash flow, EPS, NAV, P/E, P/B and relevant peer metrics where available.
- Prefer RHP/DRHP restated financial statements and valuation sections.
- Attach explicit financial periods (for example FY2023, FY2024 or a defined interim period).
- Record source document, page number, URL, retrieval timestamp and verification status.
- Keep LLM/RAG-extracted values unverified until checked against the source document.

### P3.7 — Phase 3 integration and quality report
- Integrate collected data with the Phase 2 schemas and validation engine.
- Run duplicate, date, numeric, referential-integrity and provenance checks.
- Audit stage/cutoff eligibility to prevent look-ahead leakage.
- Generate a Phase 3 collection report listing coverage, missingness, exclusions, source quality, unresolved discrepancies and record counts by year.
- Expand from the 2020 pilot to 2021–2026 only after the 2020 collection logic is repeatable and verified.

---

# 5. Full development roadmap — all phases 0–10

The following is the official 11-phase project plan. A phase should be marked complete only when its deliverables, validation checks and documentation are in place.

## Phase 0 — Project Setup

**Purpose:** Establish a reproducible, secure development environment and a maintainable repository structure.

**Work to follow:**
- Inspect and establish the project directory structure.
- Configure Python environment and dependencies.
- Create `README.md`, `requirements.txt`, `.gitignore`, `.env.example` and configuration examples.
- Keep credentials and API keys in environment variables; never commit secrets.
- Add baseline tests for environment setup and imports.

**Deliverables:** working project skeleton, setup instructions, configuration examples and baseline tests.

**Completion criteria:** a fresh environment can be configured and the baseline test suite passes.

## Phase 1 — Data Source Testing

**Purpose:** Empirically determine which public sources provide usable and sufficiently reliable information.

**Work to follow:**
- Test candidate source URLs and endpoints for HTTP accessibility.
- Inspect server-rendered HTML, tables, headings, links and JavaScript-dependent pages.
- Test PDF availability, text extraction and scanned-page behaviour.
- Record access limitations, session requirements, source structure and terms/usage constraints.
- Save source-testing results and a source registry.

**Deliverables:** `docs/data_sources.md`, source test code, test results CSV, summary report and representative raw samples.

**Completion criteria:** each selected source has a documented role, tested access method, known limitations and fallback strategy.

## Phase 2 — Dataset Construction & Validation Engine

**Purpose:** Define canonical schemas and reusable safeguards before large-scale data collection.

**Work to follow:**
- Define `ipo_registry`, `ipo_features`, `ipo_outcomes`, `ipo_gmp_history` and `ipo_feature_sources` schemas.
- Implement canonical IPO identifiers and registry management.
- Define field types, units, required/optional status, missing-value rules and source expectations.
- Build cleaning, validation and dataset-management functions.
- Enforce point-in-time cutoffs, pre-close/post-close separation and target-leakage prevention.
- Add unit tests and synthetic fixtures that remain separate from real processed data.

**Deliverables:** five empty canonical CSV templates, `docs/data_dictionary.md`, `src/cleaning/` modules, quality report and automated tests.

**Completion criteria:** schemas and rules are documented, all tests pass, templates are empty and there are no fabricated real-data records.

## Phase 3 — Historical IPO Data Collection

**Purpose:** Populate the canonical data architecture with real historical mainboard IPO information.

**Work to follow:**
- Build and verify a complete master IPO list for 2020–2026.
- Register eligible IPOs with stable canonical IDs.
- Collect issue details, dates, listing outcomes, subscription data, GMP history, financials and valuation information.
- Preserve raw snapshots and field-level provenance.
- Separate extracted, verified, missing and unresolved values.
- Integrate records with Phase 2 schemas and validators.

**Deliverables:** raw source archives, verified/interim collection files, populated canonical datasets, provenance records and a Phase 3 collection/coverage report.

**Completion criteria:** coverage and exclusions are documented; critical records and targets are verified; schemas and validation rules pass; no unsupported values are fabricated; missingness and source limitations are reported.

## Phase 4 — Data Cleaning & Preprocessing

**Purpose:** Turn the collected source records into consistent analysis-ready and model-ready datasets.

**Work to follow:**
- Standardise names, symbols, dates, numeric values, units and financial periods.
- Resolve duplicate entities and record-level conflicts.
- Audit missingness and distinguish unavailable, not applicable and not yet collected values.
- Apply appropriate outlier checks without automatically deleting genuine extreme IPO outcomes.
- Validate issue/outcome calculations and referential integrity.
- Create reproducible preprocessing pipelines and dataset versions.
- Re-run time-cutoff and leakage audits.

**Deliverables:** cleaned datasets, preprocessing code/notebooks, data-quality summaries, documented transformations and reproducible train/evaluation-ready tables.

**Completion criteria:** transformations are repeatable and documented; no unexplained duplicates or invalid dates remain; missingness is explicit; all integrity and leakage checks pass.

## Phase 5 — Exploratory Data Analysis (EDA)

**Purpose:** Understand the historical IPO data before selecting features or training models.

**Work to follow:**
- Analyse IPO counts by year, sector, issue size and market regime.
- Study listing gain distributions and positive/negative listing frequencies.
- Explore GMP versus actual listing gains, including where GMP is missing.
- Analyse subscription categories and their relationship with listing performance.
- Explore valuation, profitability, leverage, issue composition and company size.
- Examine correlations, interactions, outliers, class imbalance and data availability.
- Look for temporal regime changes and sampling bias.
- Keep descriptive analysis separate from causal claims.

**Deliverables:** EDA notebooks, charts, statistical summaries and an EDA findings report with modelling implications and data limitations.

**Completion criteria:** key distributions, relationships, missingness, bias and limitations are documented; proposed features are plausible and available at the intended prediction time.

## Phase 6 — RHP/DRHP Intelligence Engine (RAG)

**Purpose:** Make IPO prospectuses searchable and extract document-grounded company, financial, valuation and risk information.

**Work to follow:**
- Accept RHP/DRHP PDF uploads and preserve document identity.
- Extract digital PDF text and tables; use OCR only for scanned pages where necessary.
- Preserve page numbers and section metadata through chunking.
- Build embeddings and a vector store (planned: ChromaDB) plus keyword/BM25 retrieval for hybrid search.
- Integrate the selected LLM API through environment-based configuration (planned: Gemini API).
- Answer questions using retrieved document evidence, page-level citations and concise excerpts.
- Abstain when the document does not support an answer.
- Treat document content as untrusted input, not as instructions to the system.
- Extract structured company overview, financials, issue structure, valuation/peers, promoters and risk factors.
- Store extracted fields with source document, page, retrieval evidence and verification status.

**Deliverables:** PDF ingestion pipeline, extraction and chunking modules, vector/keyword index, RAG query interface, structured extraction outputs, citations and tests.

**Completion criteria:** answers are grounded in the uploaded prospectus, citations resolve to relevant pages, unsupported questions trigger abstention, and extracted financial facts are not automatically treated as verified ground truth.

## Phase 7 — Fundamental Analysis Engine

**Purpose:** Convert verified company and issue information into interpretable fundamental indicators and a transparent analysis.

**Work to follow:**
- Calculate and interpret profitability, growth, leverage, liquidity and cash-flow metrics where source data supports them.
- Analyse P/E, P/B, EPS, NAV and peer comparisons with comparable periods and definitions.
- Assess fresh issue versus OFS, use of proceeds, promoter holding and dilution where applicable.
- Summarise material risks such as litigation, regulatory matters, customer/supplier concentration, debt, promoter matters, auditor observations and contingent liabilities.
- Define transparent scoring rules and weights; disclose unavailable inputs and avoid treating the score as a guaranteed return forecast.
- Connect evidence from the RAG engine to the fundamental report.

**Deliverables:** fundamental metrics module, peer/valuation analysis, risk assessment, transparent scoring method and per-IPO fundamental report.

**Completion criteria:** every reported metric has a definition, period and source; scoring is reproducible and explainable; missing information and limitations are visible.

## Phase 8 — Machine Learning Engine

**Purpose:** Train and evaluate models for listing outcome classification and listing-gain regression.

**Prediction targets:**
- Classification: `listing_positive = 1` when listing-day opening price is above issue price; otherwise `0`.
- Regression: `listing_gain_pct = ((listing_open_price - issue_price) / issue_price) * 100`.

**Work to follow:**
- Build separate pre-close and post-close feature pipelines.
- Ensure final subscription data is unavailable to pre-close models.
- Keep all listing outcome targets out of feature inputs.
- Engineer point-in-time features using only information available by the relevant cutoff.
- Establish simple baselines before more complex models.
- Compare suitable classification and regression algorithms.
- Use chronological splits or walk-forward validation rather than relying only on random splits.
- Evaluate classification with appropriate metrics (for example precision, recall, F1, ROC-AUC and confusion matrix) and regression with MAE, RMSE and suitable error analysis.
- Analyse calibration, class imbalance, feature importance and performance by year/market regime.
- Save reproducible pipelines, model versions and evaluation reports.

**Deliverables:** feature pipelines, baseline and candidate models, evaluation/backtesting reports, saved model artefacts and prediction interface.

**Completion criteria:** no look-ahead leakage; chronological evaluation is documented; model performance is compared against baselines; probabilities and point estimates are presented with uncertainty and limitations.

## Phase 9 — Dashboard & Application Integration

**Purpose:** Deliver the IPOVision capabilities through a usable application.

**Work to follow:**
- Build a Streamlit dashboard.
- Add IPO search/selection and company overview.
- Provide distinct pre-close and post-close prediction modes.
- Show classification probability and estimated listing-gain percentage, with model limitations.
- Integrate fundamental analysis and risk summaries.
- Add RHP/DRHP upload, document Q&A and cited extraction results.
- Display GMP history and subscription information with dates, sources and missing-data states.
- Connect the application to actual datasets and trained model artefacts.
- Handle invalid inputs, missing data, unavailable services and API errors.

**Deliverables:** integrated Streamlit application, reusable UI/data services, configuration instructions and application tests.

**Completion criteria:** end-to-end user flows work with real stored data and trained models; source evidence and limitations are visible; no fabricated demo outputs are presented as actual predictions.

## Phase 10 — Testing, Backtesting, Deployment & Documentation

**Purpose:** Validate the complete system, measure historical usefulness, deploy it and make it maintainable.

**Work to follow:**
- Run unit, integration, regression and end-to-end tests.
- Backtest predictions chronologically on historical IPOs without training on future information.
- Compare predictions with actual listing outcomes and document failure cases.
- Test missing data, malformed PDFs, unavailable sources, rate limits, API errors and configuration failures.
- Review secrets handling, input validation, dependency security and logging.
- Deploy to a suitable hosting environment and configure environment variables securely.
- Document setup, data sources, model methodology, limitations, architecture and user instructions.
- Record model/data versions and define a process for future updates.

**Deliverables:** test reports, backtesting report, deployed application, complete README/user guide, architecture documentation and known-limitations register.

**Completion criteria:** reproducible deployment, passing critical tests, documented backtesting and limitations, secure configuration and complete handover documentation.

---

# 6. Final intended IPOVision architecture

```text
                         IPOVision Application
                           Streamlit Dashboard
                               (Phase 9)
                                   |
        -------------------------------------------------------
        |                         |                           |
  IPO Data Engine           RHP/DRHP RAG Engine       Prediction Interface
  (Phase 3–5)                  (Phase 6)                  (Phase 8)
        |                         |                           |
  Verified IPO data        Prospectus ingestion       Pre-close model
  GMP / subscription       Hybrid retrieval           Post-close model
  Listing outcomes         Cited Q&A                  Classification
  Fundamentals             Structured extraction      Regression
        |                         |                           |
        ---------------- Fundamental Analysis -----------------
                                   (Phase 7)
                                     |
                       Evidence-backed IPO analysis
                                     |
                         Testing / Backtesting / Deploy
                                  (Phase 10)
```

Supporting foundation:
- Phase 0: environment and repository.
- Phase 1: tested source catalogue.
- Phase 2: schemas, canonical IDs, cleaning, validators and dataset manager.
- Phase 4: reproducible data preparation.
- Phase 5: analytical understanding before modelling.

---

# 7. Immediate next actions

The next work should continue in this order:

1. **Inspect the current `ipo_date_verification_2020.csv`.** Confirm whether the SBI Cards update and Rossari evidence-URL correction have actually been executed. The last confirmed ledger count in the progress shared so far is 1 verified and 13 pending.
2. **Run a single batch verification workflow for all remaining 2020 IPO candidates.** For each record, preserve scraped dates, official dates, source name/URL, verification status and discrepancy notes. Do not mark a record verified merely because the extracted date matches another InvestorGain page.
3. **Resolve all discrepancies.** Likhitha Infrastructure is a known example: the bulk extraction returned 7 October 2020 for issue closing, while the prospectus evidence identified in the work so far indicates 1 October 2020. Keep the scraped and official values separately and document the resolution.
4. **Check 2020 master-list completeness independently.** A successful 14-record scrape does not prove that the source contains every eligible 2020 mainboard IPO.
5. **Confirm the eligibility rules.** The Phase 1/2 source notes mention a typical issue-size threshold of at least ₹50 crore, but this should not be used as the only definition of mainboard eligibility. Use exchange/issue classification and document any edge cases.
6. **Only after verification and completeness review, assign canonical IDs** using the existing `IPORegistryManager` and populate `data/processed/ipo_registry.csv` through the existing `DatasetManager`/validation workflow.
7. **Then expand the proven 2020 collector to 2021, 2022, 2023, 2024, 2025 and 2026** (through the chosen cut-off).
8. Continue with the remaining Phase 3 datasets: outcomes, subscription, GMP history, financials/valuation and provenance.

## 7.1 Rules to preserve throughout the project

- Never fabricate IPO records, historical GMP observations, financial values, sources or timestamps.
- Preserve raw HTML/PDF snapshots and source URLs where permitted.
- Keep raw, interim and processed data separate.
- Keep original scraped values separate from corrected/official values.
- Record source, retrieval time, document/page and verification status for important fields.
- Do not convert missing GMP to zero.
- Do not put final subscription figures in pre-close feature rows.
- Do not put listing outcomes into model feature inputs.
- Use chronological/walk-forward evaluation for predictive modelling.
- Do not assign canonical IDs until the IPO is eligible and sufficiently identified; never use row numbers.
- Respect source terms, rate limits and access controls. Do not bypass CAPTCHA or authentication restrictions.

---

# 8. Phase completion tracker

Use this table as the project-level tracker and update it only when the relevant evidence and deliverables exist.

| Phase | Completion gate | Current state |
|---|---|---|
| P0 | Environment, repository structure, setup instructions and baseline tests work | Complete |
| P1 | Sources empirically tested and limitations documented | Complete |
| P2 | Five schemas, ID manager, cleaner, validators, dataset manager and tests implemented | Complete — 38/38 tests reported |
| P3 | Historical IPO master list and all required data collected, verified, provenance-preserved and validated | In progress — 2020 master-list pilot only |
| P4 | Reproducible cleaning/preprocessing pipeline and clean datasets | Pending |
| P5 | EDA and findings report completed | Pending |
| P6 | Document-grounded RHP/DRHP RAG engine implemented and evaluated | Pending |
| P7 | Explainable fundamental analysis implemented | Pending |
| P8 | Leakage-safe classification/regression models evaluated chronologically | Pending |
| P9 | Integrated Streamlit application works end to end | Pending |
| P10 | Backtesting, tests, deployment and documentation complete | Pending |

**Project status at this report date:** Phases 0–2 complete; Phase 3 in progress; Phases 4–10 not yet started.
