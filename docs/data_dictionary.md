# IPOVision — Comprehensive Data Dictionary & Schema Specification

**Document Version:** 2.0.0  
**Phase:** 2 (Dataset Construction)  
**Target Market:** Indian Mainboard IPOs Only (NSE/BSE)  
**Identifier Convention:** `INMAIN-YYYY-NNNN`  

---

## 1. Architectural Foundations

### 1.1 Multi-Stage Prediction Design
To prevent future look-ahead data leakage in predictive modeling, IPOVision physically separates data into two distinct stages:
1. **Pre-Close (`pre_close`):** Captured strictly *before* the issue subscription period closes. All subscription bidding figures (`qib_subscription`, `nii_subscription`, `retail_subscription`, `overall_subscription`) **MUST BE NaN / None**. Any presence of subscription figures in this stage is treated as a fatal leakage error.
2. **Post-Close (`post_close`):** Captured *after* subscription closes but *before* listing morning. Final subscription multiples are permitted and populated.

### 1.2 Ground Truth Outcomes
Listing outcome targets (`listing_open_price`, `listing_gain_pct`, `listing_positive`) are stored in an independent dataset (`ipo_outcomes.csv`) and must **never** be used as feature inputs for predictions.

### 1.3 Missing Data Policy
1. **Grey Market Premium (GMP):** Unofficial market quote. Missing GMP is **never replaced with zero (0.0)**. It is stored as `NaN`, accompanied by `gmp_missing = 1`.
2. **Loss-Making Fundamentals:** Negative PAT, negative EBITDA, or negative operating cash flow are legitimate business values (e.g. tech startups) and are never rejected as invalid.
3. **Financial Periods:** All financial statement metrics (`revenue`, `profit_after_tax`, `ebitda`) are bound to explicit period descriptors (`revenue_period`, `pat_period`, `ebitda_period`), e.g., `FY2024`, `FY2023`, `9MFY24`. Annual and interim figures are never mixed without metadata.

---

## 2. Table Specifications

### A. `ipo_features.csv` (Primary Feature Store)
Contains IPO issue characteristics, company fundamentals, valuation multiples, subscription statistics, and sentiment metrics frozen at a specific `data_cutoff`.

