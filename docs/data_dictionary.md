# IPOVision — Data Dictionary & Schema Specification

**Document Version:** 1.0.0  
**Target Market:** Indian Mainboard IPOs Only  
**Purpose:** Defines the exact schema, data types, units, missing-value policies, and prediction-stage applicability for all datasets maintained in IPOVision.

---

## 1. Core Data Principles

1. **Explicit Missingness:** Never replace missing values (e.g. absent GMP or missing subscription rates) with `0`. Always represent absent values as `NaN` or `None`.
2. **Stable Identifier (`ipo_id`):** Every IPO is assigned a deterministic identifier formatted as:  
   `YYYY-SYMBOL` (e.g. `2024-TATACHEV`, `2024-SWIGGY`, `2024-HYUNDAI`).
3. **Consistent Financial Units:**
   - Financial statement metrics (`revenue`, `profit_after_tax`, `ebitda`, `total_debt`, `issue_size_cr`, `fresh_issue_cr`, `ofs_cr`): Expressed strictly in **₹ Crore (INR Cr)**.
   - Per-share metrics (`issue_price`, `gmp`, `listing_open_price`, `listing_close_price`): Expressed strictly in **₹ (INR)** per equity share.
   - Valuation multiples (`pe_ratio`, `pb_ratio`): Expressed as pure numerical ratios (e.g. `42.5`).
   - Subscription metrics: Expressed as multiple of subscription (e.g. `15.4x`).
4. **Time-Cutoff Rigor (Leakage Prevention):**
   - Every observation in `ipo_features.csv` must record the exact `data_cutoff` timestamp.
   - Pre-close features cannot contain any post-close data (such as final subscriptions).
   - Neither stage can contain listing outcome data.

---

## 2. Table Specifications

### A. `ipo_features.csv` (Features Dataset)
Contains pre-listing data captured at a defined prediction cutoff.

| Field Name | Type | Unit / Format | Description | Missing Value Policy | Stage Applicability | Primary Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | string | `YYYY-SYMBOL` | Unique stable identifier for the IPO issue | Required (Primary Key) | Both | Master Registry |
| `company_name` | string | Text | Registered name of the issuing company | Required | Both | SEBI / Exchange |
| `symbol` | string | Text | NSE/BSE trading ticker symbol | Required if listed | Both | NSE / BSE |
| `issue_open_date` | date | `YYYY-MM-DD` | Date on which the issue opened for subscription | Required | Both | RHP / Exchange |
| `issue_close_date` | date | `YYYY-MM-DD` | Date on which the issue closed for subscription | Required | Both | RHP / Exchange |
| `issue_price` | float | ₹ (INR) | Final issue/offer price per equity share | Required | Both | Basis of Allotment / Exchange |
| `issue_size_cr` | float | ₹ Crore | Total issue size (Fresh + OFS) | Required | Both | RHP / Exchange |
| `fresh_issue_cr` | float | ₹ Crore | Portion raised via new equity shares | Nullable (`NaN` if 100% OFS) | Both | RHP / Prospectus |
| `ofs_cr` | float | ₹ Crore | Offer for Sale portion by existing shareholders | Nullable (`NaN` if 100% Fresh) | Both | RHP / Prospectus |
| `revenue` | float | ₹ Crore | Total revenue / revenue from operations for the latest reported FY | Nullable (`NaN` if unverified) | Both | RHP / Restated Financials |
| `profit_after_tax` | float | ₹ Crore | Restated Net Profit After Tax for latest reported FY | Nullable (`NaN` if loss-making/unverified) | Both | RHP / Restated Financials |
| `ebitda` | float | ₹ Crore | Operating earnings before interest, tax, dep. & amort. | Nullable (`NaN`) | Both | RHP / Restated Financials |
| `total_debt` | float | ₹ Crore | Total short-term + long-term borrowings | Nullable (`NaN` if zero/debt-free) | Both | RHP / Balance Sheet |
| `pe_ratio` | float | Ratio | P/E at upper price band based on diluted EPS | Nullable (`NaN` if negative earnings) | Both | RHP Valuation Section |
| `pb_ratio` | float | Ratio | P/B ratio based on NAV per share | Nullable (`NaN`) | Both | RHP Valuation Section |
| `peer_pe_ratio` | float | Ratio | Weighted or median P/E of listed peer group | Nullable (`NaN` if no listed peers) | Both | RHP Peer Comparison |
| `peer_pb_ratio` | float | Ratio | Median P/B of listed peer group | Nullable (`NaN` if no listed peers) | Both | RHP Peer Comparison |
| `qib_subscription` | float | Times (x) | Final Qualified Institutional Buyer subscription rate | `NaN` in Pre-close; Float in Post-close | **Post-close ONLY** | BSE/NSE Subscription Data |
| `nii_subscription` | float | Times (x) | Final Non-Institutional Investor subscription rate | `NaN` in Pre-close; Float in Post-close | **Post-close ONLY** | BSE/NSE Subscription Data |
| `retail_subscription`| float | Times (x) | Final Retail Individual Investor subscription rate | `NaN` in Pre-close; Float in Post-close | **Post-close ONLY** | BSE/NSE Subscription Data |
| `overall_subscription`| float | Times (x) | Final total subscription across all categories | `NaN` in Pre-close; Float in Post-close | **Post-close ONLY** | BSE/NSE Subscription Data |
| `gmp` | float | ₹ (INR) | Grey Market Premium observed at cutoff date | Nullable (`NaN` if unavailable) | Both | Reputable IPO Tracker |
| `gmp_change` | float | ₹ (INR) | 3-day change in GMP prior to cutoff | Nullable (`NaN` if no historical GMP) | Both | Derived from GMP History |
| `gmp_source` | string | Text | Sourcing portal / platform name | Nullable | Both | Collection Metadata |
| `gmp_recorded_at` | datetime | ISO 8601 | Observation timestamp of the selected GMP | Nullable | Both | Collection Metadata |
| `gmp_missing` | integer | `0` or `1` | Binary flag: `1` if GMP is absent, `0` if present | Required | Both | Derived Data Quality Indicator |
| `prediction_stage` | string | Enum | `pre_close` or `post_close` | Required | Both | Pipeline Identifier |
| `data_cutoff` | datetime | ISO 8601 | Snapshot timestamp when all row features were frozen | Required | Both | Leakage Guardrail |

