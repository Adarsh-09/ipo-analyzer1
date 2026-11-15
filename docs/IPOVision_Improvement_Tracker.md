# IPOVision — Improvement Tracker

**Created:** 15 Nov 2026 · **Based on:** `summary_of_phases.md`, `eda_summary.md`, `IPOVision_Progress_and_Roadmap.md`, `modelling_decisions.md`, `requirements.txt`, `build_v2.py`, `baseline_models.py`, `build_features.py`, `baseline_v2_gmp.txt`, `ipo_outcomes.csv`, `ipo_features.csv`, `model_base_v2.csv`, and the project directory listing.

**How to use:** tick `[x]` when an item's "Done when" condition is met. Add the date and a one-line note under the item. Re-run the scoreboard (section 1) after every modelling change and paste the new numbers into the change log (section 12).

**Tags:** priority **P0** (do first) → **P3** (later) · effort **S** (≤ ½ day), **M** (1–3 days), **L** (> 3 days).

---

## Start here (P0 list)

- [ ] A1 Remove the two REIT-type rows
- [ ] A2 Fix the GMP join collision (Indiqube / GNG)
- [ ] A3 Relabel the feature stage as `listing_eve`
- [ ] B1 Build one evaluation harness
- [ ] B2 Add paired bootstrap intervals
- [ ] B3 Always report the same baselines
- [ ] D1 Re-specify the logistic model (unweighted, calibrated, regularised)
- [ ] E1 Start prospective daily GMP logging
- [ ] F1 `git init` and protect `.env`

---

## 1. Scoreboard — numbers to beat

Reproduced exactly from `build_v2.py` (logistic regression, `class_weight="balanced"`, expanding walk-forward, test years 2022–2026). **379 test rows, 100 non-positive, 279 positive.** Intervals are approximate row-bootstrap 95% intervals.

| Feature set | AUC | Note |
|---|---:|---|
| A  GMP only | **0.862** (0.821–0.900) | Best on every threshold-free metric below |
| B  GMP + total subscription | 0.845 | ΔAUC vs A = −0.017 (−0.029, −0.005) |
| C  B + size + market + momentum ("headline") | 0.848 | ΔAUC vs A = −0.014 (−0.035, +0.006) |
| D  C without GMP | 0.803 | |
| S  Total subscription only | 0.799 | D adds ≈ 0 over this |
| E  Size + market + momentum only | 0.522 | Coin flip |

**Probability quality** (unweighted logistic, same rows): Brier A 0.135 · B 0.139 · C 0.139 · prior-only 0.195. Log-loss A 0.414 · B 0.420 · C 0.416 · prior-only 0.579. With balanced weights, C's mean predicted P(positive) is 0.608 against an actual 0.736, so those probabilities are not calibrated.

**Where the negatives are** (test set):

| GMP zone | Rows | Non-positive | AUC A | AUC C | AUC subscription-only |
|---|---:|---:|---:|---:|---:|
| ≤ 0% | 63 | 45 | 0.694 | 0.537 | 0.340 |
| 0–10% | 115 | 44 | 0.613 (0.51–0.72) | 0.599 (0.49–0.70) | 0.533 (0.42–0.64) |
| > 10% | 201 | 11 | 0.742 | 0.767 | 0.770 (only 11 negatives, not meaningful) |
| **≤ 10% combined** | **178** | **89** | **0.706** | **0.660** | — |

89 of the 100 test negatives have GMP ≤ 10%, and in that region half of all IPOs are negative.

**Simple rules any model must beat at the same flag rate:**

| Rule | IPOs flagged | Negatives caught | Precision |
|---|---:|---:|---:|
| flag if GMP ≤ 0 | 63 (16.6%) | 45% | 0.71 |
| flag if GMP ≤ 5 | 130 (34.3%) | 77% | 0.59 |
| flag if GMP ≤ 10 | 178 (47.0%) | 89% | 0.50 |

**Operating point:** at threshold 0.5, A flags 50.9% of IPOs (recall 0.91, precision ≈ 0.47, accuracy 0.707 vs 0.736 majority); C flags 40.6% (recall 0.84, accuracy 0.773). At the same flag rate (193 rows) A, B and C all catch 0.91 of negatives.

**By year, AUC A / C:** 2022 0.760 / 0.728 (n = 38) · 2023 0.911 / 0.861 (59) · 2024 0.898 / 0.911 (90) · 2025 0.862 / 0.849 (97) · 2026 0.862 / 0.857 (95).