| Field Name | Description | Data Type | Unit | Expected Format | Primary Source | Required? | Missing Handling | Stage Eligibility | Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | Canonical IPO identifier | String | None | `INMAIN-YYYY-NNNN` | Master Registry | Required | Fatal error if missing | Both | Must match regex `^INMAIN-\d{4}-\d{4}$` |
| `company_name` | Full legal registered name | String | Text | E.g. "Swiggy Limited" | SEBI / Exchange | Required | Fatal error if missing | Both | Min length 2 characters |
| `symbol` | Exchange trading ticker symbol | String | Text | E.g. "SWIGGY" | NSE / BSE | Optional | Empty string / NaN if unassigned | Both | Uppercase alphanumeric |
| `exchange` | Primary listing exchange | String | Code | "NSE", "BSE", "NSE,BSE" | SEBI / Exchange | Optional | Defaults to "NSE,BSE" | Both | Valid exchange code |
| `issue_open_date` | Subscription opening date | Date | Date | `YYYY-MM-DD` | RHP / Exchange | Required | Fatal error if missing | Both | Valid date, <= `issue_close_date` |
| `issue_close_date` | Subscription closing date | Date | Date | `YYYY-MM-DD` | RHP / Exchange | Required | Fatal error if missing | Both | Valid date, >= `issue_open_date` |
| `issue_price` | Final allotment / upper band price | Float | ₹ / share | Positive decimal | RHP / Allotment | Required | Fatal error if missing | Both | Must be > 0.0 |
| `price_band_low` | Lower boundary of price band | Float | ₹ / share | Positive decimal | RHP / Red Herring | Optional | NaN if fixed price issue | Both | Must be > 0.0, <= `price_band_high` |
| `price_band_high` | Upper boundary of price band | Float | ₹ / share | Positive decimal | RHP / Red Herring | Optional | NaN if fixed price issue | Both | Must be >= `price_band_low` |
| `issue_size_cr` | Total capital raised | Float | ₹ Crore | Positive decimal | RHP / Allotment | Required | Fatal error if missing | Both | Must be > 0.0 (Mainboard >= 50 Cr typical) |
| `fresh_issue_cr` | Fresh capital raised by company | Float | ₹ Crore | Non-negative decimal | RHP / Prospectus | Optional | NaN if 100% OFS | Both | Must be >= 0.0 |
| `ofs_cr` | Offer for Sale by existing holders | Float | ₹ Crore | Non-negative decimal | RHP / Prospectus | Optional | NaN if 100% Fresh | Both | Must be >= 0.0 |
| `listing_date` | Actual date of market listing | Date | Date | `YYYY-MM-DD` | Exchange Record | Optional | NaN if pre-listing snapshot | Both | Valid date, >= `issue_close_date` |
| `revenue` | Total revenue / revenue from operations | Float | ₹ Crore | Decimal | RHP Restated P&L | Optional | NaN if unextracted | Both | Can be 0 or positive |
| `revenue_period` | Reporting period for revenue | String | Code | E.g. "FY2024", "FY2023" | RHP Restated P&L | Optional | NaN if revenue missing | Both | Must specify fiscal period |
| `profit_after_tax` | Net profit / (loss) after tax | Float | ₹ Crore | Decimal | RHP Restated P&L | Optional | NaN if unextracted | Both | Can be negative (loss) or positive |
| `pat_period` | Reporting period for PAT | String | Code | E.g. "FY2024", "FY2023" | RHP Restated P&L | Optional | NaN if PAT missing | Both | Must specify fiscal period |
| `ebitda` | Operating EBITDA | Float | ₹ Crore | Decimal | RHP Restated P&L | Optional | NaN if unextracted | Both | Can be negative or positive |
| `ebitda_period` | Reporting period for EBITDA | String | Code | E.g. "FY2024", "FY2023" | RHP Restated P&L | Optional | NaN if EBITDA missing | Both | Must specify fiscal period |
| `total_debt` | Short-term + long-term borrowings | Float | ₹ Crore | Non-negative decimal | RHP Balance Sheet | Optional | NaN if unextracted / 0 for debt-free | Both | Must be >= 0.0 (debt cannot be negative) |
| `net_worth` | Total equity shareholder funds | Float | ₹ Crore | Decimal | RHP Balance Sheet | Optional | NaN if unextracted | Both | Can be negative in severe capital erosion |
| `cash_flow_from_operations`| Net operating cash flows | Float | ₹ Crore | Decimal | RHP Cash Flow Stmt | Optional | NaN if unextracted | Both | Can be negative or positive |
| `eps` | Basic/Diluted EPS prior to issue | Float | ₹ / share | Decimal | RHP Restated | Optional | NaN if unextracted | Both | Can be negative for loss-making |
| `nav` | Net Asset Value per equity share | Float | ₹ / share | Decimal | RHP Restated | Optional | NaN if unextracted | Both | Can be negative |
| `pe_ratio` | Price to Earnings multiple at upper band | Float | Multiple | Positive decimal | RHP Valuation | Optional | NaN if negative earnings (loss) | Both | Must be > 0.0 if present |
| `pb_ratio` | Price to Book Value multiple | Float | Multiple | Positive decimal | RHP Valuation | Optional | NaN if negative net worth | Both | Must be > 0.0 if present |
| `peer_pe_ratio` | Median / weighted P/E of listed peers | Float | Multiple | Positive decimal | RHP Peer Section | Optional | NaN if no listed direct peers | Both | Must be > 0.0 if present |
| `peer_pb_ratio` | Median / weighted P/B of listed peers | Float | Multiple | Positive decimal | RHP Peer Section | Optional | NaN if no listed direct peers | Both | Must be > 0.0 if present |
| `qib_subscription` | Qualified Institutional Buyer multiple | Float | Times (x) | Non-negative decimal | InvestorGain / NSE | Optional | NaN in pre_close; Float in post_close | **Post-Close Only** | >= 0.0; MUST be NaN in pre_close |
| `nii_subscription` | Non-Institutional Investor multiple | Float | Times (x) | Non-negative decimal | InvestorGain / NSE | Optional | NaN in pre_close; Float in post_close | **Post-Close Only** | >= 0.0; MUST be NaN in pre_close |
| `retail_subscription` | Retail Individual Investor multiple | Float | Times (x) | Non-negative decimal | InvestorGain / NSE | Optional | NaN in pre_close; Float in post_close | **Post-Close Only** | >= 0.0; MUST be NaN in pre_close |
| `overall_subscription` | Total subscription across all pools | Float | Times (x) | Non-negative decimal | InvestorGain / NSE | Optional | NaN in pre_close; Float in post_close | **Post-Close Only** | >= 0.0; MUST be NaN in pre_close |
| `gmp` | Grey Market Premium per share | Float | ₹ / share | Decimal | Reputable Tracker | Optional | NaN if absent; NEVER zero-fill | Both | Can be negative, zero, or positive |
| `gmp_change` | 3-day change in quoted GMP | Float | ₹ / share | Decimal | Derived from GMP History | Optional | NaN if insufficient history | Both | Can be negative, zero, or positive |
| `gmp_source` | Platform reporting the quoted GMP | String | Text | E.g. "InvestorGain" | Platform metadata | Optional | NaN if GMP absent | Both | Valid string |
| `gmp_recorded_at` | Timestamp of GMP observation | DateTime | ISO 8601 | `YYYY-MM-DDTHH:MM:SS` | Platform metadata | Optional | NaN if GMP absent | Both | Must be <= `data_cutoff` |
| `gmp_missing` | Indicator if GMP quote is absent | Integer | Binary | `0` or `1` | Data quality audit | Required | Must be 1 if GMP NaN, 0 if present | Both | Must be 0 or 1 |
| `prediction_stage` | Prediction pipeline phase | String | Enum | `pre_close` or `post_close` | Pipeline metadata | Required | Fatal error if missing | Both | Must be 'pre_close' or 'post_close' |
| `data_cutoff` | Point-in-time timestamp of snapshot | DateTime | ISO 8601 | `YYYY-MM-DDTHH:MM:SS` | Leakage guardrail | Required | Fatal error if missing | Both | All row features must be <= cutoff |

