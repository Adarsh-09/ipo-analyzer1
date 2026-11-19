# IPOVision: Complete Project Summary and Honest Evaluation

**Date:** 17 Nov 2026 · **Author:** Adarsh Wali · **Status:** all code phases built; 91 automated tests passing at the last run; final audit and two measurements still pending (section 13)

This document is written to be critical. It separates what is **demonstrated**, what is **plausible but unverified**, and what is **not done**, so that someone evaluating the project can calibrate how much to trust each part.

---

## 0. The verdict in seven lines

1. **What it is:** a leakage-safe data pipeline, an evaluation framework and an app that estimate the probability that an Indian mainboard IPO lists above its issue price, from the grey-market premium (GMP) quoted the day before listing.
2. **The model is simple on purpose and by outcome:** a one-feature logistic regression on GMP. Every richer model tested (more features, gradient boosting, random forest, a checklist score) failed to beat it.
3. **The signal is real but it is the market's, not the model's.** GMP alone gives AUC 0.87 and Brier 0.133 against 0.195 for the base rate. The model's contribution is calibration, risk bands and honest uncertainty.
4. **It is weakest exactly where help would matter most:** when GMP is at or below 10%, outcomes are close to a coin flip (AUC 0.71 for the whole zone, 0.63 for GMP 0–10%).
5. **It is a listing-eve tool.** Before the issue closes, size, market conditions and recent-IPO momentum carry almost no signal (AUC 0.51). No true pre-issue model exists.
6. **The engineering and evaluation are the strongest parts:** validators that enforce leakage rules, deterministic builds, walk-forward validation, calibration checks, paired bootstrap intervals, and reported negative results.
7. **The weakest parts:** no external verification of the data against exchange filings, a small test set (100 non-positive listings), an unvalidated fundamentals score, and a prospectus Q&A feature whose language-model step has never run end to end.

---

## 1. What was built

| Component | What it does | Maturity |
|---|---|---|
| Data pipeline (`root/`, `src/cleaning/`) | Cleans and merges two sources into 556 IPOs; stable IDs; provenance table; stage-aware validators | Working, tested, scripts not yet packaged as modules |
| Evaluation harness (`src/evaluation/`) | Walk-forward folds, probability metrics, bootstrap intervals, baselines, label variants | Working, tested |
| Final model (`src/models/`) | GMP logistic regression, fallbacks, risk bands, 80% gain range | Working, tested, validated out-of-sample on 380 IPOs |
| Scoring module (`src/fundamental_analysis/`) | The checklist's 100-point fundamental and listing scores | Unit-tested; listing score evaluated on data; fundamental score **not validated** |
| Prospectus Q&A (`src/rag/`) | PDF text extraction, hybrid retrieval, citation checks, optional language model | Retrieval verified informally on one real DRHP; **generation untested with a real model** |
| Streamlit app (`app/`) | Home, Predict, Explorer, Model performance, About, Checklist scores, Prospectus Q&A | Smoke-tested for all 7 pages; not user-tested; not deployed |
| Documentation | README, model card, EDA summary, this file, data dictionary | Mostly current; `modelling_decisions.md` still describes the original plan |

---

## 2. The data

**556 mainboard IPOs, listed 2017 to 5 Nov 2026.** 70.5% listed positive (opening price above issue price); a final GMP exists for 452.

| Year | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| IPOs | 36 | 24 | 16 | 14 | 65 | 39 | 59 | 90 | 104 | 109 |

**Sources:** a public Kaggle IPO file (453 of the rows, after cleaning), InvestorGain's GMP performance tracker (GMP for every year from Sep 2020, plus 103 IPOs missing from the Kaggle file), and Yahoo Finance for index data.

**What was done to the data:** REITs, InvITs, SM-REIT units and follow-on offers were excluded; IPOs that share a listing date and issue price are matched by name and issue size; where Kaggle's total subscription disagreed with the tracker by more than 25% (26 IPOs), the tracker's value was used; snapshots are labelled `listing_eve`, with the cut-off the day before listing.

**Honest status of the data:**

