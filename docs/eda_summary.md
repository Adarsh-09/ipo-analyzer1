# IPOVision — EDA Summary (Phase 4)

**Date:** 15 Nov 2026 · **Data:** `data/processed/` (557 mainboard IPOs, listing dates 2017–Nov 2026) · **Figures:** `reports/figures/01…08` · **Raw tables:** `reports/eda/eda_findings.md`, `reports/eda/eda_followup.md`

Target: `listing_gain_pct = (listing_open_price − issue_price) / issue_price × 100`; an IPO is *positive* if the gain is above 0 (a flat listing counts as non-positive).

---

## 1. The dataset in one paragraph

557 IPOs, 70.2% listed positive. The median gain is 8.1% and the mean 19.5%; the 5th and 95th percentiles are −10.3% and +88.6%, the worst listing is −38.9% and the best +252.8%. Total subscription is available for all 557, and a final GMP for 451 (from Sep 2020; none for 2017–2019, and none for Jan–Feb 2025 and Jan–Mar 2026 because of the tracker's 100-row page cap).

## 2. The market regime changes year to year (figure 02)

| Year | IPOs | Positive rate | Median gain % | Mean gain % |
|---|---:|---:|---:|---:|
| 2017 | 36 | 67% | 6.4 | 22.6 |
| 2018 | 24 | 50% | 1.4 | 5.3 |
| 2019 | 16 | 62% | 6.5 | 15.5 |
| 2020 | 14 | 71% | 36.3 | 43.3 |
| 2021 | 65 | 69% | 11.3 | 30.7 |
| 2022 | 39 | 69% | 3.8 | 10.3 |
| 2023 | 59 | 78% | 16.4 | 26.5 |
| 2024 | 90 | 78% | 16.7 | 29.2 |
| 2025 | 105 | 69% | 5.4 | 9.3 |
| 2026 (to Nov) | 109 | 69% | 7.2 | 13.9 |

2023–24 were the strongest years; 2018, 2022 and 2025 were the weakest. Walk-forward validation therefore tests the models through both good and weak regimes. Nifty's 20-day return before listing has a modest rank correlation with the gain (0.20); India VIX has essentially none (−0.05).

## 3. Subscription and GMP both sort outcomes cleanly (figures 03, 05)

| Total subscription | IPOs | Positive rate | Median gain % |
|---|---:|---:|---:|
| under 1x | 20 | 40% | −1.8 |
| 1–3x | 119 | 33% | −1.0 |
| 3–10x | 88 | 61% | 3.0 |
| 10–30x | 73 | 66% | 7.9 |
| 30–100x | 158 | 91% | 20.5 |
| over 100x | 99 | 99% | 47.7 |

(The under-1x bucket has only 20 IPOs, so its 40% should not be read as a reversal.)

| Final GMP, % of issue price | IPOs | Positive rate | Median gain % |
|---|---:|---:|---:|
| 0 or below | 77 | 26% | −4.0 |
| 0–10% | 128 | 62% | 2.9 |
| 10–30% | 121 | 89% | 15.1 |
| 30–60% | 80 | 99% | 38.5 |
| above 60% | 45 | 100% | 88.5 |

Rank correlation with the gain: GMP 0.87, total subscription 0.74, QIB 0.69, NII 0.68, retail 0.59, recent-IPO momentum 0.14, issue size −0.09.

**Issue size** matters little, with one exception: ₹2,500–5,000 crore issues are the weakest bucket (46 IPOs, 57% positive, median gain 2.0%).

## 4. Where the uncertainty is (figure 08)

Once GMP exceeds about 10%, or subscription exceeds about 30x, the outcome is nearly settled. The open question lives in the **GMP 0–10% zone (128 IPOs)**, plus the 77 IPOs with GMP at or below 0 (26% positive).

Positive rate inside the GMP 0–10% zone, by subscription:

| Total subscription | IPOs | Positive rate |
|---|---:|---:|
| 1–3x | 39 | 51% |
| 3–10x | 36 | 75% |
| 10–30x | 31 | 48% |
| 30–100x | 18 | 78% |

There is no clean progression. The cells are small, and subscription is a weak, noisy signal in the zone where a second signal would be most useful. This is the most important finding for the modelling phase: the headline AUC (about 0.85) is dominated by the easy extremes.

## 5. How good is GMP? (figure 04)

- n = 451 · mean absolute error **9.2 points** · median error (actual − GMP) −1.1 points (GMP is slightly optimistic) · Spearman 0.874.
- Of the 374 IPOs with a positive GMP, **63 (16.8%) still listed flat or lower**. Their median GMP was 3.9%, against 21.9% for those that gained, and their median subscription 12.6x against 59.4x. By the bucket rates, roughly 49 of the 63 sat in the 0–10% zone.
- That false-comfort share by year: 11% (2020), 14% (2021), 23% (2022), 15% (2023), 16% (2024), 19% (2025), 17% (2026).
- Of the 77 IPOs with GMP at or below 0, 20 still listed positive.
- Big misses were mostly about size, not direction: Sigachi (GMP 138%, actual +253%), Vibhor Steel (93% → +179%), Easy Trip Planners (70% → +10%). One sign flip among the ten largest: Indiqube (GMP +36%, listed −7.7%).

## 6. Label noise and flat listings

- **87 IPOs (15.6%) listed within ±2% of the issue price.** Only 31% of them are positive, against 77% of the other 470.
- **37 IPOs (6.6%) listed at exactly 0.00%:** 3 in 2017, 1 each in 2018, 2019 and 2021, 2 in 2022, 5 in 2023, 3 in 2024, 10 in 2025 and 11 in 2026. That is 9.8% of 2025–26 IPOs against 4.7% of earlier ones. By source: 25 Kaggle rows, 12 tracker rows.
- Cross-check against the tracker's independent listing price: for **23 of the 37** the tracker agrees (a genuine flat listing), for **7** it quotes a different price, and for **7** there is no tracker price to compare. The conflicts include Udayshivakumar Infosolutions (Kaggle flat at ₹35, tracker ₹30) and Gem Aromatics (Kaggle ₹325, tracker ₹333.1, a +2.5% difference consistent with NSE vs BSE opens).
- The other 50 listings within ±2% (non-zero) are 54% positive.

Because a flat listing counts as non-positive, an IPO that opens at +0.5% on one exchange and −0.5% on the other can flip class. The model's score on these cases is partly a test of which exchange the source used.

## 7. Cases that do not fit

- **Heavily subscribed (≥30x) yet flat or lower: 15 IPOs.** Seven are exactly 0.00%. Eight had small negative gains (−1.2% to −3.7%) except two clear losers: Shree Ram Twistex (43.7x, −32.7%) and Amagi Media Labs (30.2x, −12.2%), both with no GMP on file, and Skyways Air (71x, −10.1%).
- **Weakly subscribed (<3x) yet gained 20%+: only 2 IPOs** (Antony Waste Handling, +36.5%; PhysicsWallah, +31.3%).
- **Ten worst listings** were almost all weakly subscribed with a GMP at or below zero (Om Freight Forwarders −38.9%, Waterways Leisure Tourism −38.1%, Glottis −31.8%, Annu Projects −27.3%).

## 8. What this means for modelling

1. **Evaluate inside the uncertain zone.** Report accuracy-type metrics separately for GMP ≤ 10% and GMP > 10%, and compare the model with GMP-only and subscription-only scores in each. Overall AUC will look good regardless.
2. **Treat the label as noisy near zero.** Run the evaluation under the strict label, a label that drops the price-conflict rows, and a label that keeps only clear cases (|gain| > 2%). If conclusions flip, the label definition is the finding.
3. **GMP is a strong point forecast** (MAE 9.2 points). The model's added value is the probability of a non-positive listing, and a residual model (actual − GMP) is the natural next experiment.
4. **Report GMP-based models as listing-eve models.** The final GMP is quoted just before listing; the pre-close stage has almost no usable signal (AUC about 0.55).

## 9. Limitations of this analysis

- Fewer than 150 IPOs in the key uncertain cells, so percentages move by several points on small changes.
- GMP is unofficial and untimestamped; coverage starts in Sep 2020.
- Two sources mix NSE/BSE opening prices; provenance values are marked `unverified`.
- No financial, valuation or anchor-investor features yet, so the analysis cannot say whether those would help inside the uncertain zone.
- Some company names are truncated in the source file; joins use listing date and issue price.
