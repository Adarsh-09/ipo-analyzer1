# IPOVision — Sources, Provenance & Analytical Limitations

**Document Version:** 1.1.0 (Updated after Phase 1 Empirical Testing)  
**Target Market:** Indian Mainboard IPOs Only  
**Last Tested:** November 2026

---

## 1. Empirical Source Testing Results (Phase 1)

During Phase 1, we tested 10 candidate public endpoints across 5 core categories to assess HTTP accessibility, HTML rendering architecture, data field availability, and technical limitations.

| Source & URL | Category | HTTP Status | Response Time | Rendering Type | Usability & Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **InvestorGain Mainboard Listing**<br>`/report/ipo-listing-day-performance/333/mainboard/` | IPO Listing + Subscription | 200 OK | ~60 ms | **Server-side HTML** | **PRIMARY FOR SUBSCRIPTION & OUTCOMES.** Clean `table#reportTable` with Total, QIB, NII, Retail subscription rates, issue price, P/E, and size. |
| **Chittorgarh IPO Detail Pages**<br>`/ipo/<company-name>-ipo/<id>/` | Fundamentals + Valuation | 200 OK | ~180 ms | **Server-side HTML** | **PRIMARY FOR COMPANY FUNDAMENTALS.** Contains 14–16 full HTML tables with 4-year restated balance sheets, P&L, KPIs (ROE, ROCE, NAV), valuation, and listing prices. |
| **Chittorgarh Summary Reports**<br>`/report/ipo-listing-day-performance/82/` | Summary Listing | 200 OK | ~800 ms | **Client-side React** | **LIMITED.** Page returns a React shell; tables are rendered via client-side JavaScript. 0 `<table>` elements in static HTML. |
| **Chittorgarh Subscription Status**<br>`/report/ipo-subscription-status-.../` | Subscription | 200 OK | ~110 ms | **Server-side with paywall** | **PAYWALLED.** Table 11 on detail pages and report pages lock full bidding history behind a login ("IPOMatrix"). Use InvestorGain instead. |
| **InvestorGain Live GMP**<br>`/report/live-ipo-gmp/331/` | Grey Market Premium | 200 OK | ~60 ms | **Server-side HTML** | **PRIMARY FOR LIVE GMP.** Real HTML table with quoted GMP, estimated listing price, update timestamps, and ratings. |
| **SEBI Offer Documents**<br>`sebi.gov.in/sebiweb/home/...` | Statutory Prospectuses | 200 OK | ~2.2 s | **Server-side HTML** | **PRIMARY FOR RHP/DRHP RAG.** Direct links to statutory RHP and DRHP PDFs. Downloads verified at ~0.5–2 MB for abridged, 20–80 MB for full RHP. |
| **NSE India IPO Section**<br>`nseindia.com/market-data/...` | Official Exchange Data | 200 OK | ~1.8 s | **Mixed / API-based** | **SECONDARY AUDIT.** Authoritative for exchange symbols and final allotment prices, but requires browser-like session cookies. |
| **BSE India Public Issue Page**<br>`bseindia.com/publicissue.html` | Official Exchange Data | 200 OK | ~70 ms | **Static shell** | **SECONDARY AUDIT.** General navigation page; actual IPO notices require traversing specific corporate announcement circulars. |

---

## 2. Multi-Source Architecture Strategy

Because no single public website provides complete, unencumbered, historical coverage for all required fields, IPOVision employs an **Ensemble Multi-Source Strategy**:

```text
               +------------------------------------------------+
               |              IPOVision Multi-Source Ingestion  |
               +------------------------------------------------+
                                       |
     -------------------------------------------------------------------------
     |                         |                         |                   |
InvestorGain               Chittorgarh              SEBI Filings         NSE / BSE
     |                         |                         |                   |
     v                         v                         v                   v
- Overall Subscription    - 4-Year Income Stmt     - Full RHP/DRHP PDFs  - Exchange Tickers
- QIB Subscription        - Balance Sheet Metrics  - Statutory Risks     - Official Allotment
- NII Subscription        - KPIs (ROE, ROCE, NAV)  - Objects of Issue    - Final Listing Day
- Retail Subscription     - Pre/Post IPO P/E       - Direct Text Data      Open & Close
- Live & Cutoff GMP       - Pre/Post Holding         (100% digital text)
     |                         |                         |                   |
     -------------------------------------------------------------------------
                                       |
                                       v
                    Data Cleaning & Reconciliation Pipeline
             (Duplicate elimination, cross-validation, unit conversion)
```

---

## 3. Technical Discoveries & Engineering Guardrails

### A. JavaScript-Rendered Pages
- **Finding:** Chittorgarh's high-level report pages (e.g. `/report/ipo-listing-day-performance/`) load their data tables via React on the client side. A standard `requests.get()` call receives only a 128 KB shell with 0 tables.
- **Solution:** We do not need heavy browser automation (Selenium/Playwright) because Chittorgarh's **individual detail pages** (`/ipo/...`) are fully server-side rendered with 14–16 rich HTML tables, and InvestorGain's listing tables are pure HTML.

### B. Subscription Data Paywalls
- **Finding:** Chittorgarh has placed detailed subscription bidding tables behind a paid subscription gate ("IPOMatrix").
- **Solution:** InvestorGain maintains completely open, unauthenticated subscription bidding tables across all investor categories (Total, QIB, NII, Retail).

### C. RHP PDF Extractability
- **Finding:** We downloaded and tested a real statutory offer document from SEBI. 
  - **100% selectable text** across all tested pages (zero scanned images).
  - High word density (**528 words per page** average).
  - Key sections (`Risk Factors`, `Promoter Information`, `Financial Information`) are cleanly detected using case-insensitive heading searches.
- **Conclusion:** Standard OCR will rarely be needed for modern SEBI filings. PyMuPDF (`pymupdf`) can extract high-quality text in milliseconds without heavy GPU/Tesseract requirements.

---

## 4. Key Limitations & Risk Disclaimers

1. **Unofficial Nature of GMP:** Grey Market Premium is an informal forward contract quoted in unorganized dealer circles. Quotes can be illiquid and manipulated. IPOVision records GMP with source and timestamp, and **never treats missing GMP as zero**.
2. **Mainboard vs SME Filtering:** Web sources frequently intermix SME IPOs with Mainboard IPOs. Our scrapers enforce explicit filtering (`is_sme == False`) to preserve dataset integrity.
3. **Restated Financial Adjustments:** Historical financials reported in offer documents reflect restated figures under Ind AS for the offer period. They may differ from statutory standalone filings.

---

## 5. Legal & Educational Disclaimer

> [!WARNING]
> **Not Financial Advice:** IPOVision is an educational data science and portfolio research project created to demonstrate end-to-end machine learning, data engineering, and NLP techniques on financial records.
> 
> The outputs, predictions, probabilities, and fundamental scores generated by IPOVision do **not** constitute financial, legal, tax, or investment advice. The creator is not a SEBI-registered research analyst or investment adviser. Always consult a certified financial advisor and review the full statutory offer document before making investment decisions.
