# IPOVision — Project Summary and Phase Tracker

**Last updated:** 16 Nov 2026 · **Environment:** Python 3.12, `.venv`, Windows (cmd) · **Project root:** `E:\ipo-analyzer1`

> Keep this file current. After each milestone update section 2 (status), section 10 (decisions), section 11 (corrections), section 12 (limitations) and section 14 (next steps).

---

## 1. What the project is

IPOVision estimates how an **Indian mainboard IPO will perform on listing day**.

- **Target:** `listing_gain_pct = (listing_open_price − issue_price) / issue_price × 100`
- **Label:** `listing_positive = 1` when the gain is above 0; a flat listing (exactly 0) counts as non-positive.
- **Question answered:** what is the probability that the IPO lists above its issue price, how risky is it (Low / Medium / High), and what is a plausible range for the gain?
- **Scope:** mainboard company IPOs only. SME-platform issues, REITs, InvITs, SM-REIT units and follow-on offers (FPOs) are excluded.
- **Product:** a Streamlit app (Home, Predict, Explorer, Model performance, About), with fundamentals scoring and prospectus question-answering still to come.

### The honest headline
The **final grey-market premium (GMP)** quoted the day before listing is by far the strongest signal. A one-feature logistic regression on GMP is the benchmark, and every richer model tested (more features, gradient boosting, random forest) failed to beat it. The model's contribution is a **calibrated probability, a risk band and a gain range** around the GMP, not a better forecast than the market's own number. This is a **listing-eve** model. Before the issue closes, size, market conditions and recent-IPO momentum carry almost no signal (AUC 0.513).

---

## 2. Status at a glance

7 of 11 phases complete, 2 in progress, 2 not started.

| Phase | Name | Status | Evidence |
|:-:|---|:-:|---|
| 0 | Setup and environment | ✅ | `config/`, `requirements.txt`, `tests/test_environment.py` |
| 1 | Source testing and scraper prototypes | ✅ | `src/collection/*`, `tests/test_phase1.py` |
| 2 | Dataset schemas and validation engine | ✅ | `src/cleaning/*`, `docs/data_dictionary.md`, `tests/test_phase2.py` |
| 3 | Historical data collection and loading | ✅ (scope-reduced) | 556 IPOs in `data/processed/`, validators 0 errors. Open closing item: verify the ~86 boundary labels (tracker A4) |
| 4 | Exploratory data analysis | ✅ | 8 figures, `docs/eda_summary.md` |
| 5 | RHP/DRHP question-answering (RAG) | ⬜ | `src/rag` is a stub |
| 6 | Fundamental analysis and scoring | ⬜ | `src/fundamental_analysis` is a stub |
| 7 | Baseline ML | ✅ | `src/evaluation/harness.py`, `reports/evaluation/scoreboard_v3.md` |
| 8 | Final model and validation | ✅ | `src/models/final_model.py`, `reports/evaluation/final_model_report.md`, `challenger_check.md` |
| 9 | Streamlit dashboard | 🔄 | Code for 5 pages delivered; smoke test and manual check pending |
| 10 | Testing, audit, polish | 🔄 | 65 tests passing (66 with the app smoke test); README updated; end-to-end audit, model card and data-dictionary refresh pending |

---

## 3. How the pieces fit together

```
Kaggle IPO file (652 rows, 2010–May 2026)        InvestorGain GMP tracker (2020–Nov 2026)
            │  clean: drop REITs/InvITs/FPOs/bad prices          │  parse cached pages (no price de-dup)
            └────────────── match on listing date + issue price, ───┘
                            choose by name similarity and issue size, one tracker row per IPO
                                           │  add IPOs Kaggle lacks (tracker-only rows)
                                           │  use tracker subscription where Kaggle disagrees by >25%
                                           ▼
                     model_base_v3.csv (556 IPOs, 2017–Nov 2026)
                       + features: size, subscription, GMP %, recent-IPO momentum, Nifty / India VIX
                                           │
     staging → Phase 2 validators (stage-aware) → data/processed/ (registry, features, outcomes, sources)
                                           │
        walk-forward harness ──► scoreboard, bootstrap intervals ──► final model + risk bands
                                           │
                                      Streamlit app
```

---

## 4. Data

