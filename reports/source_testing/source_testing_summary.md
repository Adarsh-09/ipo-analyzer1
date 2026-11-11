# IPOVision — Source Testing Summary (Phase 1)

**Generated:** Phase 1 Verification  
**Total Sources Tested:** 10  
**Successful:** 10 / 10 (100% reachable)  

## Key Takeaways
1. **InvestorGain:** Best for subscription data (QIB, NII, Retail, Total) and listing-day open prices. Server-rendered table `#reportTable`.
2. **Chittorgarh IPO Detail Pages:** Best for multi-year restated balance sheets, P&L (Revenue, EBITDA, PAT, Debt, Net Worth), and valuation ratios (P/E, P/B, NAV, ROCE).
3. **SEBI Prospectuses:** 100% digital selectable text (~528 words/page), ready for Phase 5 RAG ingestion.
4. **Paywalls/Client Rendering:** Avoid Chittorgarh summary report tables (React) and Chittorgarh subscription paywall ("IPOMatrix"). Use the identified alternative sources.