**Label sensitivity:** 28 of the 100 test negatives are exactly 0.00% gains. Dropping the 64 rows with |gain| ≤ 2% lifts AUC to 0.918 (A) and 0.895 (C).

**Magnitude (MAE, percentage points):** predict-median 19.43 · ridge (set C) 8.82 · **GMP used directly 8.25** (median absolute error 5.22). The 30 rows with |gain| > 60% produce 21% of GMP's total absolute error.

---

## 2. Findings confirmed in your files

| ID | Finding | Severity | Fix |
|---|---|:-:|---|
| F1 | **Two REIT-type units are in the dataset.** PropShare Titania (`INMAIN-2025-0034`, listed 2025-08-04, issue ₹1,060,000, flat 0.00%) and Propshare Celestia (`INMAIN-2026-0020`, listed 2026-04-24, issue ₹1,050,000, open ₹999,900.01, −4.77%). By name these look like SM-REIT units (please confirm). The project excludes REITs. Neither has GMP, so the current test set is unaffected, but they sit in the registry, the EDA counts and the momentum pool. | High | A1 |
| F2 | **GMP join collision.** Indiqube Spaces and GNG Electronics both listed 2025-07-30 at ₹237 and both received GMP 35.86%. It is the only duplicated (listing date, issue price) pair in the file. The 35.9% looks like GNG's (gain +47.7%), so Indiqube's GMP (gain −7.7%) is probably wrong. The EDA's "Indiqube sign flip" example and one of the 63 "false-comfort" cases are likely artifacts. Dropping the pair moves AUC A/C from 0.862/0.848 to 0.867/0.854. | High | A2 |
| F3 | **Stage label is wrong.** All 557 rows in `ipo_features.csv` are `post_close` with `data_cutoff` = listing date − 1 day, and 451 contain the final GMP. By the project's own stage table these are listing-eve snapshots. A real post-close cutoff needs issue close dates, which are not collected yet. | High | A3 |
| F4 | **The extra features add nothing.** Size, market and momentum add ≈ 0 over subscription alone (D 0.803 vs S 0.799). Adding subscription to GMP lowers AUC (B < A, interval excludes 0). The headline model C is not better than GMP alone on AUC, Brier or log-loss. Likely causes: too few training rows (about 70–360 per fold) for extra linear terms, or the wrong functional form. | High | D1, E8 |
| F5 | **The "downside recall" gap is a threshold artifact.** `class_weight="balanced"` plus a 0.5 cut makes GMP-only flag half of all IPOs. At equal flag rates recall is identical. Balanced-weight probabilities are uncalibrated. | High | B1, D1 |
| F6 | **The uncertain zone is confirmed numerically.** Inside GMP 0–10%, every feature set is near a coin flip (AUC 0.53–0.61, intervals reach 0.5). In the GMP ≤ 0 zone, subscription-only ranks backwards (AUC 0.34, n = 63; small sample, investigate). | Medium | D3, E2–E5 |
| F7 | **The label is fragile near zero.** 87 IPOs are within ±2% of issue price (86 after A1) and 37 are exactly 0.00% (36 after A1). More than a quarter of the test negatives are exact-flat listings. | Medium | A4, C1 |
| F8 | **Source and time are confounded.** The 104 tracker-only rows have no QIB/NII/retail subscription and 97% GMP coverage (Kaggle rows: 77%). 89 of them are 2026 listings, so "AUC by source" really means "2026 vs earlier", and category-subscription features are missing for most of 2026. | Medium | E4, G4 |
| F9 | **The v1 "pre-close" model is not pre-close.** `baseline_models.py` PRE features (Nifty, VIX, recent-IPO momentum) are measured the day before listing. It also uses a different row set and test years (2021–26, all rows) than v2 (451 rows with GMP, 2022–26), so "AUC ≈ 0.55" is not comparable to 0.80/0.85. On v2 rows, size + market + momentum gives 0.52. | Medium | E2, G2 |
| F10 | **Momentum look-ahead is immaterial today.** Momentum uses all IPOs listed before the row's listing date, which would include post-cutoff listings under a true post-close cutoff. Embargoing 3 or 7 days moves set D AUC from 0.803 to 0.801 / 0.800. It is also tie-order dependent: the file reproduces exactly only with a stable sort. | Low | A5 |
| F11 | **Hard-coded paths and missing dependency.** `build_features.py` and `baseline_models.py` use `E:/ipo-analyzer1/...` (`build_v2.py` uses a relative root). `requirements.txt` has no `yfinance` although two scripts import it. `xgboost` is listed but none of the three modelling scripts you sent use it. The directory listing shows traces of Python 3.12, 3.13 and 3.14 while the file targets 3.11/3.12. | Low | A6 |
| F12 | **Docs drift from code.** `modelling_decisions.md` describes folds starting 2018–2020 and a late-2024/2025 holdout; the scripts you sent use yearly folds from 2021 (v1) or 2022 (v2) through 2026, with no separate holdout. It lists Brier, PR-AUC, balanced accuracy and a "GMP > 0" baseline that none of those scripts computes. | Low | G2, B1 |
| F13 | **ID rule differs from the roadmap.** IDs follow listing year for all 557 rows; the roadmap says issue year. IDs must stay stable once assigned. | Low | G3 |
| F14 | **No version control in the listing.** There is no `.git` folder, and `.env` sits in the project root. | Medium | F1 |

