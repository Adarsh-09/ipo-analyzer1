# IPOVision — Data-Driven Intelligence for Indian Mainboard IPO Listing Analysis

[![Python 3.11 | 3.12](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Market: Indian Mainboard](https://img.shields.io/badge/Market-Indian%20Mainboard%20IPOs-orange.svg)]()
[![RAG: Hybrid Search + Gemini](https://img.shields.io/badge/RAG-PyMuPDF%20%2B%20ChromaDB%20%2B%20Gemini-green.svg)]()

> **Tagline:** Data-driven intelligence for IPO listing analysis.  
> **Market Focus:** Indian Mainboard IPOs only (BSE & NSE). SME IPOs are strictly excluded in v1.

---

## 1. Project Overview

**IPOVision** is an end-to-end data engineering, machine learning, and document intelligence application built to systematically analyze historical Indian Mainboard IPOs. Rather than treating IPO evaluation as a speculative guessing game or relying blindly on unverified grey market rumors, IPOVision constructs reproducible data pipelines, point-in-time features, strictly leak-proof machine learning models, and an automated RHP/DRHP prospectus analysis engine.

### Core Objectives
1. **Binary Classification:** Predict whether an IPO is likely to list at a premium ($\text{listing\_positive} = 1$) or discount ($\text{listing\_positive} = 0$) relative to its issue price.
2. **Regression:** Estimate the percentage listing-day gain or loss ($\text{listing\_gain\_pct}$) based on listing morning open prices.
3. **Calibrated Probabilities:** Provide trustworthy listing probabilities rather than overconfident binary predictions.
4. **Transparent Explainability:** Surface the key fundamental, valuation, subscription, and sentiment drivers behind every prediction.
5. **RHP/DRHP RAG Intelligence Engine:** Extract structured financials, borrowing profiles, and litigation risk factors directly from statutory Red Herring Prospectus (RHP) PDF documents with verifiable page citations.

---

## 2. Two-Stage Prediction Architecture

To reflect real-world market constraints, IPOVision enforces two distinct prediction stages with strictly isolated feature pipelines:

```
                            +-------------------------------------------+
                            |          STATUTORY RHP & ANNOUNCEMENT     |
                            +-------------------------------------------+
                                                  |
                                                  v
==================================== STAGE A: PRE-CLOSE ====================================
Cutoff Moment: While subscription window is OPEN (e.g. Day 1 or Day 2 morning)
Features Used:
  - Issue price & price band
  - Issue size, fresh issue cr, OFS cr (Fresh vs OFS split)
  - Balance sheet & income statement (Revenue, EBITDA, PAT, Net Debt)
  - Valuation metrics (P/E, P/B, Peer-group valuation premium/discount)
  - Point-in-time Grey Market Premium (GMP) & short-term trend
  - Broad market trend (Nifty 50 return before cutoff)
STRICT BARRIER: Final subscription figures are STRICTLY FORBIDDEN (to prevent data leakage).
=============================================================================================
                                                  |
                                                  v
=================================== STAGE B: POST-CLOSE ====================================
Cutoff Moment: After subscription window CLOSES (bidding tallies finalized)
Features Used:
  - All eligible Stage A pre-close features
  - Final QIB subscription rate (Institutional demand proxy)
  - Final NII subscription rate (High-net-worth demand proxy)
  - Final Retail individual subscription rate
  - Overall subscription multiple
  - Final recorded pre-allotment GMP
STRICT BARRIER: Listing-day open/close prices are STRICTLY FORBIDDEN.
=============================================================================================
                                                  |
                                                  v
                                      [ LISTING DAY MORNING ]
                                 Target: Listing Open Price Gain %
```

---

## 3. High-Level System Architecture

```text
                                  IPOVision System
                                         |
     -------------------------------------------------------------------------
     |                         |                         |                   |
Data Collection & Web     Data Cleaning &          ML Engine &         RHP/DRHP RAG
Scraping Modules          Normalization          Model Validation    Intelligence Engine
     |                         |                         |                   |
 - NSE/BSE Listing Data   - Unit Standardisation   - Pre-close Model    - PDF Text/Tables
 - SEBI Offer Filings       (₹ Cr & ₹ / share)     - Post-close Model   - OCR Fallback
 - Bidding Subscriptions  - Missing Value Flags    - Walk-Forward CV    - ChromaDB Store
 - GMP Time Series Logs   - Duplicate Auditing     - Baselines Audit    - Gemini Citation
     |                         |                         |                   |
     -------------------------------------------------------------------------
                                         |
                                         v
                            Streamlit Analytics Dashboard
      [Home] [IPO Explorer] [Fundamentals] [GMP Tracker] [Predictions] [RHP RAG]
```

---

## 4. Repository Folder Structure

```text
IPOVision/
├── README.md                           # Master project documentation & portfolio guide
├── requirements.txt                    # Pinned, compatible Python dependencies
├── .gitignore                          # Strict git ignore (secrets, venv, large binaries)
├── .env.example                        # Template for API keys and environment variables
│
├── config/
│   ├── settings.yaml                   # Active local configuration (git-ignored)
│   └── settings.example.yaml           # Master configuration template & defaults
│
├── data/
│   ├── raw/                            # Immutable raw scraped HTML/JSON/CSV files
│   ├── interim/                        # Partially cleaned, merged staging data
│   └── processed/                      # Production tables (ipo_features, ipo_outcomes, ipo_gmp)
│
├── notebooks/
│   ├── 01_source_testing.ipynb         # Data source accessibility & rate-limit validation
│   ├── 02_data_collection.ipynb        # Historical scraping and manual verification
│   ├── 03_data_cleaning.ipynb          # Unit conversion, deduplication, sanity checks
│   ├── 04_exploratory_analysis.ipynb   # Listing gain distributions & correlation analysis
│   ├── 05_baseline_models.ipynb        # Benchmarking simple baselines & leak audits
│   └── 06_model_evaluation.ipynb       # Chronological walk-forward model evaluation
│
├── src/
│   ├── __init__.py                     # Package initialization
│   ├── config.py                       # Centralized settings and environment loader
│   ├── collection/                     # Scrapers for NSE, BSE, SEBI filings, and GMP
│   ├── cleaning/                       # Standardization, unit conversions (Cr), deduplication
│   ├── features/                       # Pre-close vs Post-close feature engineering pipelines
│   ├── fundamental_analysis/           # Rule-based financial health and risk indicators
│   ├── models/                         # Classifiers and regressors (Logistic, RF, XGBoost)
│   ├── evaluation/                     # Chronological cross-validation and calibration metrics
│   └── rag/                            # RHP/DRHP document extractor, Chroma store, and Gemini RAG
│
├── app/
│   ├── streamlit_app.py                # Main entrypoint for Streamlit web interface
│   ├── pages/                          # Multi-page dashboard modules
│   └── components/                     # Reusable UI widgets and Plotly charts
│
├── models/                             # Serialized trained model weights and preprocessors
├── reports/
│   ├── figures/                        # Generated EDA charts and ROC/PR curves
│   └── evaluation/                     # Model performance and walk-forward backtest reports
│
├── tests/
│   ├── __init__.py
│   └── test_environment.py            # Environment, schema, and directory integrity tests
│
└── docs/
    ├── data_dictionary.md              # Detailed schema specification and field dictionary
    ├── modelling_decisions.md          # Methodological decisions, leak guardrails, metrics
    └── sources_and_limitations.md      # Data provenance, GMP disclaimers, and boundaries
```

---

## 5. Getting Started — Windows PowerShell Setup

Follow these exact steps to set up and run IPOVision on Windows using PowerShell.

### Step 1: Open PowerShell and Navigate to the Project
```powershell
cd e:\ipo-analyzer1
```

### Step 2: Create a Virtual Environment with Python 3.12 (or 3.11)
> **Note:** Python 3.11 or 3.12 is recommended for optimal compatibility with C-extension machine learning packages (`scikit-learn`, `xgboost`, `chromadb`).

```powershell
# Create virtual environment using the Python 3.12 launcher
py -3.12 -m venv .venv

# If using Python 3.11 instead:
# py -3.11 -m venv .venv
```

### Step 3: Activate the Virtual Environment
If you encounter an execution policy restriction, set the scope policy for the current process:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
```
*(Your prompt should now display `(.venv)`)*

### Step 4: Upgrade Pip and Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables
Copy `.env.example` to `.env` and insert your Google Gemini API key:
```powershell
Copy-Item .env.example .env
```
Open `.env` in your editor and provide:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Step 6: Verify the Environment Setup
Run the automated test suite to confirm directory structures, configurations, and schemas:
```powershell
python tests/test_environment.py
```
*(Expected Output: `Ran 7 tests ... OK`)*

---

## 6. The 3 Primary Datasets

All data generated in IPOVision adheres strictly to the specifications documented in [docs/data_dictionary.md](file:///e:/ipo-analyzer1/docs/data_dictionary.md):

1. **`ipo_features.csv`:** Stores point-in-time features frozen at the prediction cutoff. Features include company fundamentals, issue structure, valuation multiples, early/late GMP, and stage-dependent subscription rates.
2. **`ipo_outcomes.csv`:** Stores verified listing day outcome labels (`listing_date`, `issue_price`, `listing_open_price`, `listing_gain_pct`, `listing_positive`).
3. **`ipo_gmp_history.csv`:** Stores timestamped grey market premium quotes over time to capture market sentiment velocity and volatility.

### Immutable Data Handling Rules
- **No Zero Imputation for Missing Sentiment:** Absent GMP or subscription data is never replaced with `0`. It remains `NaN` and is accompanied by binary quality flags (`gmp_missing`).
- **Consistent Monetary Units:** Aggregate financials are recorded in **₹ Crore**, and share prices in **₹ / share**.
- **Deterministic Identifier:** Linked via `ipo_id` (e.g. `2024-SWIGGY`).

---

## 7. Machine Learning Methodology

1. **Strict Look-Ahead Leakage Prevention:** Features are strictly constrained to information published before the prediction cutoff.
2. **Walk-Forward Chronological Cross-Validation:** Shuffling time-dependent financial market data across time causes look-ahead bias. IPOVision evaluates models using expanding-window chronological splits:
   $$\text{Train on } [T_0 \dots T_k] \longrightarrow \text{Validate on } [T_{k+1}]$$
3. **Downside Risk Prioritization:** Metric selection optimizes for **Negative Class Recall** (catching IPOs that list at a discount) and **Brier Score** (calibrated probabilities), rather than deceptive overall accuracy.
4. **Baseline Benchmarking:** Every ML model is systematically compared against:
   - Majority Class Classifier
   - GMP-implied Listing Gain
   - Historical Median Listing Gain Regressor

---

## 8. Development Phases & Roadmap

| Phase | Description | Deliverable | Status |
| :---: | :--- | :--- | :---: |
| **Phase 0** | **Project Setup & Environment Initialization** | **Project skeleton, config, tests, documentation** | **COMPLETED** |
| Phase 1 | Data Source Testing & Scraper Prototyping | Verified HTTP endpoints, headers, and rate limits | *Next* |
| Phase 2 | Dataset Construction & Validation Engine | Schema validators, duplicate auditors, CSV storage | *Pending* |
| Phase 3 | Historical Mainboard IPO Data Collection | Verified historical sample dataset with provenance | *Pending* |
| Phase 4 | Exploratory Data Analysis (EDA) | Statistical distributions, GMP correlation report | *Pending* |
| Phase 5 | RHP/DRHP RAG Intelligence Engine | PDF extraction, OCR fallback, ChromaDB, Gemini RAG | *Pending* |
| Phase 6 | Fundamental Analysis Integration | Transparent financial scoring & risk flags | *Pending* |
| Phase 7 | Baseline ML Models | Baseline classifiers and regressors with leak audits | *Pending* |
| Phase 8 | Advanced ML & Chronological Validation | Tuned XGBoost/Random Forest with walk-forward CV | *Pending* |
| Phase 9 | Streamlit Multi-Page Dashboard | Interactive analytics UI, GMP tracker, and RAG chat | *Pending* |
| Phase 10 | Testing, Documentation & Final Polish | End-to-end integration tests & GitHub polish | *Pending* |

---

## 9. Educational Value & Portfolio Highlights

This project demonstrates core competencies required of a modern Machine Learning & Data Engineer:
- **Clean Architecture:** Strict decoupling between data ingestion, cleaning, feature generation, modeling, and presentation.
- **Time-Series Integrity:** Domain-appropriate leakage prevention and chronological walk-forward validation.
- **Hybrid Retrieval RAG:** Combining dense vector similarity (Sentence Transformers) with sparse keyword retrieval (BM25) over hundreds of pages of complex financial prospectuses.
- **Factual Integrity:** Model calibrations, downside recall metrics, and strict refusal to fabricate financial data or guarantee speculative market gains.

---

## 10. Legal Disclaimer
*IPOVision is developed solely for educational and research purposes. It does not provide investment advice or securities recommendations. Predictions are statistical estimates, not financial guarantees.*