### Sources
| Source | Used for | Notes |
|---|---|---|
| Kaggle `Initial_Public_Offering_(Updated).xlsx` | Listing prices, issue size, category subscription, 2010–May 2026 | `List Price` verified to be the listing-day **opening** price. About 67 recent company names are truncated (`...`) |
| InvestorGain GMP Performance Tracker (year pages) | Final GMP, total subscription, listing price, IPOs missing from Kaggle | Each year page returns at most ~100 rows (2025 starts 17 Feb, 2026 starts 24 Mar); GMP only from Sep 2020 |
| Yahoo Finance via `yfinance` | Nifty 50 and India VIX (cached in `data/raw/market_context.csv`) | Used for market-context features |

### Cleaning rules
- Removed: REITs, InvITs, SM-REIT units (name rules, and any unit price above ₹10,000), follow-on offers (Power Grid 2013, Yes Bank 2020, Vodafone Idea 2024), rows with invalid prices.
- Name rules use word boundaries, so operating companies such as SBI Funds Management are kept.
- Kaggle's total subscription disagreed with the tracker by more than 25% for **26 IPOs** (Kaggle lower in every case, apparently an intermediate-day value). Those rows use the tracker's value and drop Kaggle's category split.
- IPOs that share a listing date and issue price (for example Indiqube Spaces and GNG Electronics) are matched by name similarity and issue size, and each tracker row is used at most once.
- Missing GMP stays blank with `gmp_missing = 1`, never 0.
- Builds are deterministic: two runs of `build_v3.py` give an identical file hash.

### The dataset (`model_base_v3.csv` and `data/processed/`)
**556 IPOs**, 70.5% positive, final GMP for **452**.

| Year | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| IPOs | 36 | 24 | 16 | 14 | 65 | 39 | 59 | 90 | 104 | 109 |

| Table | Rows | Notes |
|---|---:|---|
| `ipo_registry` | 556 | Stable IDs `INMAIN-YYYY-NNNN` by listing year; retired IDs (`INMAIN-2025-0034`, `INMAIN-2026-0020`) are never reused |
| `ipo_features` | 556 | 39 columns; every row is `prediction_stage = listing_eve`, `data_cutoff` = day before listing |
| `ipo_outcomes` | 556 | Target and listing prices |
| `ipo_feature_sources` | 3,401 | One row per sourced value; all marked `unverified` |
| `ipo_gmp_history` | 0 | The tracker gives one untimestamped GMP per IPO, so this stays an empty template |

Fields left blank on purpose (deferred, not forgotten): exchange, issue open/close dates, price band, fresh issue / OFS split, financials and valuation ratios, `gmp_change`, `gmp_recorded_at`.

### Validation rules enforced in code
- Stages: `pre_close`, `post_close`, `listing_eve`. A `pre_close` row may not hold subscription data (look-ahead leakage error).
- GMP without its own timestamp is allowed only in `listing_eve` rows.
- Unit price above ₹10,000 is rejected. IDs must be valid and unique; the target must match the prices; missing GMP is never 0.

---

## 5. Evaluation framework and results

**Harness** (`src/evaluation/harness.py`, run by `root/run_scoreboard.py`): one set of rows (2020 onward, with GMP and total subscription, 452 rows), expanding walk-forward folds with test years 2022–2026, unweighted logistic regressions, identical rows for every model, paired bootstrap intervals (row and quarter-block), fixed-flag-rate recall, breakdowns by GMP zone and year, simple rule baselines, and two label variants (strict, and clear-only with |gain| > 2%).

**Test set:** 380 IPOs, 280 positive (73.7%), 100 non-positive. Majority-class accuracy 0.737.

| Model | AUC | Brier | ECE | Non-positives caught at 35% flagged |
|---|---:|---:|---:|---:|
| Prior only (train base rate) | 0.470 | 0.195 | 0.060 | n/a |
| **A: GMP only (benchmark)** | **0.869** | **0.133** | 0.074 | **0.79** |
| S: subscription only | 0.805 | 0.156 | 0.071 | 0.68 |
| B: GMP + subscription | 0.851 | 0.137 | 0.055 | 0.73 |
| C: B + size + market + momentum | 0.851 | 0.136 | 0.036 | 0.77 |
| D: C without GMP | 0.809 | 0.154 | 0.066 | 0.68 |
| E: size + market + momentum | 0.513 | 0.198 | 0.085 | 0.34 |
| Monotone gradient boosting (GMP, subscription) | 0.852 | 0.136 | 0.061 | n/a |
| Random forest on C's features | 0.844 | 0.135 | 0.050 | n/a |