| Question | Answer |
|---|---|
| Are the rows internally consistent? | Yes. Validators check IDs, stages, leakage rules, target math and "missing GMP is never zero". Deliberate corruption tests were all caught |
| Are they correct? | **Not independently verified.** Every sourced value is marked `unverified`. The listing price was hand-checked as the *opening* price for a sample; about 86 labels sit within ±2% of the issue price and have not been checked individually |
| Is the list complete? | **Unknown.** It was never compared with an independent count of all mainboard IPOs. Gaps in the Kaggle file were found by accident (a two-month block in 2024, everything after May 2026) |
| Is the GMP a pre-listing value? | Probably, but **not proven for every year**. The tracker gives one untimestamped final value. In 2020, the last records I inspected were from before listing |
| Is there coverage for the whole period? | No GMP before Sep 2020; the tracker's year pages return about 100 rows, so some early-2025 and early-2026 listings have no GMP |
| Can the 2017–2019 rows be cross-checked? | No (no tracker data), so Kaggle's subscription values there are unverified, and 26 rows elsewhere were wrong |
| Licensing and terms of use | The Kaggle file's licence and the tracker's terms were **not reviewed**. Scraping used a polite rate limit and cached pages. Raw data is not committed |

---

## 3. Method

**Target:** `listing_gain_pct = (listing open − issue price) / issue price × 100`. The class is positive when the gain is above 0 (a listing exactly at the issue price counts as non-positive; 36 IPOs do this).

**Validation:** expanding-window walk-forward, test years 2022–2026, each fold trained only on earlier years. Same 452 rows (GMP and subscription present, 2020 onward) for every model. Training sizes 72, 110, 169, 259 and 356; test sizes 38, 59, 90, 97 and 96, totalling **380 test IPOs (280 positive, 100 non-positive)**.

**Metrics:** Brier score (primary), AUC, PR-AUC for the non-positive class, log-loss, expected calibration error, recall of non-positives at fixed flag rates, paired bootstrap of differences (by IPO and by quarter), and breakdowns by GMP zone and year.

**Benchmark and decision rule, fixed in advance:** GMP-only logistic regression; a richer model replaces it only if it improves Brier with a bootstrap interval that excludes zero.

---

## 4. Results

### 4.1 Model comparison (strict labels, 380 test IPOs)

| Model | AUC | Brier | Calibration error |
|---|---:|---:|---:|
| Base rate only | 0.470 | 0.195 | 0.060 |
| **GMP only (final model)** | **0.869** | **0.133** | 0.074 |
| Subscription only | 0.805 | 0.156 | 0.071 |
| GMP + subscription | 0.851 | 0.137 | 0.055 |
| GMP + subscription + size + market + momentum | 0.851 | 0.136 | 0.036 |
| Subscription + size + market + momentum (no GMP) | 0.809 | 0.154 | 0.066 |
| Size + market + momentum only | 0.513 | 0.198 | 0.085 |
| Gradient boosting (monotone) | 0.852 | 0.136 | 0.061 |
| Random forest | 0.844 | 0.135 | 0.050 |
| Checklist listing score (logistic on the score) | 0.831 | 0.147 | 0.061 |

Against the GMP-only model: adding features changes Brier by +0.002 to +0.004 (intervals include zero) and lowers AUC by 0.017 to 0.025. The checklist score is reliably worse (ΔAUC −0.039, interval −0.067 to −0.016; ΔBrier +0.014, interval +0.006 to +0.026).

### 4.2 By year, zone and label definition (GMP-only model)

| Test year | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|
| AUC | 0.760 | 0.911 | 0.898 | 0.891 | 0.863 |

| GMP zone | IPOs | Non-positive | AUC |
|---|---:|---:|---:|
| above 10% | 201 | 10 | 0.772 |
| 0–10% | 115 | 44 | 0.633 |
| at or below 0% | 64 | 46 | 0.621 |
| at or below 10% (combined) | 179 | 90 | 0.710 |

With the 64 IPOs listing within ±2% of the issue price removed from the test set, the AUC is 0.923 (Brier 0.094): a large share of the apparent difficulty is label ambiguity, not model weakness.

### 4.3 Risk bands and gain range

| Band | IPOs | Predicted flat/lower | Actual flat/lower |
|---|---:|---:|---:|
| Low (under 15%) | 138 | 4.7% | 2.2% |
| Medium (15–40%) | 101 | 28.7% | 16.8% |
| High (40% or more) | 141 | 53.3% | 56.7% |

The 80% gain range, built only from earlier years, covered **84.2%** of 342 held-out IPOs (77% when GMP is at or below 0%, n = 48; 84%, 89% and 84% in the other buckets). Mean widths: about 14 points at or below 10% GMP, 31 points at 10–30%, 53 points above 30%.

