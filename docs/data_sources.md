# IPOVision — Verified Public Data Sources

**Document Version:** 1.0.0  
**Phase:** 1 & 2 Synthesis  
**Market:** Indian Mainboard IPOs Only  

---

## 1. Verified Data Sources Overview

Based on empirical testing conducted during Phase 1 across 10 candidates, the following sources have been verified and selected for the IPOVision pipeline:

| Source | Role in Pipeline | Accessibility | Structure | Key Fields Sourced |
| :--- | :--- | :--- | :--- | :--- |
| **InvestorGain** | Primary: Subscriptions, Outcomes & GMP | High (Server-side HTML) | `table#reportTable` | Total, QIB, NII, Retail Subscriptions; Upper Band Issue Price; P/E; Issue Size; Listing Open/Close Prices; Live & Historical GMP |
| **Chittorgarh (Detail Pages)** | Primary: Company Fundamentals & Valuation | High (Server-side HTML) | 14–16 Tables per IPO page | 4-Year Restated Financials (Revenue, PAT, EBITDA, Debt, Net Worth, Cash Flow); Valuation (EPS, P/E, P/B); Key Performance Indicators (ROE, ROCE, RoNW, NAV) |
| **SEBI (Securities & Exchange Board of India)** | Primary: RHP/DRHP Documents & RAG | High (Public PDFs) | Statutory PDFs (100% digital text) | Prospectuses, Objects of the Issue, Detailed Risk Factors, Industry Overview, Promoter Disclosures |
| **NSE / BSE** | Secondary: Master Verification & Tickers | Moderate (Session cookies required) | REST/HTML | Canonical Ticker Symbols, Allotment Dates, Official Listing Settlement Prices |

---

## 2. Inaccessibility & Limitations Identified

1. **Chittorgarh Summary / Report Pages:** Use React client-side rendering; raw HTTP GET returns a shell with 0 data tables. We bypass this by scraping individual IPO detail pages (`/ipo/<slug>/<id>/`) which are 100% server-side HTML.
2. **Chittorgarh Subscription Status:** Bidding breakdown tables are paywalled under "IPOMatrix". We source subscription multiples cleanly from InvestorGain.
3. **Grey Market Premium (GMP):** Unofficial market quote. It is recorded with timestamp and source. Missing GMP is **never filled with 0.0**.
4. **Mainboard vs SME:** Sources often interleave SME issues. Mainboard filtering is enforced (`is_sme == False`, issue size >= 50 Cr).

