"""
IPOVision — Deep HTML Structure Inspector (Phase 1)

Purpose:
    Some websites render data using JavaScript (div-based grids, Vue/React
    components, etc.) rather than plain HTML <table> elements. This script
    does a deeper inspection of page structures to find where the actual
    IPO data lives — whether in tables, divs, JSON-LD, embedded scripts,
    or API calls referenced in the page source.

Usage:
    cd e:\\ipo-analyzer1
    .venv\\Scripts\\Activate.ps1
    python src/collection/deep_inspector.py
"""

import sys
import re
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collection.http_client import IPOHttpClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def inspect_page_deeply(client: IPOHttpClient, url: str, label: str) -> Dict[str, Any]:
    """
    Perform a deep structural inspection of an HTML page.
    
    Checks for:
    - Standard HTML tables
    - Div-based data grids (Bootstrap tables, CSS-styled divs)
    - Embedded JSON data (script tags with application/json or variable assignments)
    - API endpoint references in JavaScript
    - Data attributes on elements
    """
    logger.info(f"Deep inspecting: {label}")
    result = {"label": label, "url": url, "findings": []}
    
    resp = client.get(url)
    if not resp["success"]:
        result["findings"].append(f"FAILED: {resp['error']}")
        return result
    
    html = resp["text"]
    soup = BeautifulSoup(html, "lxml")
    
    # 1. Check for HTML tables
    tables = soup.find_all("table")
    result["html_tables"] = len(tables)
    if tables:
        for i, table in enumerate(tables[:5]):
            cls = table.get("class", [])
            tid = table.get("id", "")
            rows = len(table.find_all("tr"))
            result["findings"].append(
                f"TABLE[{i}]: id='{tid}', class={cls}, rows={rows}"
            )
    
    # 2. Check for div-based grids or list structures
    # Many modern sites use div-based tables with classes like 'row', 'col', 'card'
    data_divs = soup.find_all("div", class_=re.compile(
        r"(table|grid|row|card|list-item|ipo|report)", re.I
    ))
    result["data_divs"] = len(data_divs)
    if data_divs:
        # Sample some class names
        sample_classes = set()
        for d in data_divs[:20]:
            for c in d.get("class", []):
                sample_classes.add(c)
        result["findings"].append(
            f"DIV data structures: {len(data_divs)} divs found. "
            f"Sample classes: {list(sample_classes)[:15]}"
        )
    
    # 3. Check for embedded JSON in script tags
    scripts = soup.find_all("script")
    json_data_found = []
    api_urls_found = []
    
    for script in scripts:
        content = script.string or ""
        
        # Look for JSON data assignments like: var data = [{...}];
        json_patterns = re.findall(
            r'(?:var|let|const)\s+\w+\s*=\s*(\[[\s\S]*?\]);', content
        )
        for match in json_patterns:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, list) and len(parsed) > 0:
                    json_data_found.append({
                        "type": "variable_assignment",
                        "items": len(parsed),
                        "sample_keys": list(parsed[0].keys())[:10] if isinstance(parsed[0], dict) else "non-dict"
                    })
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Look for API fetch calls
        api_patterns = re.findall(
            r'(?:fetch|axios\.get|ajax|\.get)\s*\(\s*["\']([^"\']+)["\']', content
        )
        api_urls_found.extend(api_patterns)
        
        # Look for URL patterns that suggest API endpoints
        url_patterns = re.findall(
            r'["\'](/api/[^"\']+|/rest/[^"\']+|/data/[^"\']+)["\']', content
        )
        api_urls_found.extend(url_patterns)
    
    if json_data_found:
        result["findings"].append(f"EMBEDDED JSON: {json_data_found}")
    if api_urls_found:
        result["findings"].append(f"API ENDPOINTS: {api_urls_found[:10]}")
    
    result["json_data_blocks"] = len(json_data_found)
    result["api_endpoints"] = api_urls_found[:10]
    
    # 4. Look for data stored in HTML data-* attributes
    elements_with_data = soup.find_all(attrs={"data-sort-value": True})
    if not elements_with_data:
        elements_with_data = soup.find_all(
            attrs=lambda attrs: attrs and any(k.startswith("data-") for k in attrs) if attrs else False
        )
    result["data_attributes"] = len(elements_with_data)
    if elements_with_data:
        sample_attrs = {}
        for el in elements_with_data[:5]:
            for k, v in el.attrs.items():
                if k.startswith("data-"):
                    sample_attrs[k] = str(v)[:50]
        result["findings"].append(f"DATA ATTRIBUTES: {len(elements_with_data)} elements. Sample: {sample_attrs}")
    
    # 5. Check page text for IPO-related keywords to confirm data presence
    page_text = soup.get_text(separator=" ", strip=True)
    ipo_keywords = [
        "issue price", "listing price", "listing gain", "subscription",
        "qib", "nii", "retail", "gmp", "grey market", "ipo date"
    ]
    found_keywords = [kw for kw in ipo_keywords if kw in page_text.lower()]
    result["ipo_keywords_in_text"] = found_keywords
    
    # 6. Check for specific Chittorgarh/InvestorGain structures
    # Chittorgarh often uses Bootstrap responsive table inside divs
    responsive_tables = soup.find_all("div", class_="table-responsive")
    if responsive_tables:
        result["findings"].append(
            f"RESPONSIVE TABLE DIVS: {len(responsive_tables)} found"
        )
    
    # Look for specific Chittorgarh report structure
    report_divs = soup.find_all("div", id=re.compile(r"report|content|main", re.I))
    if report_divs:
        result["findings"].append(
            f"REPORT DIVS: {len(report_divs)} divs with report/content/main IDs"
        )
    
    # 7. Check if page uses Vue.js, React, or Angular (indicating JS rendering)
    framework_signals = {
        "vue": "v-for" in html or "vue" in html.lower() or "__vue__" in html,
        "react": "react" in html.lower() or "_reactRoot" in html,
        "angular": "ng-app" in html or "angular" in html.lower(),
        "datatables": "datatable" in html.lower() or "DataTable" in html,
    }
    active_frameworks = [k for k, v in framework_signals.items() if v]
    if active_frameworks:
        result["findings"].append(f"JS FRAMEWORKS DETECTED: {active_frameworks}")
    result["frameworks"] = active_frameworks
    
    # 8. Extract a snippet of the main content area to see data structure
    main_content = soup.find("div", class_=re.compile(r"content|main|container", re.I))
    if main_content:
        text_preview = main_content.get_text(separator="\n", strip=True)[:500]
        result["content_preview"] = text_preview
    
    return result