### 4.4 Comparison with a simple rule

"Flag the IPO if GMP is 5% or lower" flags 34.5% of IPOs and catches 78% of the non-positives (precision 59.5%). The model, at the same flag rate, catches 79%. **At that operating point the model is no better than the one-line rule.** Its advantage is calibrated probabilities across the whole range.

### 4.5 Exploratory findings

- Positive rate rises with total subscription (about 34% below 3x, 91% at 30–100x, 99% above 100x) and with GMP (26% at GMP ≤ 0, 62% at 0–10%, 89% at 10–30%, about 99–100% above 30%).
- GMP correlates 0.87 with the actual gain (rank correlation) and its mean absolute error is about 9 points.
- 63 of 374 IPOs with a positive GMP (16.8%) listed flat or lower, most with a GMP between 0 and 10%.
- The positive rate varies by year from 50% (2018) to 78% (2023 and 2024).
- Checklist bands (all 452 IPOs with a GMP): 80 or more, 139 IPOs, all positive; 70–79, 88.7%; 60–69, 80.0%; below 60, 50.5% (210 IPOs). The band results are **in-sample**, since I wrote the point mappings after seeing the EDA.

### 4.6 Prospectus Q&A (informal)

Indexed one 499-page DRHP (1,982 passages) and ran the nine checklist questions in retrieval-only mode. By my reading of the printed passages, 7 of 9 questions returned a relevant page in the top three; the financial-summary and capital-structure questions were weaker (numeric tables). **This is a reading, not a scored evaluation.** A Gemini call failed with a billing/permission error, so answer generation has never run with a real model.

---

## 5. How to read these results honestly

- **The headline AUC of 0.87 is mostly GMP, which is public sentiment information.** An investor who sees the GMP already has most of what the model has.
- **Out-of-sample, but with design choices informed by all the data.** The choice of GMP as the feature, the bucket edges (0, 10, 30) and the band cut-offs (15%, 40%) came from exploring the whole dataset, including the test years. The reported numbers are therefore somewhat optimistic about design. A genuinely clean test needs **prospective** validation on future IPOs, which has not been done.
- **The test set is small.** With 100 non-positive test IPOs, the AUC of the final model is uncertain by a few hundredths (I did not report an interval for it alone). Differences between the better models are within noise, which is why the conclusion rests on the paired intervals and on parsimony, not on small rankings.
- **Calibration is decent but not perfect.** Predicted positive rate 70.9% against 73.7% actual; the Medium band is pessimistic (28.7% predicted, 16.8% actual).
- **The result generalises only as far as the data does:** one boom-heavy period (2023–2025) dominates, and no prolonged weak market is represented.
- **"Beats the baseline" is relative to a weak baseline.** The base rate scores Brier 0.195. The meaningful comparison, the raw GMP, is ahead of the model for predicting the size of the gain (mean absolute error about 8 to 9 points against 8.8 for a fitted ridge model).

---

## 6. Phase-by-phase status

| Phase | Status | Honest note |
|:-:|---|---|
| 0 Setup | ✅ | Pinned requirements, config, directory test |
| 1 Source testing | ✅ | Scrapers prototyped; the per-IPO GMP history is behind a paywall and was not circumvented |
| 2 Dataset engine | ✅ | Validators are the project's best asset |
| 3 Data collection | ✅ scope-reduced | The original plan (scrape 2021–2024 from detail pages, build pre-close snapshots, GMP history) was replaced by a Kaggle-plus-tracker approach. `pre_close` snapshots, issue dates, financials and anchor data were **not collected** |
| 4 EDA | ✅ | 8 figures, written summary |
| 5 Prospectus Q&A | 🔄 | Retrieval works on one document; no scored retrieval evaluation yet; language-model path untested with a real model |
| 6 Fundamentals | ✅ with a caveat | Scoring code is tested; **the weights come from a checklist and the point mappings are my assumptions**. No outcome data exists to validate the fundamental score |
| 7 Baseline ML | ✅ | |
| 8 Final model | ✅ | The outcome is a negative result about added complexity |
| 9 Dashboard | ✅ | Seven pages, smoke-tested; no user testing; not deployed |
| 10 Audit and polish | 🔄 | This document, the model card and the README exist; final clean-environment run pending |

**Original goals not delivered:** a pre-close model (the data carries no signal), a live GMP tracker, two-stage predictions, SHAP explanations (not applicable to a one-feature model), valuation and anchor-investor features.

