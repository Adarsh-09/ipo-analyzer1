"""Preset questions taken from the DRHP/RHP items of the IPO analysis checklist."""

CHECKLIST_QUESTIONS = {
    "Business overview": "What does the company do, and what are its main products or services and customers?",
    "Top risk factors": "What are the most important risk factors disclosed? List the top five with a one-line explanation each.",
    "Objects of the issue": "What are the objects of the issue and how will the proceeds be used? Give amounts if stated.",
    "Fresh issue vs offer for sale": "How much of the issue is a fresh issue and how much is an offer for sale, and who are the selling shareholders?",
    "Promoters and pledges": "Who are the promoters, what is their shareholding before and after the issue, and is any promoter shareholding pledged?",
    "Litigation": "Summarise the material outstanding litigation, including amounts involved, against the company, promoters and directors.",
    "Related-party transactions": "What related-party transactions are disclosed and how large are they relative to revenue?",
    "Financial summary": "Summarise revenue, profit after tax, EBITDA, net worth and borrowings for the periods presented.",
    "Capital structure": "What is the share capital before and after the issue, including the number of equity shares outstanding?",
}

# Retrieval queries use the words the document itself uses; BM25 and the embedder both respond to them.
RETRIEVAL_QUERIES = {
    "Business overview": "overview who we are our business company products services customers platform",
    "Top risk factors": "risk factors summary of risks internal risks key risks adversely affect our business",
    "Objects of the issue": "objects of the offer objects of the fresh issue net proceeds utilisation estimated amount",
    "Fresh issue vs offer for sale": "the offer fresh issue offer for sale selling shareholders number of equity shares aggregating",
    "Promoters and pledges": "our promoters shareholding pre-offer post-offer promoter pledge encumbrance equity shares pledged",
    "Litigation": "outstanding litigation material civil proceedings criminal proceedings tax proceedings aggregate amount involved",
    "Related-party transactions": "related party transactions Ind AS 24 aggregated absolute amount of related party transactions percentage of revenue",
    "Financial summary": "summary of restated consolidated financial information revenue from operations profit for the year EBITDA net worth total borrowings",
    "Capital structure": "capital structure equity share capital pre-offer post-offer number of equity shares outstanding issued subscribed paid-up",
}