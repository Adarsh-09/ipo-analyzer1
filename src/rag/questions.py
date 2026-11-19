"""Existing IPO prospectus questions and extraction field definitions."""

# ---------------------------------------------------------
# EXISTING CHECKLIST QUESTIONS — LABELS PRESERVED
# ---------------------------------------------------------

CHECKLIST_QUESTIONS = {

    "Business overview":
        "What does the company do, and what are its main products or services and customers?",

    "Top risk factors":
        "What are the most important risk factors disclosed? List the top five with a one-line explanation each.",

    "Objects of the issue":
        "What are the objects of the issue and how will the proceeds be used? Give amounts if stated.",

    "Fresh issue vs offer for sale":
        "How much of the issue is a fresh issue and how much is an offer for sale, and who are the selling shareholders?",

    "Promoters and pledges":
        "Who are the promoters, what is their shareholding before and after the issue, and is any promoter shareholding pledged?",

    "Litigation":
        "Summarise the material outstanding litigation, including amounts involved, against the company, promoters and directors.",

    "Related-party transactions":
        "What related-party transactions are disclosed and how large are they relative to revenue?",

    "Financial summary":
        "Summarise revenue, profit after tax, EBITDA, net worth and borrowings for the periods presented.",

    "Capital structure":
        "What is the share capital before and after the issue, including the number of equity shares outstanding?",

}


# ---------------------------------------------------------
# IMPROVED RETRIEVAL QUERIES
# ---------------------------------------------------------

RETRIEVAL_QUERIES = {

    "Business overview":
        "our business overview who we are company profile "
        "business model products services customers operations "
        "manufacturing facilities geography segment revenue",

    "Top risk factors":
        "risk factors summary of risks key risks material risks "
        "internal risks external risks adversely affect business "
        "concentration dependency regulatory risk",

    "Objects of the issue":
        "objects of the offer objects of the fresh issue "
        "net proceeds utilisation estimated amount repayment "
        "capital expenditure general corporate purposes",

    "Fresh issue vs offer for sale":
        "the offer fresh issue offer for sale OFS "
        "selling shareholders number of equity shares "
        "aggregating issue size net proceeds primary secondary sale",

    "Promoters and pledges":
        "our promoters promoter shareholding pre offer post offer "
        "shareholding pattern pledged encumbrance security lenders",

    "Litigation":
        "outstanding litigation material litigation "
        "civil proceedings criminal proceedings tax proceedings "
        "aggregate amount involved company promoters directors",

    "Related-party transactions":
        "related party transactions Ind AS 24 "
        "absolute amount related parties revenue purchases sales "
        "loans guarantees outstanding balances",

    "Financial summary":
        "summary of restated consolidated financial information "
        "revenue from operations profit after tax profit for year "
        "EBITDA net worth total borrowings cash generated "
        "from operating activities total assets financial years "
        "inventory days return on equity return on capital employed",

    "Capital structure":
        "capital structure equity share capital "
        "authorised issued subscribed fully paid up "
        "pre offer post offer number equity shares "
        "shareholding pattern face value fresh issue shares",
}


# ---------------------------------------------------------
# STRUCTURED EXTRACTION SCHEMAS
# ---------------------------------------------------------
#
# Each field uses:
#   type: number / text / list / series / amount
#   unit: expected unit (where applicable)
#   description: what Gemini must extract
#
# These schemas do NOT determine scores.
# The existing scoring.py remains responsible for scoring.
# ---------------------------------------------------------