---

## 7. Evidence strength

| Claim | Evidence |
|---|---|
| Walk-forward results are free of look-ahead | Strong: a test checks that every fold's training data ends before its test data starts; features use only earlier listings |
| GMP-only beats the richer models | Moderate: paired bootstrap on 380 IPOs; intervals for Brier include zero, so the claim is "no improvement", not "worse" |
| Risk bands are ordered and meaningful | Moderate: out-of-sample, 380 IPOs, clear monotone pattern |
| The 80% range is well calibrated | Moderate: 84.2% coverage on 342 IPOs |
| The data are correct | Weak: automated consistency only; `unverified` provenance |
| The list of IPOs is complete | Unverified |
| The model works in a different market regime | Unknown |
| The prospectus answers are accurate | Unverified (language model not run); retrieval informally checked on one document |
| The fundamental score predicts anything | Unverified |

---

## 8. My assessment of each dimension

These scores are subjective, on a 1 to 5 scale, and written by the assistant that helped build the project.

| Dimension | Score | Reason |
|---|:-:|---|
| Problem framing | 4 | Clear target, explicit stages, honest about timing |
| Data coverage | 3 | 556 IPOs, but completeness unverified and GMP only from 2020 |
| Data verification | 2.5 | Strong automated checks, weak external verification |
| Leakage control | 4.5 | Enforced in code and tests; residual design optimism |
| Modelling | 3 | Appropriate and minimal; the best model has one feature; no tuning |
| Evaluation rigour | 4.5 | Calibration, bootstrap, baselines, label variants, negative results |
| Predictive usefulness | 3 | Real signal, mostly GMP; weak in the zone that matters |
| Product (app) | 3.5 | Complete and tested; not user-tested or deployed |
| Prospectus Q&A | 2.5 | Retrieval promising, generation untested, no scored evaluation |
| Fundamentals scoring | 2 | Heuristics, unit-tested, unvalidated |
| Software engineering | 3.5 | 91 tests, validators, pinned requirements; scripts in `root/`, no CI, no one-command pipeline |
| Documentation | 4 | README, model card, EDA summary, this file |
| Reproducibility | 3 | Pinned environment, deterministic builds; needs a manual data download and live scraping |
| **Overall** | **about 3.5 / 5** | A strong, honest applied-ML portfolio project; **not** a production predictor |

---

## 9. Weaknesses and risks, ranked

1. **Unverified data.** Any silent error in rows that could not be cross-checked (2017–2019, the uncovered 2025–26 windows) would pass every automated check.
2. **Edge-of-class label noise.** 86 IPOs (15.5%) list within ±2% of the issue price; 36 exactly at it; for 7 of the exactly-flat ones the two sources quote different prices.
3. **Small, one-regime test set.** 100 non-positive test cases, mostly from a strong IPO market.
4. **Design choices informed by the whole dataset.** Mild optimism in every reported number.
5. **Dependence on an unofficial, scrapable source.** The tracker can change format, cap rows or restrict access.
6. **No prospective validation.**
7. **Unreviewed licences and terms** for the Kaggle file and the tracker.
8. **Unproven RAG generation path** and an unvalidated fundamental score; both are shown in the app, so they must stay clearly labelled.
9. **Scripts are not packaged**, and there is no automated end-to-end rebuild.

---

## 10. Errors found during development

The project was built with an AI assistant, and several errors were found and corrected through review and testing. They are listed because they show where the pipeline was fragile:

| Error | Consequence | Fix |
|---|---|---|
| GMP join on listing date and issue price after de-duplicating the tracker | One IPO received another's GMP (Indiqube and GNG Electronics) | Match by name and issue size; collision test |
| A name rule that matched "fund" | An operating company (SBI Funds Management) was dropped | Word-boundary rules; removal list printed on every rebuild |
| SM-REIT units not caught by name rules | Two ₹10 lakh units in the dataset | Unit-price rule in the cleaner and the validator |
| Kaggle total subscription taken at face value | 26 IPOs had understated subscription | Reconciled against the tracker |
| Rows labelled `post_close` | They were listing-eve snapshots with GMP | New stage and a validator rule |
| Recall quoted at a 0.5 cut-off | Not comparable between models | Recall at fixed flag rates |
| An early "pre-close AUC 0.55" | Different rows and years from later runs | Replaced by the harness result (0.51) |
| A test that required empty data tables | Failed once data was loaded | Replaced by processed-store tests |
| Prospectus Q&A message said "no language model" after a failed call | Misleading | Reasons and hints now explicit |