### Corrections to my first reply

- **Selection bias** is mostly not borne out: hyperparameters are fixed and every feature-set × model result is reported. The remaining risk is choosing C as "headline" after seeing the test years (B6).
- **402 vs 379 test rows:** resolved. All four v2 feature sets use the same 451 rows; the 23-row gap is test-year rows with no GMP.
- **"Model ties GMP":** too generous. B is slightly but reliably worse, and C is indistinguishable-to-worse (F4).
- **Momentum leak:** real in principle, immaterial today (F10).

---

## 3. A — Data integrity (do first)

- [ ] **A1 · P0 · S — Remove the two REIT-type rows.** Drop `INMAIN-2025-0034` and `INMAIN-2026-0020` from registry, outcomes, features, sources and `model_base_v2`. Add review rules: issue price > ₹10,000, and names containing REIT / InvIT / Trust / PropShare. *Done when:* 555 rows, validators report 0 errors, rules appear in `clean_kaggle.py` and `validators.py`. Expected shifts: positive rate 70.2% → 70.45%, exact-flat 37 → 36, ±2% band 87 → 86.
- [ ] **A2 · P0 · S — Fix the GMP join collision.** Add a name or issue-size tolerance to the join key, assert key uniqueness in both tables, and report matched pairs where issue size or total subscription disagree between Kaggle and tracker. Until fixed, set Indiqube's GMP to missing. *Done when:* zero duplicate keys and the mismatch report is reviewed.
- [ ] **A3 · P0 · S — Relabel the stage.** Add `listing_eve` to the schema and validators and relabel the 557 rows (or write two snapshots per IPO once close dates exist). Validator rule: GMP may appear only in `listing_eve` rows. *Done when:* the validator rejects a `post_close` row that contains GMP.
- [ ] **A4 · P1 · M — Verify labels near the boundary.** Check the ≈ 86 IPOs within ±2% against NSE and BSE bhavcopy opens (yfinance `.NS` / `.BO` as a cross-check). Make NSE the primary open; store both opens and a `label_conflict` flag; update `verification_status`. *Done when:* every IPO within ±2% is checked and conflicts are listed.
- [ ] **A5 · P1 · S — Make sorts deterministic.** Use `sort_values([...], kind="stable")` with a tie-breaker in all build scripts; compute momentum from IPOs listed before each row's `data_cutoff`. *Done when:* two runs give identical files.
- [ ] **A6 · P1 · S — Clean the environment.** Add `yfinance` to `requirements.txt`, remove or use `xgboost`, replace `E:/` paths with a project-root path, pin one Python version. *Done when:* a fresh clone runs `pytest` and the build scripts.
- [ ] **A7 · P2 · M — Add tests for the new rules.** Key uniqueness, price sanity, stage/GMP rule, momentum cutoff. Re-run the full suite on the loaded data. *Done when:* the tests are in `tests/` and passing.

## 4. B — Evaluation framework (build once, reuse)