EXTRACTION_FIELDS = {

    "Business overview": {

        "business_overview": {
            "type": "text",
            "description": "Business model, main operations and products."
        },

        "products_services": {
            "type": "list",
            "description": "Main products and services."
        },

        "customer_concentration": {
            "type": "text",
            "description": "Major customers and disclosed concentration risks."
        },

        "competitive_strengths": {
            "type": "list",
            "description": "Competitive strengths explicitly stated in the RHP."
        },

    },


    "Top risk factors": {

        "top_risk_factors": {
            "type": "list",
            "description": "Up to five material risk factors and explanations."
        },

    },


    "Objects of the issue": {

        "objects_of_issue": {
            "type": "list",
            "description": "Objects of the issue with their allocations and amounts."
        },

        "use_of_proceeds_summary": {
            "type": "text",
            "description": "How the issue proceeds will be used."
        },

    },


    "Fresh issue vs offer for sale": {

        "fresh_issue_amount": {
            "type": "amount",
            "unit": "INR crore",
            "description": "Amount allocated to fresh issue."
        },

        "ofs_amount": {
            "type": "amount",
            "unit": "INR crore",
            "description": "Amount allocated to offer for sale."
        },

        "selling_shareholders": {
            "type": "list",
            "description": "Names of selling shareholders."
        },

    },


    "Promoters and pledges": {

        "promoter_names": {
            "type": "list",
            "description": "Names of promoters."
        },

        "promoter_holding_pre_pct": {
            "type": "number",
            "unit": "%",
            "description": "Promoter shareholding before the issue."
        },

        "promoter_holding_post_pct": {
            "type": "number",
            "unit": "%",
            "description": "Promoter shareholding after the issue."
        },

        "promoter_pledge_pct": {
            "type": "number",
            "unit": "%",
            "description": "Percentage of promoter shareholding pledged."
        },

        "promoter_pledge_details": {
            "type": "text",
            "description": "Details of pledged or encumbered promoter shares."
        },

    },


    "Litigation": {

        "material_litigation": {
            "type": "list",
            "description": "Material proceedings, parties, nature and amounts."
        },

        "litigation_summary": {
            "type": "text",
            "description": "Summary of disclosed material litigation."
        },

    },


    "Related-party transactions": {

        "related_party_transactions": {
            "type": "list",
            "description": "Material related-party transactions, parties and amounts."
        },

        "related_party_summary": {
            "type": "text",
            "description": "Overall summary of related-party transactions."
        },

    },


    "Financial summary": {

        "revenue": {
            "type": "series",
            "unit": "INR crore",
            "description": "Revenue from operations for every financial year."
        },

        "pat": {
            "type": "series",
            "unit": "INR crore",
            "description": "Profit after tax for every financial year."
        },

        "ebitda": {
            "type": "series",
            "unit": "INR crore",
            "description": "EBITDA for each disclosed financial year."
        },

        "net_worth": {
            "type": "series",
            "unit": "INR crore",
            "description": "Net worth for each financial year."
        },

        "total_borrowings": {
            "type": "series",
            "unit": "INR crore",
            "description": "Total borrowings for each financial year."
        },

        "cfo": {
            "type": "series",
            "unit": "INR crore",
            "description": "Net cash generated from operating activities by year."
        },

        "inventory_days": {
            "type": "series",
            "unit": "days",
            "description": "Inventory holding days for each financial year, or latest year."
        },

        "roe_pct": {
            "type": "number",
            "unit": "%",
            "description": "Return on equity for the latest reported year."
        },

        "roce_pct": {
            "type": "number",
            "unit": "%",
            "description": "Return on capital employed for the latest reported year."
        },

        "ebitda_margin_pct": {
            "type": "number",
            "unit": "%",
            "description": "Reported EBITDA margin for the latest year."
        },

        "debt_to_equity": {
            "type": "number",
            "unit": "times",
            "description": "Reported debt-to-equity ratio."
        },

        "interest_coverage": {
            "type": "number",
            "unit": "times",
            "description": "Reported interest coverage ratio."
        },

    },


    "Capital structure": {

        "pre_offer_share_count": {
            "type": "number",
            "unit": "shares",
            "description": "Outstanding equity shares before the offer."
        },

        "post_offer_share_count": {
            "type": "number",
            "unit": "shares",
            "description": "Outstanding equity shares after the offer."
        },

        "fresh_issue_shares": {
            "type": "number",
            "unit": "shares",
            "description": "Number of fresh equity shares issued."
        },

        "face_value": {
            "type": "number",
            "unit": "INR per share",
            "description": "Face value of each equity share."
        },

    },

}