- **Nothing beat A.** Against A, models B and C differ by +0.004 and +0.003 in Brier (intervals include 0) and by −0.018 and −0.019 in AUC. The challengers are no better either (ΔBrier +0.003 and +0.002, intervals include 0; random forest AUC lower by 0.025, interval excludes 0).
- **The simple rule "flag if GMP ≤ 5%"** flags 34.5% of IPOs and catches 78% of non-positives, so the model only matches a one-line rule at that flag rate. Its added value is calibrated probabilities.
- **By year (AUC of A):** 0.760 (2022), 0.911 (2023), 0.898 (2024), 0.891 (2025), 0.863 (2026).
- **Weak spot, the GMP 0–10% zone:** 115 IPOs, 44 non-positive; A's AUC is 0.633 there (0.710 for GMP ≤ 10%). Every model is close to a coin flip in that zone.
- **Label noise matters.** With ambiguous listings within ±2% removed, A's AUC rises from 0.869 to 0.923, and inside GMP ≤ 10% from 0.710 to 0.789.

---

## 6. The final model

`src/models/final_model.py`, saved by `root/train_final_model.py` to `src/models/artifacts/ipovision_final.joblib`.

- **Probability:** logistic regression on GMP % of issue price (452 IPOs). If no GMP is supplied: logistic regression on log total subscription (556 IPOs). If neither: the historical positive rate (70.5%). GMP is clipped to −50%…200%.
- **Risk band** on P(flat or lower): Low below 15%, Medium 15–40%, High 40% or more. Out-of-sample check:

| Band | IPOs | Predicted flat/lower | Actual flat/lower |
|---|---:|---:|---:|
| Low | 138 | 4.7% | 2.2% |
| Medium | 101 | 28.7% | 16.8% |
| High | 141 | 53.3% | 56.7% |

- **Gain range:** the GMP plus the 10th–90th percentile of past (actual gain − GMP) in the same GMP bucket. Built only from earlier years, it covered **84.2%** of 342 held-out IPOs (target 80%).

| GMP bucket | Residual range (points) | Mean width |
|---|---|---:|
| ≤ 0% | −12.1 to +4.2 | 14.4 |
| 0–10% | −8.7 to +5.4 | 15.5 |
| 10–30% | −14.5 to +10.1 | 31.2 |
| > 30% | −20.9 to +24.9 | 52.5 |

Example (issue price ₹100): GMP 0% gives 42% positive, High; GMP 15% gives 85% positive, Medium; GMP 40% gives 99% positive, Low, with an 80% gain range of +19% to +65%.

---

## 7. Exploratory findings (full text in `docs/eda_summary.md`)

- **Regime changes by year:** positive rate from 50% (2018) to 78% (2023, 2024); median gain from 1.4% (2018) to 36.3% (2020).
- **Subscription sorts outcomes:** about 34% positive below 3x, 61% at 3–10x, 91% at 30–100x, 99% above 100x.
- **GMP sorts outcomes:** 26% positive at GMP ≤ 0, 62% at 0–10%, 89% at 10–30%, about 99–100% above 30%.
- **GMP accuracy:** Spearman 0.874 with the actual gain, mean absolute error about 9 points. Misses are mostly about size, not direction.
- **False comfort:** 63 of 374 IPOs with a positive GMP (16.8%) listed flat or lower, roughly 49 of them in the 0–10% zone.
- **Flat listings:** 36 IPOs list at exactly 0.00% and 86 within ±2% of the issue price (15.5% of the data). For 7 of the exactly-flat ones the tracker quotes a different price, mostly +0.3% to +2.5%, consistent with NSE-versus-BSE opening prices.
- **Issue size** matters little; ₹2,500–5,000 crore issues are the weakest bucket (57% positive).

---

## 8. The app (`app/`, run with `streamlit run app\Home.py`)

| Page | What it does |
|---|---|
| Home | Counts, positive rate by year, gain distribution, outcomes by GMP bucket |
| 1 Predict | Enter issue price, GMP (₹ or %) and optional subscription; shows probability, risk band, 80% gain range, implied price range, and the closest past IPOs |
| 2 Explorer | Filter all IPOs by year, outcome, GMP, subscription and name; scatter of GMP vs actual gain; CSV download |
| 3 Model performance | Re-runs the walk-forward evaluation live: scoreboard, calibration curve, risk bands, interval coverage, GMP zones, by-year AUC |
| 4 About | Data, method and limitations |

Pending: Fundamentals page (Phase 6), Ask-the-prospectus page (Phase 5).

---

## 9. Quality and tests

**65 tests passing** (66 with `tests/test_app_smoke.py`):

