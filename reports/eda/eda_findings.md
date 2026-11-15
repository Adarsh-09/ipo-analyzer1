# IPOVision - EDA findings (auto-generated from data/processed)

- IPOs: **557** (2017-2026); positive listings **70.2%**
- Gain: median 8.1%, mean 19.5%, 5th pct -10.3%, 95th pct 88.6%, min -38.9%, max 252.8%
- IPOs within +/-2% of the issue price (exposed to NSE/BSE open-price label noise): 15.6%
- GMP present for 451 IPOs; total subscription for 557

## By year
| year | ipos | positive_rate | median_gain | mean_gain |
|---|---|---|---|---|
| 2017.00 | 36.00 | 0.67 | 6.38 | 22.63 |
| 2018.00 | 24.00 | 0.50 | 1.35 | 5.26 |
| 2019.00 | 16.00 | 0.62 | 6.51 | 15.49 |
| 2020.00 | 14.00 | 0.71 | 36.28 | 43.31 |
| 2021.00 | 65.00 | 0.69 | 11.28 | 30.72 |
| 2022.00 | 39.00 | 0.69 | 3.75 | 10.25 |
| 2023.00 | 59.00 | 0.78 | 16.43 | 26.47 |
| 2024.00 | 90.00 | 0.78 | 16.68 | 29.20 |
| 2025.00 | 105.00 | 0.69 | 5.36 | 9.27 |
| 2026.00 | 109.00 | 0.69 | 7.22 | 13.91 |

## By total subscription
| sub_bucket | ipos | positive_rate | median_gain | mean_gain |
|---|---|---|---|---|
| <1x | 20 | 0.40 | -1.82 | -0.54 |
| 1-3x | 119 | 0.33 | -1.03 | -2.57 |
| 3-10x | 88 | 0.61 | 3.01 | 2.42 |
| 10-30x | 73 | 0.66 | 7.89 | 11.51 |
| 30-100x | 158 | 0.91 | 20.51 | 27.68 |
| >100x | 99 | 0.99 | 47.69 | 58.18 |

## By final GMP % of issue price
| gmp_bucket | ipos | positive_rate | median_gain | mean_gain |
|---|---|---|---|---|
| <=0 | 77 | 0.26 | -3.95 | -5.40 |
| 0-10% | 128 | 0.62 | 2.94 | 3.05 |
| 10-30% | 121 | 0.89 | 15.13 | 16.05 |
| 30-60% | 80 | 0.99 | 38.53 | 40.74 |
| >60% | 45 | 1.00 | 88.50 | 93.25 |

## By issue size (crore)
| size_bucket | ipos | positive_rate | median_gain | mean_gain |
|---|---|---|---|---|
| <250 | 89 | 0.75 | 11.90 | 24.34 |
| 250-500 | 115 | 0.68 | 9.40 | 19.84 |
| 500-1k | 161 | 0.70 | 10.16 | 21.28 |
| 1k-2.5k | 112 | 0.75 | 7.11 | 16.34 |
| 2.5k-5k | 46 | 0.57 | 2.00 | 15.28 |
| >5k | 34 | 0.68 | 4.34 | 13.65 |

## GMP accuracy
- n=451 | MAE 9.16 pts | median residual (actual minus GMP) -1.09 | Spearman 0.874
- GMP > 0 in 374 IPOs; 63 of them (16.8%) still listed flat or lower
- GMP <= 0 in 77 IPOs; 20 of them listed positive

## Spearman correlation with listing gain
| feature | spearman |
|---|---|
| gmp_pct | 0.87 |
| overall_subscription | 0.74 |
| qib_subscription | 0.69 |
| nii_subscription | 0.68 |
| retail_subscription | 0.59 |
| nifty_ret_20d | 0.20 |
| nifty_ret_5d | 0.17 |
| recent_gain_mean10 | 0.14 |
| vix_level | -0.05 |
| issue_size_cr | -0.09 |

## 10 worst listings
| date | company_name | issue_price | listing_gain_pct | overall_subscription | gmp_pct |
|---|---|---|---|---|---|
| 2025-10-08 | Om Freight Forward... | 135.00 | -38.89 | 3.87 | -2.22 |
| 2026-07-01 | Waterways Leisure Tourism | 808.00 | -38.12 | 1.53 | -6.31 |
| 2026-03-02 | Shree Ram Twistex ... | 104.00 | -32.69 | 43.66 | nan |
| 2025-10-07 | Glottis Ltd | 129.00 | -31.78 | 2.05 | 0.00 |
| 2026-09-02 | Annu Projects | 99.00 | -27.27 | 2.93 | -7.07 |
| 2018-04-02 | Dharan Infra EPC Ltd | 180.00 | -24.44 | 2.54 | nan |
| 2017-03-31 | CL Educate Ltd | 502.00 | -20.72 | 1.90 | nan |
| 2021-12-20 | Shriram Properties Limited | 118.00 | -20.34 | 4.60 | -8.47 |
| 2025-10-01 | BMW Ventures Ltd | 99.00 | -19.19 | 1.50 | 0.00 |
| 2021-08-23 | Nuvoco Vistas Corporation Limited | 570.00 | -17.37 | 1.71 | -2.11 |

## 10 biggest GMP misses (actual gain minus GMP %)
| date | company_name | issue_price | listing_gain_pct | overall_subscription | gmp_pct | resid |
|---|---|---|---|---|---|---|
| 2021-11-15 | Sigachi Industries Limited | 163.00 | 252.76 | 101.91 | 138.04 | 114.72 |
| 2024-02-20 | Vibhor Steel Tubes Limited | 151.00 | 178.81 | 298.86 | 92.72 | 86.09 |
| 2024-03-07 | Mukka Proteins Ltd  | 28.00 | 57.14 | 136.99 | 125.00 | -67.86 |
| 2021-03-19 | Easy Trip Planners Limited | 187.00 | 10.16 | 159.33 | 69.52 | -59.36 |
| 2024-08-13 | Unicommerce eSolutions Limited | 108.00 | 112.96 | 168.39 | 63.89 | 49.07 |
| 2021-10-01 | Paras Defence and Space Technologies Limited | 175.00 | 171.43 | 304.26 | 125.71 | 45.71 |
| 2023-11-30 | Tata Technologies Limited | 500.00 | 139.99 | 69.43 | 95.00 | 44.99 |
| 2025-07-30 | Indiqube Spaces Limited | 237.00 | -7.72 | 12.41 | 35.86 | -43.59 |
| 2021-02-25 | Nureca Limited | 400.00 | 58.74 | 39.93 | 17.50 | 41.24 |
| 2024-12-27 | Mamata Machinery Limited | 243.00 | 146.91 | 194.95 | 107.00 | 39.92 |