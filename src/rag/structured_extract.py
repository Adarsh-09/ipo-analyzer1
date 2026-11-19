"""
IPOVision: Structured RHP/DRHP evidence extraction.

Uses the existing hybrid retriever and LLM provider configuration.
Every extracted field must have a source-backed quotation.
No extracted field is automatically approved for scoring.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict

from src.rag.answer import generate_text, is_configured


SYSTEM_PROMPT = """
You are a financial document extraction assistant for IPOVision.

Your task is to extract information from Indian IPO RHP/DRHP documents.

STRICT RULES:

1. Use ONLY the supplied document excerpts.
2. Never invent numbers, financial values or company information.
3. Never use outside knowledge.
4. Return valid JSON only. No Markdown or explanations outside JSON.
5. Every extracted fact must have a supporting verbatim quotation.
6. Every quotation must contain the correct source page number.
7. If information is unavailable, return null.
8. Preserve financial years and units exactly.
9. Financial series must be ordered oldest to newest.
10. Do not assign investment ratings or checklist scores.
11. Distinguish reported values from calculated values.
12. Confidence is an extraction-quality estimate, NOT an investment probability.

Do not provide investment advice.
"""


# Separate extraction requests to keep prompts manageable.
GROUPS = {

    "financials": {
        "query": (
            "summary of restated consolidated financial information "
            "revenue from operations profit for the year profit after tax "
            "EBITDA net worth total borrowings operating cash flows "
            "return on equity return on capital employed "
            "debt equity interest coverage inventory days"
        ),

        "fields": {
            "revenue": "Revenue from operations by financial year.",
            "pat": "Profit after tax by financial year.",
            "ebitda": "EBITDA by financial year.",
            "cfo": "Net cash generated from operating activities by year.",
            "inventory_days": "Inventory holding days by financial year.",

            "ebitda_margin_pct": "Latest explicitly reported EBITDA margin percentage.",
            "roe_pct": "Latest explicitly reported ROE percentage.",
            "roce_pct": "Latest explicitly reported ROCE percentage.",
            "debt_to_equity": "Latest explicitly reported debt-to-equity ratio.",
            "interest_coverage": "Latest explicitly reported interest coverage ratio.",
        },
    },

    "valuation_and_peers": {
        "query": (
            "basis for issue price earnings per share P E ratio "
            "listed industry peers peer comparison peer group"
        ),

        "fields": {
            "pe_ratio": "Issuer IPO P/E ratio.",
            "peer_pe_ratio": "Peer median P/E ratio.",
            "peer_ebitda_margin_pct": "Peer median EBITDA margin percentage.",
            "peer_roe_pct": "Peer median ROE percentage.",
            "peer_revenue_growth_pct": "Peer median revenue growth percentage.",
        },
    },

    "promoters_and_risks": {
        "query": (
            "our promoters promoter shareholding pre offer post offer "
            "pledge encumbrance litigation outstanding material "
            "civil criminal tax proceedings"
        ),

        "fields": {
            "promoter_holding_post_pct": (
                "Promoter shareholding after IPO as percentage."
            ),

            "promoter_pledge_pct": (
                "Percentage of promoter shareholding pledged. "
                "Return zero only if the document explicitly says none."
            ),

            "litigation_summary": (
                "Material outstanding litigation, parties and amounts."
            ),
        },
    },

    "issue_structure": {
        "query": (
            "terms of the offer fresh issue offer for sale "
            "selling shareholders objects of the offer "
            "utilisation of net proceeds"
        ),

        "fields": {
            "ofs_pct": (
                "OFS as percentage of total issue size. "
                "Only return if supported by disclosed figures."
            ),

            "fresh_issue_amount": "Fresh issue amount and unit.",
            "ofs_amount": "Offer for sale amount and unit.",

            "objects_of_issue": (
                "Objects of the issue and their allocated amounts."
            ),

            "use_of_funds_summary": (
                "Summary of how IPO proceeds will be utilised."
            ),
        },
    },

    "business_and_related_parties": {
        "query": (
            "our business business overview products services customers "
            "competitive strengths concentration risk factors "
            "related party transactions"
        ),

        "fields": {
            "business_overview": (
                "Business model, products, services and customer types."
            ),

            "top_risk_factors": (
                "Up to five major disclosed risk factors."
            ),

            "related_party_transactions": (
                "Related-party transactions and amounts."
            ),
        },
    },
}


SERIES_FIELDS = {
    "revenue",
    "pat",
    "ebitda",
    "cfo",
    "inventory_days",
}

TEXT_FIELDS = {
    "litigation_summary",
    "use_of_funds_summary",
    "business_overview",
    "related_party_transactions",
}

LIST_FIELDS = {
    "objects_of_issue",
    "top_risk_factors",
}

PERCENT_FIELDS = {
    "ebitda_margin_pct",
    "roe_pct",
    "roce_pct",
    "promoter_holding_post_pct",
    "promoter_pledge_pct",
    "peer_ebitda_margin_pct",
    "peer_roe_pct",
    "peer_revenue_growth_pct",
    "ofs_pct",
}


def normalize_text(text: str) -> str:
    """Normalize text for quotation matching."""

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        str(text).lower()
    ).strip()


def parse_json_response(raw: str) -> Dict[str, Any]:
    """Parse JSON even when the provider adds Markdown fences."""

    raw = (raw or "").strip()

    raw = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw,
        flags=re.IGNORECASE
    )

    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end <= start:
        raise ValueError(
            "LLM did not return a valid JSON object."
        )

    data = json.loads(raw[start:end + 1])

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")

    return data


def is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    )


def validate_value(field: str, value: Any) -> bool:

    if value is None:
        return False

    if field in SERIES_FIELDS:

        if not isinstance(value, list) or not value:
            return False

        return all(
            isinstance(row, dict)
            and isinstance(row.get("period"), str)
            and is_number(row.get("amount"))
            for row in value
        )

    if field in TEXT_FIELDS:
        return isinstance(value, str) and bool(value.strip())

    if field in LIST_FIELDS:
        return (
            isinstance(value, list)
            and bool(value)
            and all(isinstance(x, str) for x in value)
        )

    if field in {"fresh_issue_amount", "ofs_amount"}:
        return (
            isinstance(value, dict)
            and is_number(value.get("amount"))
            and isinstance(value.get("unit"), str)
        )

    return is_number(value)


def validate_evidence(
    evidence: Any,
    page_texts: Dict[int, str]
) -> list:

    verified = []

    if not isinstance(evidence, list):
        return verified

    for item in evidence:

        if not isinstance(item, dict):
            continue

        try:
            page = int(item.get("page"))
        except (TypeError, ValueError):
            continue

        quote = str(item.get("quote") or "").strip()

        if not quote:
            continue

        original_text = page_texts.get(page, "")

        normalized_quote = normalize_text(quote)
        normalized_source = normalize_text(original_text)

        # Check whether the quotation really occurs in the retrieved page.
        if (
            len(normalized_quote) >= 18
            and normalized_quote in normalized_source
        ):
            verified.append({
                "page": page,
                "quote": quote,
            })

    return verified


def build_field_result(
    field: str,
    raw: Any,
    page_texts: Dict[int, str]
) -> Dict[str, Any]:

    if not isinstance(raw, dict):
        raw = {}

    value = raw.get("value")

    evidence = validate_evidence(
        raw.get("evidence", []),
        page_texts
    )

    confidence = raw.get("confidence", 0)

    confidence = (
        float(confidence)
        if is_number(confidence)
        else 0.0
    )

    confidence = min(max(confidence, 0.0), 1.0)

    if value is None:
        status = "not_found"

    elif not validate_value(field, value):
        status = "unverified"

    elif not evidence:
        status = "unverified"

    else:
        status = "verified"

    # Sanity checks. Values failing checks remain unapproved.
    if status == "verified" and field in PERCENT_FIELDS:
        if not 0 <= float(value) <= 100:
            status = "unverified"

    if status == "verified" and field in {
        "debt_to_equity",
        "interest_coverage",
        "pe_ratio",
        "peer_pe_ratio",
    }:
        if float(value) < 0:
            status = "unverified"

    return {
        "value": value,
        "unit": str(raw.get("unit") or ""),
        "status": status,
        "confidence": confidence,
        "evidence": evidence,
        "approved": False,
    }


def extract_rhp_evidence(
    retriever,
    settings: Dict[str, Any],
    top_k: int = 8
) -> Dict[str, Any]:
    """
    Retrieve five RHP topic groups and extract structured evidence.

    `retriever` must expose search(query, k, pool), matching
    IPOVision's existing HybridRetriever.
    """

    if not is_configured(settings):
        raise RuntimeError(
            "No LLM provider configured. Check your .env."
        )

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider": settings.get("provider"),
        "model": settings.get("model"),
        "fields": {},
        "group_errors": {},
    }

    for group_name, specification in GROUPS.items():

        fields = specification["fields"]

        hits = retriever.search(
            specification["query"],
            k=top_k,
            pool=40
        )

        if not hits:

            result["group_errors"][group_name] = (
                "No relevant passages retrieved."
            )

            for field in fields:
                result["fields"][field] = build_field_result(
                    field, {}, {}
                )

            continue

        # Preserve the original page text for source validation.
        page_texts = {}

        for hit in hits:

            page = int(hit["page"])

            page_texts[page] = (
                page_texts.get(page, "")
                + "\n"
                + hit["text"]
            )

        excerpts = "\n\n".join(
            f"[SOURCE PAGE {hit['page']}]\n{hit['text']}"
            for hit in hits
        )

        field_instructions = "\n".join(
            f'- "{key}": {description}'
            for key, description in fields.items()
        )

        expected_structure = {
            key: {
                "value": None,
                "unit": "",
                "confidence": 0.0,
                "evidence": [],
            }
            for key in fields
        }

        prompt = f"""