---

### B. `ipo_outcomes.csv` (Ground Truth Listing Outcomes)
Stores actual verified market listing performance. Used strictly as supervised targets ($y$) for ML models.

| Field Name | Description | Data Type | Unit | Expected Format | Primary Source | Required? | Missing Handling | Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | Canonical IPO identifier | String | None | `INMAIN-YYYY-NNNN` | Master Registry | Required | Foreign key to `ipo_features` | Must match regex `^INMAIN-\d{4}-\d{4}$` |
| `listing_date` | Official date of exchange debut | Date | Date | `YYYY-MM-DD` | NSE / BSE Official | Required | Fatal error if missing | Valid date |
| `issue_price` | Final allotment price | Float | ₹ / share | Positive decimal | Basis of Allotment | Required | Fatal error if missing | Must be > 0.0 |
| `listing_open_price`| First trade price in pre-open session | Float | ₹ / share | Positive decimal | NSE Official Feed | Required | Fatal error if missing | **Primary Ground Truth Target**; Must be > 0.0 |
| `listing_close_price`| Final settlement price on listing day | Float | ₹ / share | Positive decimal | NSE Official Feed | Optional | NaN if unavailable | Must be > 0.0 if present |
| `listing_gain_pct` | Opening gain or discount percentage | Float | % | Decimal | Derived outcome | Required | Computed deterministically | Formula: `((open - issue) / issue) * 100` |
| `listing_positive` | Binary outcome (1=Premium, 0=Discount/Par) | Integer | Binary | `0` or `1` | Derived classification target | Required | Computed deterministically | `1` if `listing_gain_pct > 0.0` else `0` |

---

### C. `ipo_gmp_history.csv` (GMP Time Series Sentiment)
Preserves granular grey market movements across the entire IPO lifecycle (from DRHP filing to listing morning).

| Field Name | Description | Data Type | Unit | Expected Format | Primary Source | Required? | Missing Handling | Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | Canonical IPO identifier | String | None | `INMAIN-YYYY-NNNN` | Master Registry | Required | Foreign key | Must match regex `^INMAIN-\d{4}-\d{4}$` |
| `recorded_at` | Timestamp of the quoted premium | DateTime | ISO 8601 | `YYYY-MM-DDTHH:MM:SS` | Tracker platform | Required | Fatal error if missing | Valid ISO timestamp |
| `gmp` | Unofficial market premium per share | Float | ₹ / share | Decimal | Tracker platform | Required | Fatal error if missing | Can be negative, zero, or positive |
| `source` | Name of tracker reporting the quote | String | Text | E.g. "InvestorGain" | Tracker platform | Required | Fatal error if missing | Min length 2 characters |
| `source_url` | Direct URL of observation | String | URL | Valid HTTP/S URL | Scraper metadata | Optional | NaN if uncaptured | Valid URL format if present |
| `notes` | Market context or trading status | String | Text | E.g. "Kostak 500", "Subject to Sauda" | Market tracker | Optional | NaN if absent | Text string |

---

### D. `ipo_feature_sources.csv` (Data Provenance & RAG Audit)
Tracks the exact origin, extraction methodology, and verification status for every critical fundamental and valuation feature. Serves as the audit backbone for Phase 5 (RHP/DRHP RAG Engine).