| Area | Tests |
|---|---:|
| Phases 0–2 and the processed-store checks (headers, validators, ID integrity, no `pre_close` subscription, target math, GMP never 0, no synthetic fixture rows) | 44 |
| Round-2 rules (`listing_eve` stage, untimestamped GMP, unit-price limit, no REIT names, GMP join-collision guard) | 8 |
| Evaluation harness (no look-ahead folds, calibration error, flag metrics, reproducible bootstrap, label variants) | 5 |
| Final model (monotonicity, bands, fallbacks, interval, clipping, save/load, coverage) | 8 |

Validators were checked with deliberate corruption: 8 of 8 bad-data cases were caught.

---

## 10. Decision log

| Decision | Reason |
|---|---|
| Mainboard IPOs only | SME listings behave differently |
| Kaggle as the base, tracker as gap-filler and cross-check | ~630 IPOs already available; scraping each IPO was too slow |
| Kaggle `List Price` = listing-day opening price | Verified by hand; the target requires the open |
| Only the listing date is verified, not issue open/close dates | Nothing in the current model depends on them |
| Modelling window 2017 onward (GMP models from 2020) | 2012–2014 have too few IPOs; GMP exists from Sep 2020 |
| Missing GMP stays blank, never 0 | Zero would teach "no data = no premium" |
| REITs, InvITs, SM-REITs and FPOs excluded | Not operating-company IPOs; an FPO has no real listing gain |
| Snapshots are `listing_eve`, `data_cutoff` = day before listing | The tracker's GMP is a final, untimestamped value |
| Walk-forward validation only | No training on the future |
| Judge models by Brier, AUC, calibration and recall at fixed flag rates, not accuracy or recall at a 0.5 cut | 70% of IPOs are positive; a cut-off changes recall by changing how many IPOs are flagged |
| Final model = GMP-only logistic (pre-registered benchmark) | Nothing richer beat it on Brier |
| Unweighted logistic regressions | Keeps probabilities interpretable |
| Existing IDs are kept on rebuild; retired IDs never reused | IDs must be immutable |
| Improvements are parked until every phase works | Priority: a complete working system first |

---

## 11. Corrections log (errors found and fixed)

| What was wrong | Effect | Fix |
|---|---|---|
| GMP join on listing date + issue price after de-duplicating the tracker on that key | Indiqube Spaces received GNG Electronics' GMP (35.9% instead of 0%); one "false comfort" example and an EDA example were artifacts | Match by name and issue size; each tracker row used once; regression test |
| Name filter matched "fund" | SBI Funds Management (an operating company) was dropped | Word-boundary rules; the rebuild prints every removed row |
| SM-REIT units not caught by name rules | Two ₹10 lakh units (PropShare Titania and Celestia) sat in the processed store | Unit-price rule in the cleaner and the validator; IDs retired |
| Kaggle total subscription taken at face value | 26 IPOs had understated subscription (e.g. Sansera 0.53x vs 11.47x) | Tracker value used where the two disagree by more than 25% |
| Rows labelled `post_close` | They are listing-eve snapshots with GMP | New `listing_eve` stage; validator forbids untimestamped GMP earlier |
| "84% of non-positives caught" quoted at a 0.5 cut | Models flag different numbers of IPOs, so recall was not comparable | Recall now reported at fixed flag rates |
| "Pre-close AUC 0.55" from the first baseline | Different rows and years from later runs | Replaced by the harness result (size/market/momentum alone: 0.513) |
| Set C presented as the headline model | It does not beat GMP alone | GMP-only logistic is the benchmark and final model |
| Phase 2 test asserted empty processed tables | Failed once real data was loaded | Replaced by processed-store tests |

---

## 12. Known limitations

1. The final GMP is a listing-eve value with no timestamp, so there is no true pre-issue model.
2. GMP is unofficial and sources disagree.
3. The tracker's year pages return at most ~100 rows, so Jan–Feb 2025 and Jan–Mar 2026 listings have no GMP.
4. About 15.5% of IPOs list within ±2% of the issue price, where the label depends on which exchange's open is used.
5. Provenance values are marked `unverified`; subscription for 2017–2019 rows and for the uncovered 2025–26 windows cannot be cross-checked.
6. Small samples: 380 test IPOs, 100 of them non-positive. Differences under about 0.03 AUC are noise.
7. Company names are truncated for about 67 recent Kaggle rows; joins use listing date, issue price, name similarity and size.
8. Market features use the trading day before listing, later than the true issue-close cutoff (not used by the final model).
9. No financial, valuation or anchor-investor features yet.
10. Scripts still live in `root/`, not in `src/` modules (backlog).