The pattern suggests more undetected errors are likely wherever rows cannot be cross-checked.

---

## 11. Machine learning used

**Algorithms:** logistic regression (final model and all harness models), ridge regression and random forest regression (early baselines), random forest classifier and monotone histogram gradient boosting (challengers), baselines (base rate, median, GMP as the forecast, GMP threshold rules), empirical quantile intervals, hybrid retrieval (BM25 plus sentence embeddings, reciprocal rank fusion). **Not used:** deep learning, XGBoost, SHAP, clustering, hyperparameter search, formal conformal prediction, isotonic calibration, Bayesian models.

**Concepts:** supervised classification and regression; feature engineering; missing-data handling; leakage prevention; walk-forward validation; regularisation; class imbalance; overfitting and parsimony; ablation; ensembles; monotonic constraints; AUC, PR-AUC, Brier, log-loss, calibration error and reliability curves; recall at fixed operating points; subgroup and regime analysis; paired and block bootstrap; prediction intervals and coverage; pre-registered benchmarks; label noise and robustness; record linkage; reproducibility and automated testing.

---

## 12. How to describe it, and how not to

**Supportable:**
- "Built a leakage-safe data pipeline and walk-forward evaluation framework for Indian IPO listings (556 IPOs, 2017–2026), with validators that enforce stage-based leakage rules."
- "Found that a one-feature GMP logistic regression (AUC 0.87, Brier 0.133 against 0.195 for the base rate) was not beaten by richer models, tested with paired block-bootstrap intervals; added calibrated risk bands and an 80% gain range (84% out-of-sample coverage)."
- "Delivered a Streamlit app with prediction, exploration, model-performance and prospectus-search pages; 91 automated tests."

**Avoid:**
- "Predicts IPO listing gains with 87% accuracy" (AUC is not accuracy, and the signal is the GMP).
- "Beats the market", "trading signal" or any investment claim.
- "Advanced ML" (the final model is one feature; more complex models were tested and rejected).
- "Verified data" (provenance is unverified).
- "Prospectus Q&A answers questions" without saying that retrieval was only informally checked and the language model step was not run.

**Questions an evaluator may ask:**
- *Why not use more features?* They were tested and added nothing measurable on Brier.
- *What is the model's real value?* Calibration, risk bands and honest ranges around a market signal.
- *Could this make money?* No evidence of that; it is evaluated on listing-day opening prices only and nothing here considers whether an IPO can be bought at the issue price.
- *What did you get wrong?* See section 10.
- *What would you do next?* Section 13.

---

## 13. What would improve it most, in order

1. **Collect timestamped GMP prospectively** for every new IPO from the day it opens; this is the only route to a true pre-close model and to clean prospective validation.
2. **Verify the data:** compare the IPO list with an independent count; check the roughly 86 boundary labels and a random sample of 20 IPOs against exchange data.
3. **Handle the boundary properly:** a three-class label (clear gain, flat, clear loss) or an ordinal model.
4. **Add anchor-investor, valuation and offer-for-sale features** and test them inside the weak GMP zone.
5. **Finish the prospectus work:** score retrieval against hand-labelled pages (script ready), table-aware chunking for financial tables, and one real language-model run.
6. **Package the scripts** as tested modules with one command to rebuild; add continuous integration.
7. **Review licences and terms**, then decide what can be published.

**Pending right now:** fill the gold-page file and run `root\rag_eval.py`; refresh `summary_of_phases.md` and the README; run the whole pipeline once from a clean environment.

---

## 14. Reproducing it

```
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
# place Initial_Public_Offering_(Updated).xlsx in data\raw\
python root\clean_kaggle.py
python root\gmp_step.py
python root\build_v2.py            # one-off: market data cache
python root\build_v3.py
python root\load_processed_v3.py && python root\write_processed.py
python root\run_scoreboard.py && python root\train_final_model.py && python root\challenger_check.py
python -m pytest tests/ -q
streamlit run app\Home.py
```

Key outputs: `data/processed/`, `reports/evaluation/` (scoreboard, final model report, challenger check, listing-score baseline), `src/models/artifacts/ipovision_final.joblib`, `docs/model_card.md`, `docs/eda_summary.md`.

*Disclaimer: research and education only. Nothing here is investment advice.*
