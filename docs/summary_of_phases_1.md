# IPOVision — Summary of Phases

**Last updated:** 15 Nov 2026 · **Environment:** Python 3.12, `.venv`, Windows PowerShell · **Project root:** `E:\ipo-analyzer1`

> Keep this file current. After each milestone, update the status table (section 3), add anything new to the decision log (section 5) and the limitations list (section 6), and refresh "Next steps" (section 8).

---

## 1. What the project is

IPOVision predicts how an **Indian mainboard IPO will perform on listing day**, using only information that exists *before* the listing.

- **Target:** `listing_gain_pct = (listing_open_price − issue_price) / issue_price × 100`
- **Classification label:** `listing_positive = 1` if the gain is above 0, otherwise 0 (a gain of exactly 0 counts as non-positive).
- **Two tasks:** (1) will the IPO list above its issue price? (2) by roughly how much?
- **Scope:** mainboard IPOs only. SME-platform issues, REITs/InvITs and follow-on offers (FPOs) are excluded.
- **Later phases** add a prospectus (RHP/DRHP) question-answering engine, fundamental scoring, and a Streamlit dashboard.

### Why three prediction stages
What you know depends on *when* you ask the question. Mixing stages would leak the future into the model.

| Stage | When | Information available |
|---|---|---|
| Pre-close | Before the issue closes | Issue size, price, market conditions, recent IPO performance |
| Post-close | Evening of the last bidding day | + QIB / NII / retail / total subscription |
| Listing-eve | Day before listing | + final grey-market premium (GMP) |

The project's validation engine enforces this: a `pre_close` row may never contain subscription numbers.

---

## 2. How the pieces fit together

```
Kaggle IPO file (652 rows, 2010–May 2026)      InvestorGain GMP tracker (2020–Nov 2026)
            │                                              │
            └── clean: drop REITs/InvITs, FPOs, bad prices ┤
                       (633 kept)                          │
                                                           ▼
        merge GMP by (listing date + issue price) ── add 104 IPOs Kaggle lacks (tracker-only rows)
                                                           │
        features: size, subscription, GMP %, recent-IPO momentum, Nifty / India VIX
                                                           │
                       model_base_v2.csv (557 IPOs, 2017–2026)
                                                           │
        staging → Phase 2 validators → data/processed/ (registry, features, outcomes, feature_sources)
                                                           │
                         walk-forward models → reports → (dashboard)
```

---

## 3. Phase tracker

| Phase | Name | Status | Evidence |
|:-:|---|:-:|---|
| 0 | Setup & environment | ✅ Done | `config/`, `requirements.txt`, `tests/test_environment.py` |
| 1 | Source testing & scraper prototypes | ✅ Done | `src/collection/*`, `tests/test_phase1.py`, source reports |
| 2 | Dataset schemas & validation engine | ✅ Done | `src/cleaning/*`, `tests/test_phase2.py`, `docs/data_dictionary.md` (38 tests at completion) |
| 3 | Historical data collection & loading | ✅ Done (scope-reduced) | 557 IPOs written to `data/processed/`, all validators 0 errors, 8 deliberate-corruption tests caught |
| 4 | Exploratory data analysis | ✅ Done | `root/eda_findings.py`, `root/eda_followup.py`, `root/check_zero_gain.py` → `reports/figures/` (8 figures), `reports/eda/`; written up in `docs/eda_summary.md` |
| 5 | RHP/DRHP RAG engine | ⬜ Not started | `src/rag` is a stub |
| 6 | Fundamental analysis | ⬜ Not started | `src/fundamental_analysis` is a stub |
| 7 | Baseline ML | ✅ Done early (v2) | `reports/evaluation/baseline_v2_gmp.txt` |
| 8 | Advanced ML & validation | ⬜ Not started | Planned: tuned boosting, SHAP, residual-on-GMP model |
| 9 | Streamlit dashboard | ⬜ Not started | `app/` is empty |
| 10 | Testing, audit, polish | 🔄 Partly | 44 tests passing on the loaded data (15 Nov); remaining: end-to-end audit, documentation review |

### What "Phase 3 done" means (and what was deferred)