- [ ] **B1 · P0 · M — One evaluation harness** in `src/evaluation/`. Same rows for every model; AUC, PR-AUC, Brier, log-loss, calibration error and reliability curve, balanced accuracy; recall at fixed flag rates (20 / 35 / 50%) and precision at fixed recall; results by year and by GMP zone (≤ 0, 0–10, > 10, ≤ 10 combined). *Done when:* the scoreboard in section 1 is regenerated by one command.
- [ ] **B2 · P0 · S — Paired bootstrap** for ΔAUC and ΔBrier against GMP-only, including a by-year block version. *Done when:* every comparison prints an interval.
- [ ] **B3 · P0 · S — Fixed baselines in every report:** majority, prior-only, GMP logistic (A), GMP ≤ 5 / ≤ 10 rules, subscription-only (S).
- [ ] **B4 · P1 · S — Label variants in every report:** strict (> 0), clear cases only (|gain| > 2%), and the 3-class label from C1.
- [ ] **B5 · P1 · M — Quarterly rolling-origin folds** instead of yearly; compare expanding windows with recency-weighted training.
- [ ] **B6 · P1 · S — Pre-register the headline** model and metric in this file before each experiment round; use nested validation once tuning begins.
- [ ] **B7 · P2 · M — Decision metric.** Policy "skip when P(non-positive) > p": losses avoided vs gains missed per 100 IPOs, with and without allotment odds.

## 5. C — Target and label

- [ ] **C1 · P1 · S — Define a 3-class label** {≤ −2%, −2% to +2%, > +2%} (confirm the band against trading costs) and keep the binary label as a derived view. *Done when:* the definition is in `modelling_decisions.md` and the build script writes both.
- [ ] **C2 · P2 · S — Document flat-listing treatment** and decide whether listing-day close becomes a secondary target later.

## 6. D — Models (ordered by value)

- [ ] **D1 · P0 · M — Re-specify the logistic model.** Unweighted logistic plus calibration inside the folds (Venn-ABERS or isotonic); tune the regularisation strength with inner CV; try splines or monotone terms on GMP and log-subscription and a GMP × subscription interaction. *Done when:* it beats A on Brier and log-loss with a paired interval that excludes 0, or the file records that it could not.
- [ ] **D2 · P1 · M — Monotone GAM / EBM** (InterpretML or pyGAM) on GMP and log-subscription, adding new features as they arrive.
- [ ] **D3 · P1 · M — Ordinal / 3-class model** (statsmodels `OrderedModel`) giving P(loss), P(flat), P(gain) and an expected gain; derive P(gain > 0) from it. Evaluate mainly inside the GMP ≤ 10 zone.
- [ ] **D4 · P1 · M — Residual-on-GMP model.** Shrunk model of (actual − GMP) with GMP as an offset; test paired against the zero-residual baseline (MAE 8.25).
- [ ] **D5 · P1 · M — Quantile regression + conformal intervals** (LightGBM or sklearn quantile boosting, with MAPIE or crepes) on a signed-log target. Metrics: pinball loss, 80% interval coverage, MAE vs GMP-direct.
- [ ] **D6 · P2 · M — Monotone-constrained gradient boosting** (XGBoost, HistGradientBoosting or CatBoost) as a challenger, only after new features exist.
- [ ] **D7 · P2 · S — TabPFN v2 challenger** (torch already installed; check licence terms for your use).
- [ ] **D8 · P3 · L — Bayesian hierarchical logistic** with year and sector effects (PyMC or bambi); stacking.
- [ ] **D9 · P2 · M — Zone specialist.** A model trained and scored only on GMP ≤ 10%, after new features.

## 7. E — Features and data collection

- [ ] **E1 · P0 · S — Start prospective GMP logging.** A daily timestamped capture of GMP for open and upcoming IPOs (Windows Task Scheduler or a GitHub Actions cron), written to the `ipo_gmp_history` schema. This is the only way to get true point-in-time GMP. *Done when:* two weeks of timestamped rows exist.
- [ ] **E2 · P1 · L — Issue open/close dates** (Chittorgarh detail pages or exchange data), enabling real `pre_close` and `post_close` snapshots. *Done when:* ≥ 90% of rows have both dates.
- [ ] **E3 · P1 · L — Anchor book, price band, P/E vs peers, OFS %, sector** (Chittorgarh, exchange circulars, RHP).
- [ ] **E4 · P1 · M — Day-wise subscription** (day 1 / 2 / 3, late QIB surge) and category subscription for tracker-only rows.
- [ ] **E5 · P1 · M — Supply and regime features:** number and size of IPOs in the same week and prior 30 days; Nifty smallcap return during the bidding window; a T+6 → T+3 listing-timeline flag (voluntary Sept 2023, mandatory Dec 2023; confirm dates).
- [ ] **E6 · P2 · M — Historical GMP time series** from dated Internet Archive snapshots (check terms and quality first).
- [ ] **E7 · P2 · L — RAG → structured features** (P/E, OFS %, revenue growth, promoter holding, litigation count), kept `unverified` until spot-checked.
- [ ] **E8 · P1 · S — Re-specify the headline feature set.** Size, Nifty, VIX and momentum currently add ≈ 0. Keep them out of the headline model until a test shows they help.

