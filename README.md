# IPOVision 2.0

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-132%20passed-success?logo=pytest&logoColor=white)](file:///tests/)
[![LLM](https://img.shields.io/badge/LLM-Gemini%202.5%20Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Market](https://img.shields.io/badge/Market-NSE%20%7C%20BSE%20Mainboard-orange)](#)
[![Dataset](https://www.kaggle.com/datasets/karanammithul/ipo-data-india-2010-2025)

> **Empirical probability modeling & citation-grounded prospectus RAG intelligence for Indian mainboard IPO listings (2017–2026).**

---

## ⚡ Key Benchmark Scoreboard

Evaluated via strict **out-of-sample walk-forward validation (2022–2026)** — models are trained strictly on past cohorts and tested on unseen future years:

| Metric | IPOVision Final Model | Baseline / Benchmark Context |
|:---|:---:|:---|
| **ROC-AUC** | **0.869** | Strong discrimination between debut winners & discounts |
| **Brier Score** | **0.133** | Superior probability calibration (Base rate benchmark: 0.195) |
| **Log Loss** | **0.407** | Strict information-theoretic probability penalty score |
| **ECE (Calibration Error)** | **0.041** | Empirical outcomes track forecast risk bins within 4% |
| **Recall @ 35% Flag** | **80.6%** | Accurately identifies >80% of listing discounts |
| **80% Gain Range Coverage**| **78.4%** | Conformal interval coverage across held-out listings |

---

## 🧭 System Capabilities

1. **Empirical Probability & Pricing Engine**
   - Calibrated logistic regression over final Grey Market Premium (GMP).
   - Subscription-tier demand mapping fallback when GMP is unquoted or unavailable.
   - Non-parametric 80% listing gain interval and implied debut price calculation.

2. **Statutory Prospectus RAG Workbench**
   - Ingests 400+ page Red Herring Prospectus (RHP / DRHP) PDFs.
   - Hybrid BM25 + dense MiniLM vector retrieval via persistent ChromaDB.
   - Extracts 9 SEBI statutory areas (Financial summary, P/E & peer valuation, Risk factors, Related party transactions, Objects of issue, Litigation, Promoters, Working capital, Capital structure).
   - Structured JSON validation, schema-constrained repair retry, and exact quotation page verification against original document excerpts.

3. **Checklist & Fundamental Scoring**
   - 0–100 fundamental score mapped strictly from verified & approved evidence.
   - Listing checklist score incorporating external demand, size, and market momentum signals.

---

## 🖥️ Application Architecture

```
app/
├── Home.py                       # Macro IPO market pulse, annual win-rates & gain histograms
└── pages/
    ├── 1_Predict.py              # Live probability, 80% listing interval & subscription fallback
    ├── 2_Explorer.py             # Historical database explorer with scatter filters & CSV export
    ├── 3_Model_Performance.py    # Walk-forward benchmark scoreboard & calibration reliability
    ├── 4_Prospectus_Workbench.py # 4-step RHP PDF ingestion, RAG extraction, evidence review & Q&A
    └── 5_About.py                # Provenance, boundary conditions & data governance
```

---

## 🚀 Quickstart

```bash
# 1. Clone repository
git clone https://github.com/Adarsh-09/ipo-analyzer1.git
cd ipo-analyzer1

# 2. Virtual environment setup
python -m venv .venv
.venv\Scripts\activate      # Windows (.venv/bin/activate on Linux/macOS)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure Gemini API key (for RHP RAG Extraction & Q&A)
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# 5. Launch Application
streamlit run app/Home.py
```

---

## 🧪 Test Verification

Run the comprehensive test suite (132 tests covering models, RAG extraction, scoring, and UI smoke rendering):

```bash
pytest
```

---

## ⚖️ Empirical Boundaries & Disclaimer

- **Mainboard Only**: SME platform IPOs, REITs, and InvITs are excluded.
- **Listing-Eve Signal**: GMP is evaluated the evening prior to listing; it does not replace long-term fundamental diligence.
- **Research Project**: IPOVision is an empirical research and educational system. It does not provide financial or investment advice.