---

## 13. Improvement tracker status

| Item | Status |
|---|---|
| A1 REIT/unit rows, A2 join collision, A3 stage relabel, A5 deterministic sorts, A8 subscription conflicts, A9 name false positives | ✅ |
| A6 environment (pin `yfinance`, retire old scripts with hard-coded paths) | 🔄 confirm |
| A7 tests for new rules | ✅ mostly (momentum-cutoff test still open) |
| B1–B4, B6 harness, bootstrap, baselines, label variants, pre-registered choice | ✅ |
| F1 version control | 🔄 first commit and `.gitignore` check for `.env` |
| A4 verify boundary labels, C1 three-class label, C2–C5, D1–D9, E1–E8, F2–F8, G1–G5 | ⬜ parked until every phase works |

---

## 14. Next steps

1. **Phase 9, finish:** run `python -m pytest tests/ -q` (expect 66) and `streamlit run app\Home.py`; check Home (556 IPOs, ~70.5% positive), Predict (GMP 0%, price 100 → 42% positive, High), and Model performance (bands match section 6).
2. **Phase 6, fundamentals:** implement the checklist's two scores as tested pure functions.
   - *Fundamental score* (100): business quality 15, revenue and profit growth 15, profitability 10, debt 10, cash flow 10, promoter 10, peer comparison 10, valuation 15, structure and use of funds 5. Bands: 80+ Excellent, 70–79 Good, 60–69 Average, 50–59 Weak, below 50 Avoid or caution.
   - *Listing score* (100): GMP 30, QIB subscription 25, total subscription 15, market sentiment 10, valuation 10, sector 5, size 5. Bands: 80+ strong, 70–79 good, 60–69 uncertain, below 60 weak.
   - Evaluate the Listing score as a rule-based baseline on our data, add red-flag rules, and add a Fundamentals page (manual entry until financial data is collected).
3. **Phase 5, prospectus Q&A:** PDF text extraction with page numbers, chunking, hybrid retrieval (BM25 plus sentence embeddings), ChromaDB index, Gemini answers with page citations, and an Ask-the-prospectus page. Needs a Gemini API key in `.env` and 2–3 RHP PDFs.
4. **Phase 10:** model card, data-dictionary and modelling-decisions refresh (`docs/modelling_decisions.md` still describes the original plan), one-command pipeline, final audit.
5. **Then** the parked improvement items, starting with A4 and the three-class label.

---

## 15. File map and run order

| Purpose | Path |
|---|---|
| Raw Kaggle file; cached tracker pages; market cache | `data/raw/`, `data/raw/gmp/tracker_<year>.html`, `data/raw/market_context.csv` |
| Intermediate outputs | `data/interim/kaggle/` (`kaggle_clean_candidates.csv`, `model_base_v3.csv`), `data/interim/gmp/` |
| **Final datasets** | `data/processed/` |
| Evaluation and model reports | `reports/evaluation/` (`scoreboard_v3.md`, `final_model_report.md`, `challenger_check.md`) |
| Figures and EDA tables | `reports/figures/`, `reports/eda/` |
| Trained model | `src/models/artifacts/ipovision_final.joblib` |
| Core code | `src/cleaning/`, `src/evaluation/harness.py`, `src/models/final_model.py`, `app/` |

Pipeline (all from `E:\ipo-analyzer1`):

```
python root\clean_kaggle.py              # Kaggle cleaning -> kaggle_clean_candidates.csv
python root\gmp_step.py                  # fetch and cache tracker pages, first GMP merge
python root\build_v2.py                  # one-off: downloads the Nifty/VIX cache (needs yfinance)
python root\build_v3.py                  # clean join, exclusions, features -> model_base_v3.csv
python root\load_processed_v3.py         # stage the four processed tables and validate
python root\write_processed.py           # validated, atomic write to data/processed/
python root\run_scoreboard.py            # walk-forward scoreboard and bootstrap intervals
python root\train_final_model.py         # final model, risk bands, interval coverage
python root\challenger_check.py          # boosting and forest challengers
python -m pytest tests/ -q               # 65 tests (66 with the app smoke test)
streamlit run app\Home.py                # the app
```

Resume work:

```
cd E:\ipo-analyzer1
.\.venv\Scripts\activate
python -m pytest tests/ -q
```