---

### B. `ipo_outcomes.csv` (Listing Outcomes Dataset)
Stores verified ground-truth market listing outcomes. Used strictly for model training labels and performance evaluation.

| Field Name | Type | Unit / Format | Description | Missing Value Policy | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | string | `YYYY-SYMBOL` | Unique stable identifier for the IPO issue | Required (Foreign Key) | Matches `ipo_features.ipo_id` |
| `listing_date` | date | `YYYY-MM-DD` | Date of official exchange listing | Required | NSE / BSE Official Record |
| `issue_price` | float | ₹ (INR) | Final allotted issue price | Required | Reference for gain calculation |
| `listing_open_price` | float | ₹ (INR) | First traded price on listing morning (NSE primary) | Required | **Primary Ground Truth Target** |
| `listing_close_price`| float | ₹ (INR) | Closing settlement price on listing day | Nullable (Optional secondary) | Optional reference metric |
| `listing_gain_pct` | float | Percentage (%) | Percentage listing gain based on opening price | Required | Target for Regression: `((open - issue) / issue) * 100` |
| `listing_positive` | integer | `0` or `1` | Binary classification indicator | Required | Target for Classification: `1` if gain > 0 else `0` |

---

### C. `ipo_gmp_history.csv` (GMP Time Series Dataset)
Tracks the evolution of unofficial grey market premium quotes over the pre-listing window.

| Field Name | Type | Unit / Format | Description | Missing Value Policy | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | string | `YYYY-SYMBOL` | Stable identifier for the IPO issue | Required (Foreign Key) | Connects to `ipo_features` |
| `recorded_at` | datetime | ISO 8601 | Exact date and time the quote was posted/recorded | Required | Essential for point-in-time lookup |
| `gmp` | float | ₹ (INR) | Unofficial premium per share over issue price | Required | Raw observation |
| `estimated_listing_price` | float | ₹ (INR) | Quoted estimated listing price (`issue_price + gmp`) | Nullable | Calculated or reported |
| `source` | string | Text | Origin website or market tracker name | Required | For provenance & credibility auditing |
| `source_url` | string | URL | Direct link or archived URL of the record | Nullable | Audit trail |
| `notes` | string | Text | Special context (e.g. subject to Sauda, muted trading) | Nullable | Market qualitative notes |

---

## 3. Data Integrity & Validation Rules

- **Duplicate Check:** No duplicate `(ipo_id, prediction_stage)` tuples in `ipo_features.csv`.
- **Temporal Consistency:** `issue_open_date` $\le$ `issue_close_date` $\le$ `listing_date`.
- **Price Sanity:** `issue_price > 0`, `listing_open_price > 0`.
- **Issue Size Consistency:** If both present, `fresh_issue_cr + ofs_cr` $\approx$ `issue_size_cr`.
- **Subscription Positivity:** Subscriptions cannot be negative; `overall_subscription >= 0`.