| Included | Deferred (documented, not forgotten) |
|---|---|
| 557 IPOs, 2017–Nov 2026 (registry, outcomes, `post_close` features) | `pre_close` snapshots (need issue open/close dates) |
| Subscription (total for all rows; QIB/NII/retail for Kaggle rows), size, final GMP, issue and listing-open price | Financials, P/E, P/B, price band, fresh/OFS split, anchor investors |
| 3,481 provenance rows, all marked `unverified` | `ipo_gmp_history` (the tracker gives one untimestamped GMP per IPO) |

Intentionally blank fields in `ipo_features.csv` (not missing by accident): exchange, issue open/close dates, price band, fresh issue/OFS, all financials and valuation ratios, `gmp_change`, `gmp_recorded_at`.

---

## 4. Results so far

**Data loaded:** 557 IPOs · 70.2% list positive · GMP available for 451 (final value, from Sep 2020).

**Models** (walk-forward: train on all earlier years, test on the next year; test years 2022–2026, 379 rows; the "always positive" baseline is 73.6% accurate):

| Stage / feature set | Best AUC | Downside recall | Note |
|---|---:|---:|---|
| Pre-close (size, market, momentum) | ~0.55 | weak | Near coin-flip (run on the earlier 633-row base) |
| Post-close (+ subscription), set D | 0.80 | 0.70 | Logistic regression |
| Listing-eve (+ GMP), set C | 0.85 | 0.84 | Logistic regression; headline model |
| GMP alone | 0.86 | 0.91 (logreg) | Highest single feature |

**Size of the gain (MAE, percentage points):** predict-the-median 19.4 · ridge model 8.8 · **GMP used directly 8.25.** GMP beats the model for magnitude. The classifier's value is estimating the *probability of a non-positive listing*, which GMP alone does badly (rule "GMP > 0 ⇒ positive" catches only 45% of non-gainers).

**Robustness:** AUC 0.846 on Kaggle rows and 0.868 on tracker-only rows, so mixing the two sources did not hurt.

**EDA highlights (details in `docs/eda_summary.md`):**
- Positive rate rises with subscription (about 34% below 3x, 91% at 30–100x, 99% above 100x) and with final GMP (26% at GMP ≤ 0, 89% at 10–30%, about 99–100% above 30%).
- The uncertain zone is GMP 0–10% (128 IPOs, 62% positive); subscription barely separates outcomes there.
- 63 of 374 IPOs with a positive GMP (16.8%) listed flat or lower, roughly 49 of them at GMP 0–10%.
- GMP vs actual gain: Spearman 0.874, MAE 9.2 points.
- 87 IPOs (15.6%) listed within ±2% of the issue price; 37 listed at exactly 0.00%, 21 of those in 2025–26.

---

## 5. Decision log

| Decision | Reason |
|---|---|
| Mainboard IPOs only | SME listings trade under different rules and behave differently |
| Kaggle file as the base, tracker as gap-filler | Already covered ~630 IPOs; scraping history one IPO at a time was too slow |
| Kaggle `List Price` = listing-day **opening** price | Checked by hand against exchange data; the target requires the open |
| Only the listing date is verified, not open/close dates | Nothing in the models depends on them |
| Modelling window 2017 onward | 2012–2014 have only 3–11 IPOs a year; different market regime |
| Missing GMP stays blank (`gmp_missing = 1`), never 0 | A zero would teach the model that "no data" means "no premium" |
| REITs, InvITs, FPOs excluded | Not operating-company IPOs; an FPO has no real listing gain |
| Staged `post_close` rows only, `data_cutoff` = day before listing | Source data has no issue dates; matches how GMP and subscription were measured |
| Walk-forward validation, no random shuffles | Prevents training on the future |
| Judge models on AUC, downside recall, F1 on the negative class, not accuracy | 70% of IPOs are positive; accuracy rewards always saying "positive" |
| Replaced the empty-template test with processed-store tests | The old test asserted Phase 2's empty state; the new tests guard headers, validators, IDs, leakage, target math and GMP-never-zero |
| Evaluate separately inside the GMP ≤ 10% zone and under clear-only labels | Headline AUC is dominated by easy extremes; 15.6% of IPOs sit within ±2%, where the label depends on which exchange's open is used |

---

## 6. Known limitations and risks

