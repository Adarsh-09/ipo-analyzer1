# IPOVision

**Calibrated risk estimates for Indian mainboard IPO listings.**

IPOVision estimates the chance that an Indian mainboard IPO lists above its issue price, labels the risk (Low / Medium / High), and gives a plausible range for the listing gain. It combines a validated data pipeline, a walk-forward evaluation framework and a Streamlit app.

> **Research and learning project. Not investment advice.** GMP (grey-market premium) is unofficial market sentiment, models can be wrong, and past listings do not guarantee future ones.

---

## Headline results

Walk-forward validation: each test year (2022–2026) is predicted by models trained only on earlier years, on identical rows for every model. 380 test IPOs, 280 positive (73.7%).

| Model | AUC | Brier (lower is better) |
|---|---:|---:|
| Base rate only | 0.470 | 0.195 |
| Size + market + momentum (no GMP, no subscription) | 0.513 | 0.198 |
| Subscription only | 0.805 | 0.156 |
| **GMP only (benchmark and final model)** | **0.869** | **0.133** |
| GMP + subscription + size + market + momentum | 0.851 | 0.136 |
| Gradient boosting, random forest | 0.852, 0.844 | 0.136, 0.135 |

What this means:

- **GMP is the signal.** The final GMP quoted the day before listing beats every richer model tested. Paired bootstrap intervals show no Brier improvement from adding anything to it.
- **The model adds calibration, not a better forecast than the market.** Out-of-sample, the **Low / Medium / High** bands saw 2.2% / 16.8% / 56.7% of IPOs list flat or lower, and the 80% gain range covered 84% of held-out IPOs.
- **Be honest about the weak zone.** When GMP is at or below 10%, outcomes are close to a coin flip, and the app says so.
- **It is a listing-eve model.** Before the issue closes, size, market conditions and recent-IPO momentum carry almost no signal (AUC 0.51).

Full numbers: `reports/evaluation/scoreboard_v3.md`, `reports/evaluation/final_model_report.md`, `docs/eda_summary.md`.

---

## The data

**556 mainboard IPOs, listed 2017 to Nov 2026**, 70.5% positive, final GMP for 452 of them.

| Source | Used for |
|---|---|
| Public Kaggle IPO dataset (not redistributed here) | Listing prices, issue size, subscription |
| InvestorGain GMP Performance Tracker | Final GMP, total subscription, IPOs missing from the Kaggle file |
| Yahoo Finance (`yfinance`) | Nifty 50 and India VIX |

Data quality is treated as part of the project:

- REITs, InvITs, SM-REIT units and follow-on offers are excluded; mismatched subscription values are reconciled; IPOs sharing a listing date and issue price are matched by name and size.
- A validation engine enforces **look-ahead leakage rules** (a `pre_close` row may never hold subscription data; an untimestamped GMP is allowed only in `listing_eve` snapshots), target consistency, valid unique IDs, and "missing GMP is never zero".
- Every sourced value is stored with its provenance in `ipo_feature_sources`, currently marked `unverified`.
- The project keeps a log of errors found and fixed (`summary_of_phases.md`, section 11).

---

## Project status

| Phase | Status |
|---|---|
| 0 Setup, 1 Source testing, 2 Dataset engine | ✅ |
| 3 Data collection and loading | ✅ (scope-reduced) |
| 4 Exploratory analysis | ✅ |
| 7 Baseline models, 8 Final model | ✅ |
| 9 Streamlit app | 🔄 five pages built, verification in progress |
| 6 Fundamentals scoring | ⬜ planned |
| 5 Prospectus (RHP) question-answering | ⬜ planned |
| 10 Audit and polish | 🔄 |

Details, decisions and limitations: [`summary_of_phases.md`](summary_of_phases.md).

---

## Quick start (Windows)

Requires Python 3.12.