def main():
    client = IPOHttpClient(rate_limit_delay=3.0)
    
    pages_to_inspect = [
        (
            "https://www.chittorgarh.com/report/ipo-listing-day-performance/82/",
            "Chittorgarh Listing Performance (0 tables — needs deep inspection)"
        ),
        (
            "https://www.chittorgarh.com/report/ipo-grey-market-premium-latest-mainboard-ipo-gmp/82/",
            "Chittorgarh GMP Page (0 tables — needs deep inspection)"
        ),
        (
            "https://www.chittorgarh.com/report/ipo-subscription-status-live-bidding-data/21/",
            "Chittorgarh Subscription (0 tables — needs deep inspection)"
        ),
        (
            "https://www.chittorgarh.com/report/mainboard-ipo-list-in-india-702/82/",
            "Chittorgarh Mainboard Archive (0 tables — needs deep inspection)"
        ),
        (
            "https://www.chittorgarh.com/ipo/swiggy-ipo/1670/",
            "Chittorgarh Detail Page (16 tables — verify structure)"
        ),
        (
            "https://www.investorgain.com/report/live-ipo-gmp/331/",
            "InvestorGain GMP (1 table found — verify structure)"
        ),
    ]
    
    all_results = []
    for url, label in pages_to_inspect:
        result = inspect_page_deeply(client, url, label)
        all_results.append(result)
        
        # Print findings immediately
        print(f"\n{'='*78}")
        print(f"  {result['label']}")
        print(f"  URL: {result['url']}")
        print(f"{'='*78}")
        print(f"  HTML Tables: {result.get('html_tables', 0)}")
        print(f"  Data DIVs: {result.get('data_divs', 0)}")
        print(f"  JSON data blocks: {result.get('json_data_blocks', 0)}")
        print(f"  Data attributes: {result.get('data_attributes', 0)}")
        print(f"  Frameworks: {result.get('frameworks', [])}")
        print(f"  IPO keywords in text: {result.get('ipo_keywords_in_text', [])}")
        
        for finding in result.get("findings", []):
            print(f"  >> {finding}")
        
        if result.get("api_endpoints"):
            print(f"  API Endpoints: {result['api_endpoints']}")
        
        if result.get("content_preview"):
            preview = result["content_preview"][:300]
            print(f"  Content preview:\n    {preview}")
    
    # Save deep inspection report
    output_path = PROJECT_ROOT / "data" / "raw" / "deep_inspection_report.json"
    # Make content_preview JSON-serializable
    for r in all_results:
        if "content_preview" in r:
            r["content_preview"] = r["content_preview"][:500]
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Deep inspection report saved to: {output_path}")


if __name__ == "__main__":
    main()

