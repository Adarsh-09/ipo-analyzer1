# IPOVision — Machine Learning Decisions & Methodology

**Document Version:** 1.0.0  
**Context:** Indian Mainboard IPO Listing Performance Prediction

---

## 1. Problem Formulation

IPOVision models the listing performance of Indian Mainboard IPOs through two distinct tasks:

1. **Classification Task:** Predict whether an IPO will open at a premium relative to its issue price:
   $$ \text{Target: } \text{listing\_positive} = \begin{cases} 1, & \text{if } \text{listing\_gain\_pct} > 0 \\ 0, & \text{if } \text{listing\_gain\_pct} \le 0 \end{cases} $$
2. **Regression Task:** Predict the expected percentage listing gain or loss:
   $$ \text{Target: } \text{listing\_gain\_pct} = \frac{\text{listing\_open\_price} - \text{issue\_price}}{\text{issue\_price}} \times 100 $$

### Primary Outcome Definition: Listing Open Price
- **Rationale:** The first traded price at the end of the pre-opening session on listing day (typically 9:45 AM - 10:00 AM IST on NSE/BSE) captures pure uninfluenced listing discovery.
- Using closing prices introduces intraday market volatility, broad market index swings, and institutional churn that are disconnected from the primary issuance characteristics.

---

## 2. Preventing Look-Ahead Data Leakage

Data leakage is the most critical failure mode in financial machine learning. IPOVision establishes strict architectural barriers:

```
+-------------------------------------------------------------------------+
|                              CHRONOLOGY                                 |
|                                                                         |
| Offer Document Filings ---> Subscription Period ---> Cutoff ---> Listing |
|                                                      |                  |
| [ PRE-CLOSE WINDOW ]                                 |                  |
| - Issue Details, Financials, Valuations, Early GMP   |                  |
|                                                      |                  |
| [ POST-CLOSE WINDOW ]                                |                  |
| - Pre-close Features + Final Subscription + Late GMP |                  |
|                                                      v                  |
|                                            [ STRICT CUTOFF ]            |
|                                                      |                  |
| [ STRICTLY FORBIDDEN FROM ALL INPUTS ]               v                  |
| - Listing Open Price, Close Price, Listing Gain                         |
+-------------------------------------------------------------------------+
```

### Pre-Close vs Post-Close Feature Isolation
- **Stage A (Pre-Close):** Evaluated while the subscription window is still open. 
  - *Strict Rule:* Zero access to final QIB, NII, Retail, or Total subscription numbers.
- **Stage B (Post-Close):** Evaluated after the subscription closes, when official exchange bidding tallies and final pre-allotment GMP are locked.
  - *Strict Rule:* Subscription features are included, but absolutely no listing morning data is accessible.

---

## 3. Validation Strategy: Chronological Walk-Forward

### Why Standard Random K-Fold Cross-Validation is Flawed
In financial markets, macroeconomic sentiment, interest rate cycles, and liquidity regimes are strongly auto-correlated. Random splitting (e.g. shuffling 2021 and 2024 IPOs into training and test folds indiscriminately) allows models to memorize market conditions from the future to predict past outcomes—leading to overly optimistic backtest results that fail in live deployment.

### Chronological Walk-Forward Scheme
We implement an expanding-window chronological cross-validation strategy:

```
Split 1: Train [2018 - 2020]  ---> Test [2021]
Split 2: Train [2018 - 2021]  ---> Test [2022]
Split 3: Train [2018 - 2022]  ---> Test [2023]
Split 4: Train [2018 - 2023]  ---> Test [2024]
Holdout: Final Test Evaluation on most recent vintage (e.g., late 2024 - 2025)
```

- Preprocessing transformations (imputation, standard scaling, target encoding) are **fitted exclusively on the training folds** and applied forward without peeking at the test folds.

---

## 4. Benchmark Baselines

No machine learning model will be considered useful unless it systematically outperforms simple, deterministic benchmarks:

1. **Majority Class Classifier:** Predicts that every IPO will list positively. (In strong bull markets, 70-80% of IPOs list positively, making raw accuracy misleading).
2. **GMP Implied Baseline:**
   - Listing Gain Estimate: $\text{GMP\_pct} = \frac{\text{gmp}}{\text{issue\_price}} \times 100$
   - Classification: Positive if $\text{GMP} > 0$.
3. **Historical Median Gain Regressor:** Predicts the median listing gain observed in the training window.

---

## 5. Evaluation Metrics

Because retail investors face asymmetric risk (losing capital on unexpected listing discounts is more damaging than missing moderate gains), metric selection emphasizes downside recall:

- **Classification:**
  - **Balanced Accuracy:** Average recall on positive and negative classes.
  - **Negative Class Recall (Discount Recall):** The fraction of discount listings correctly flagged.
  - **Brier Score / Calibration:** Measures whether a predicted probability of 80% genuinely corresponds to an 80% real-world win rate.
  - **ROC-AUC & PR-AUC:** Separation power across probability thresholds.
- **Regression:**
  - **Mean Absolute Error (MAE):** Average error in percentage points.
  - **Root Mean Squared Error (RMSE):** Penalizes extreme mispredictions.
  - **Directional Accuracy:** Percentage of cases where predicted sign matches actual sign.