1. **Final GMP is a listing-eve value.** The tracker gives no timestamp, so GMP cannot feed a true pre-close model. In 2020 the last records were dated just before listing.
2. **GMP is unofficial** market sentiment and sources disagree. Treat it as an input, not ground truth.
3. **Tracker page cap:** each year page returns at most 100 rows. Jan–Feb 2025 and Jan–Mar 2026 listings have no GMP (about 20 rows).
4. **Label noise of roughly ±1–2 points** because the two sources can quote different exchanges' opening prices (NSE vs BSE). It matters for the 87 IPOs (15.6%) listing within ±2% of the issue price, 37 of them at exactly 0.00%; for 7 of those 37 the tracker quotes a different price than Kaggle.
5. **Provenance is `unverified`:** aggregator values, not checked against RHPs or exchange filings. Kaggle's source URL is not recorded yet.
6. **Small samples:** 379 test rows means AUC differences below about 0.03 are noise.
7. **Company names truncated** (`...`) in about 67 recent Kaggle rows. Joins use listing date + issue price.
8. **Market features are measured the trading day before listing**, which is later than the true issue-close cutoff. Fine for post-close/listing-eve models.
9. **Tests:** 44 passing (15 Nov 2026). The Phase 2 empty-template test was replaced by processed-store tests (headers, validators, ID integrity, no `pre_close` subscription, target math, GMP never zero, no synthetic fixture rows).
10. **Class imbalance:** ~70% positive.

---

## 7. Backlog (deferred work, in rough priority order)

1. Collect issue open/close dates → build real `pre_close` snapshots.
2. Anchor-investor data (rated highly in the IPO checklist; available the day before the issue opens).
3. Valuation (P/E at upper band) and OFS %.
4. Sector and sector-index sentiment.
5. Verify a random sample of 20 IPOs against exchange/RHP data; update `verification_status`.
6. Residual model: predict *actual gain − GMP* from subscription and market features.
7. Move scripts from `root/` into `src/` modules with tests; make the data-quality report's integrity section computed instead of fixed text.
8. Phase 5–6: RHP question answering and fundamental scoring.

---

## 8. Next steps

**Phase 8 groundwork (current):**
- Run `python root\zone_and_label_eval.py`: compares the model with GMP-only and subscription-only scores inside the GMP ≤ 10% zone, and under three label definitions (strict, drop price conflicts, clear-only |gain| > 2%).
- Verify the 7 flat listings where Kaggle and the tracker disagree on the listing price.
- Then pick the main experiment: a residual-on-GMP model, or a model focused on the uncertain zone (tuned boosting + SHAP).

**Then:** start the Phase 9 dashboard skeleton so the model is visible on real IPOs.

---

## 9. File map

| Purpose | Path |
|---|---|
| Raw Kaggle file | `data/raw/Initial_Public_Offering_(Updated).xlsx` |
| Cached GMP tracker pages | `data/raw/gmp/tracker_<year>.html` |
| Market data cache (Nifty, India VIX) | `data/raw/market_context.csv` |
| Cleaned Kaggle outputs | `data/interim/kaggle/` (`kaggle_clean_candidates.csv`, `kaggle_excluded.csv`, `model_base_v2.csv`) |
| Parsed GMP | `data/interim/gmp/` |
| Staging area | `data/interim/processed_staging/` |
| **Final datasets** | `data/processed/` (`ipo_registry`, `ipo_features`, `ipo_outcomes`, `ipo_feature_sources`; `ipo_gmp_history` empty) |
| Pre-write backup | `data/interim/processed_backup_20261114_204726/` |
| Data-quality report | `reports/data_quality/data_quality_report.md` |
| Baseline results | `reports/evaluation/baseline_v2_gmp.txt` |

| Script (`root/`) | Role |
|---|---|
| `clean_kaggle.py` | Exclusion rules and review queue |
| `parse_gmp_tracker.py`, `gmp_step.py`, `gmp_gaps.py` | Fetch, parse, merge and diagnose the GMP tracker |
| `build_features.py`, `build_v2.py` | Feature building; v2 adds tracker-only IPOs |
| `models/baseline_models.py` | First baseline (v1) |
| `load_processed_staging.py`, `check_staging.py` | Stage and test the processed tables |
| `write_processed.py` | Validated, atomic write to `data/processed/` |
| `eda_findings.py`, `eda_followup.py`, `check_zero_gain.py` | Phase 4 figures, follow-up analysis, zero-gain check |
| `zone_and_label_eval.py` | Phase 8 groundwork: zone and label-robustness evaluation |

### Resuming work

```powershell
cd E:\ipo-analyzer1
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ -q
python root\eda_findings.py
```