## 8. F — Tools and infrastructure · G — Documents

**F — Tools**

- [ ] **F1 · P0 · S — `git init`**, confirm `.env`, `.venv`, `data/` and caches are ignored, make a first commit.
- [ ] **F2 · P1 · S — DVC** for the data folders.
- [ ] **F3 · P1 · S — MLflow** (local file store) for experiment tracking.
- [ ] **F4 · P2 · S — Optuna**, only inside nested walk-forward.
- [ ] **F5 · P2 · S — SHAP** (trees) and EBM's built-in explanations.
- [ ] **F6 · P2 · S — Install** `statsmodels`, `mapie` or `crepes`, `venn-abers`, `lightgbm`, `catboost` (none are in the venv today).
- [ ] **F7 · P2 · M — Move code** from `root/` and `models/` into `src/features`, `src/models`, `src/evaluation` (empty stubs now) with tests; add ruff and pre-commit.
- [ ] **F8 · P3 · S — Dashboard:** show probability, interval and a "GMP ≤ 10% zone" warning once D1–D5 land.

**G — Documents**

- [ ] **G1 · P1 · S — Reconcile the two roadmap docs.** `IPOVision_Progress_and_Roadmap.md` (12 Nov) and `summary_of_phases.md` (14 Nov) disagree on phase numbering and Phase 3 status. Treat Phase 3 as "scope-reduced" with A4 (label verification) as its closing item.
- [ ] **G2 · P1 · S — Align `modelling_decisions.md` with the code** (fold years, holdout, metrics, baselines) or implement what it promises (B1).
- [ ] **G3 · P2 · S — Write down the ID rule** (listing year) in `data_dictionary.md`.
- [ ] **G4 · P1 · S — Regenerate the EDA** after A1 and A2 (counts, flat-listing numbers, the Indiqube example, the 63 false-comfort cases).
- [ ] **G5 · P3 · S — Fix the file reference.** Docs mention `root\eda_phase4.py`; the listing shows `eda_findings.py` and `eda_followup.py`.

---

## 9. Suggested order

| Step | Items | Outcome |
|---|---|---|
| 1 — Integrity and harness | A1–A3, A5, A6, F1, E1, B1–B3 | Clean data, one trusted scoreboard, GMP logging running |
| 2 — Re-baseline | D1, B4, C1, A4, G4 | A calibrated model that is honestly compared with GMP-only |
| 3 — Better targets and models | D2–D5, B5–B7 | 3-class probabilities, intervals, residual test |
| 4 — New information | E2–E5, then D6 / D7 / D9 | Features that can separate outcomes inside the GMP ≤ 10% zone |
| 5 — Scale up | E6–E7, F2–F4, F7, F8 | Reproducible pipeline and dashboard |

## 10. Proposed definition of success (adjust as you learn)

1. Calibrated P(non-positive) beats GMP-only logistic on Brier and log-loss with a paired interval that excludes 0 overall, **or** matches overall and is clearly better inside GMP ≤ 10%.
2. AUC inside GMP ≤ 10% reaches ≥ 0.75 (today 0.71 for A, 0.66 for C) **and** holds on ≥ 100 prospectively logged IPOs.
3. Calibration error ≤ 0.05, with a reliability curve in the report.
4. Magnitude: 80% intervals cover 75–85% of outcomes, and point MAE is no worse than GMP-direct (8.25) on the same rows.
5. **Fallback:** if 1–4 are not met, the product is "GMP plus a calibrated risk band", and the report says GMP is the benchmark.

## 11. Parked / not recommended

Deep networks or LSTMs · SMOTE or other resampling (70/30 is mild and it distorts probabilities) · embedding prospectus text straight into the model · AutoML leaderboard chasing · random-shuffle cross-validation.

## 12. Change log

| Date | Change | Scoreboard AUC A / C | Brier A / C |
|---|---|---|---|
| 15 Nov 2026 | Baseline recorded (tracker created) | 0.862 / 0.848 | 0.135 / 0.139 |
|  |  |  |  |