| Field Name | Description | Data Type | Unit | Expected Format | Required? | Missing Handling | Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | Canonical IPO identifier | String | None | `INMAIN-YYYY-NNNN` | Required | Foreign key | Must match regex `^INMAIN-\d{4}-\d{4}$` |
| `prediction_stage` | Associated prediction stage | String | Enum | `pre_close` or `post_close` | Required | Fatal error if missing | Must be 'pre_close' or 'post_close' |
| `data_cutoff` | Frozen snapshot timestamp | DateTime | ISO 8601 | `YYYY-MM-DDTHH:MM:SS` | Required | Fatal error if missing | Valid ISO timestamp |
| `feature_name` | Name of feature sourced | String | Column Name | E.g. "revenue", "ebitda" | Required | Fatal error if missing | Must correspond to valid feature |
| `feature_value` | Raw recorded value | String | Stringified | E.g. "11247.3" | Required | Fatal error if missing | String representation of value |
| `source_name` | Entity or document providing data | String | Text | E.g. "SEBI_RHP", "Chittorgarh" | Required | Fatal error if missing | Valid text |
| `source_url` | Direct URL to online source / PDF | String | URL | Valid HTTP/S URL | Optional | Empty string / NaN | Valid URL if present |
| `document_name` | Name of prospectus PDF file | String | Filename | E.g. "Swiggy_RHP.pdf" | Optional | Empty string / NaN | File basename if RHP extract |
| `document_page` | PDF page number where value appears | Integer | Page number | Positive integer | Optional | NaN if not from PDF | Must be >= 1 if present |
| `retrieved_at` | Timestamp when data was retrieved | DateTime | ISO 8601 | `YYYY-MM-DDTHH:MM:SS` | Required | Defaults to ingestion time | Valid ISO timestamp |
| `verification_status`| Verification workflow state | String | Enum | `unverified`, `llm_extracted`, `verified` | Required | Defaults to "unverified" | 'unverified', 'llm_extracted', or 'verified' |
| `notes` | Context or extraction caveats | String | Text | E.g. "Restated Ind AS summary" | Optional | Empty string / NaN | Text string |

---

### E. `ipo_registry.csv` (Master IPO Directory)
The authoritative master registry establishing unique, permanent identifiers for Indian Mainboard IPOs.

| Field Name | Description | Data Type | Unit | Expected Format | Required? | Missing Handling | Validation Rules |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | Canonical IPO identifier | String | None | `INMAIN-YYYY-NNNN` | Required | Primary Key | Unique, immutable |
| `company_name` | Registered legal corporate name | String | Text | E.g. "Swiggy Limited" | Required | Fatal error if missing | Min length 2 characters |
| `symbol` | Exchange ticker symbol | String | Text | E.g. "SWIGGY" | Optional | Empty string if unassigned | Uppercase alphanumeric |
| `issue_open_date` | Subscription opening date | Date | Date | `YYYY-MM-DD` | Optional | Empty string if unannounced | Valid date |
| `issue_close_date` | Subscription closing date | Date | Date | `YYYY-MM-DD` | Optional | Empty string if unannounced | Valid date, >= open date |
| `listing_date` | Date of exchange listing | Date | Date | `YYYY-MM-DD` | Optional | Empty string if unlisted | Valid date, >= close date |

---

## 3. Data Integrity & Validation Safeguards

1. **Uniqueness:**
   - In `ipo_features.csv`, each tuple of `(ipo_id, prediction_stage, data_cutoff)` must be strictly unique.
   - In `ipo_outcomes.csv` and `ipo_registry.csv`, `ipo_id` must be strictly unique (1 row per IPO).
2. **Temporal Precedence:**
   - $\text{issue\_open\_date} \le \text{issue\_close\_date} \le \text{listing\_date}$.
   - All feature values in a snapshot row must have an observation timestamp $\le \text{data\_cutoff}$.
3. **Leakage Prohibition:**
   - For all rows where $\text{prediction\_stage} = \text{"pre\_close"}$:
     $$\text{qib\_subscription} = \text{nii\_subscription} = \text{retail\_subscription} = \text{overall\_subscription} = \mathbf{NaN}$$
4. **Calculated Target Invariants:**
   - $\text{listing\_gain\_pct} = \frac{\text{listing\_open\_price} - \text{issue\_price}}{\text{issue\_price}} \times 100$.
   - $\text{listing\_positive} = \begin{cases} 1 & \text{if } \text{listing\_gain\_pct} > 0.0 \\ 0 & \text{if } \text{listing\_gain\_pct} \le 0.0 \end{cases}$ (Note: a gain of exactly $0.0\%$ lists at par, thus $\text{listing\_positive} = 0$).