```
git clone <your-repo-url>
cd ipo-analyzer1
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Data is not included

`data/` is git-ignored. To reproduce the pipeline:

1. Download the Kaggle IPO file `Initial_Public_Offering_(Updated).xlsx` and place it in `data/raw/`.
2. The GMP tracker pages are fetched and cached by the scripts below. The scraper uses a polite rate limit and caches every page.
3. No API key is needed for the core pipeline. The planned prospectus Q&A feature will need `GEMINI_API_KEY` in a local `.env` file (never commit it).

### Rebuild the pipeline

```
python root\clean_kaggle.py              # clean the Kaggle file
python root\gmp_step.py                  # fetch and cache the GMP tracker pages
python root\build_v2.py                  # one-off: download the Nifty / VIX cache
python root\build_v3.py                  # join, exclusions, features -> model_base_v3.csv
python root\load_processed_v3.py         # stage the four processed tables and validate them
python root\write_processed.py           # validated, atomic write to data/processed/
python root\run_scoreboard.py            # walk-forward scoreboard with bootstrap intervals
python root\train_final_model.py         # final model, risk bands, interval coverage
python root\challenger_check.py          # boosting and random-forest challengers
```

### Run the tests

```
python -m pytest tests/ -q
```

65 tests (66 with the app smoke test) cover the validators, the processed-store invariants, the evaluation harness and the final model.

### Run the app

```
streamlit run app\Home.py
```

| Page | What it does |
|---|---|
| Home | Dataset overview, positive rate by year, outcomes by GMP bucket |
| Predict | Enter issue price, GMP and optional subscription; get a probability, risk band, 80% gain range and the closest past IPOs |
| Explorer | Filter and chart all IPOs, download the filtered rows |
| Model performance | Live walk-forward evaluation: scoreboard, calibration, risk bands, weak zones |
| About | Data, method, limitations |

---

## Repository layout

```
app/                  Streamlit app (Home.py, pages/, components/)
config/               Settings
data/                 raw/, interim/, processed/   (git-ignored)
docs/                 Data dictionary, source notes, EDA summary
notebooks/            Source-testing notebook
reports/              evaluation/, figures/, eda/, data_quality/
root/                 Pipeline scripts (to be moved into src/ modules)
src/
  collection/         HTTP client and scrapers
  cleaning/           Registry/IDs, cleaner, validators, dataset manager
  evaluation/         Walk-forward harness, metrics, bootstrap
  models/             Final model and saved artifact
  features/, fundamental_analysis/, rag/   (planned)
tests/                Unit, integration and app smoke tests
summary_of_phases.md  Complete project summary and tracker
```

---

## Method in brief

- **Target:** `listing_gain_pct = (listing_open_price − issue_price) / issue_price × 100`; positive means above 0.
- **Model:** logistic regression on GMP as a percentage of the issue price (subscription-only fallback, then the base rate). Risk band from P(flat or lower): Low under 15%, Medium 15–40%, High 40% or more. The gain range is the GMP plus the 10th–90th percentile of past (actual gain − GMP) in the same GMP bucket.
- **Validation:** expanding-window walk-forward; unweighted models; Brier score, AUC, calibration error and recall at fixed flag rates; paired row and quarter-block bootstrap intervals; strict and clear-only label variants.

## Known limitations

- The final GMP is a single untimestamped value, so this is a listing-eve model, not a pre-issue one.
- GMP is unofficial and sources disagree.
- The tracker's year pages return at most about 100 rows, so some early-2025 and early-2026 listings lack GMP.
- About 15% of IPOs list within 2% of the issue price, where the label depends on which exchange's open is used.
- No financial, valuation or anchor-investor features yet; provenance is not yet verified against exchange filings.
- Small test set (380 IPOs), so differences under about 0.03 AUC are noise.

## Roadmap

1. Finish and verify the app.
2. Fundamentals scoring based on a published IPO checklist (fundamental and listing scores), including a rule-based baseline.
3. Prospectus question-answering with page citations (hybrid retrieval over RHP PDFs).
4. Model card, refreshed data dictionary, one-command pipeline.
5. Improvements: label handling near zero, anchor-investor and valuation data, prospective GMP logging, move scripts into tested modules.

## Disclaimer

This project is for research and education. It does not provide investment advice, and nothing here recommends buying or selling any security.

## Author

Adarsh Wali — [github.com/Adarsh-09](https://github.com/Adarsh-09)