Extract the following information from the supplied RHP excerpts.

FIELDS:
{field_instructions}

Return this JSON structure with every requested key:

{json.dumps(expected_structure, ensure_ascii=False)}

OUTPUT RULES:

For financial series:
"value" must be a list of objects:
[
  {{"period": "FY2023", "amount": 500}}
]

For list fields:
"value" must be a list of strings.

For amount fields:
"value" must be:
{{"amount": 100, "unit": "INR crore"}}

For scalar fields:
"value" must be a number.

For text fields:
"value" must be a string.

Use null if the source does not contain the information.

Every evidence entry must contain:
- page: actual integer source page number
- quote: exact quotation from that page

Do not create calculations that cannot be supported by the excerpts.

SOURCE EXCERPTS:

{excerpts}
"""

        try:

            raw_text = generate_text(
                settings.get("provider"),
                SYSTEM_PROMPT,
                prompt,
                api_key=settings.get("api_key"),
                model=settings.get("model"),
                host=settings.get("host"),
            )

            extracted = parse_json_response(raw_text)

        except Exception as exc:

            result["group_errors"][group_name] = (
                f"{type(exc).__name__}: {exc}"
            )

            for field in fields:

                result["fields"][field] = build_field_result(
                    field, {}, page_texts
                )

            continue

        for field in fields:

            result["fields"][field] = build_field_result(
                field,
                extracted.get(field),
                page_texts
            )

    return result