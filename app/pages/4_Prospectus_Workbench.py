"""
IPOVision 2.0 — IPO Research Workbench

Combines:
1. RHP/DRHP evidence extraction
2. Fundamental checklist scoring
3. Listing checklist scoring
4. Prospectus question answering
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.components.common import (
    apply_candy_theme,
    footer,
    page_header,
    workflow_stepper,
)

from src.rag.index import (
    RAG_DIR,
    build_index,
    doc_id_from_path,
    index_exists,
)

from src.rag.retrieve import HybridRetriever

from src.rag.answer import (
    answer_question,
    get_llm_settings,
    is_configured,
    extract_structured_fields,
)

from src.rag.questions import (
    CHECKLIST_QUESTIONS,
    RETRIEVAL_QUERIES,
    EXTRACTION_FIELDS,
)

from src.rag.structured_extract import GROUPS

from src.fundamental_analysis.scoring import (
    FundamentalInputs,
    ListingInputs,
    score_fundamental,
    score_listing,
)

from src.fundamental_analysis.scoring import (
    fundamental_inputs_from_evidence,
)

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Prospectus Workbench - IPOVision",
    page_icon="📊",
    layout="wide",
)
apply_candy_theme()

page_header(
    title="Prospectus workbench",
    subtitle=(
        "Upload a Red Herring Prospectus (RHP / DRHP), extract structured financial and risk evidence "
        "via RAG, and query grounded citations with conversational reasoning."
    ),
    badge="LLM Reasoning & Extraction",
    category="RAG Pipeline Verified",
    live_text="Grounded Evidence Extraction",
    dot_color="pink",
)


PDF_DIR = RAG_DIR / "pdfs"

PDF_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ---------------------------------------------------------
# CACHED RESOURCES
# ---------------------------------------------------------

@st.cache_resource(
    show_spinner="Loading embedding model..."
)
def get_embedder():

    from src.rag.embeddings import default_embedder

    return default_embedder()


@st.cache_resource(show_spinner=False)
def get_retriever(document_id):

    return HybridRetriever(
        document_id,
        get_embedder()
    )


# ---------------------------------------------------------
# INPUT HELPERS
# ---------------------------------------------------------

def parse_number(label, key):

    raw = st.text_input(
        label,
        key=key,
        placeholder="Leave blank if unknown"
    )

    if not raw.strip():
        return None

    try:

        raw = raw.replace(",", "").replace("%", "")

        return float(raw)

    except ValueError:

        st.error(f"{label}: invalid numeric value.")

        return None


def parse_rating(label, key):

    selected = st.selectbox(
        label,
        ["Not rated", 0, 1, 2, 3, 4, 5],
        key=key
    )

    if selected == "Not rated":
        return None

    return float(selected)


# ---------------------------------------------------------
# SCORE DISPLAY
# ---------------------------------------------------------

def display_score(result, title):

    if result["score"] is None:

        st.info(
            "Enter or approve sufficient inputs to calculate this score."
        )

        return

    col1, col2, col3 = st.columns(3)

    col1.metric(
        title,
        f"{result['score']:.1f}/100"
    )

    col2.metric(
        "Score band",
        result["band"]
    )

    col3.metric(
        "Coverage",
        f"{result['coverage']:.0%}"
    )

    if result["partial"]:

        st.warning(
            "Less than 60% of the checklist is covered. "
            "Treat this score as a partial assessment."
        )

    rows = []

    for category, data in result["categories"].items():

        rows.append({

            "Category": category,

            "Weight": data["weight"],

            "Points earned": data["points"],

            "Status": (
                "Scored"
                if data["score"] is not None
                else "Missing"
            )
        })

    st.dataframe(
        rows,
        width="stretch",
        hide_index=True
    )

    for flag in result.get("red_flags", []):

        st.warning(flag)


# ---------------------------------------------------------
# DOCUMENT UPLOAD
# ---------------------------------------------------------

st.header("1. Upload IPO prospectus")

uploaded = st.file_uploader(
    "Upload RHP / DRHP PDF",
    type=["pdf"]
)

if uploaded is not None:

    safe_name = Path(uploaded.name).name

    destination = PDF_DIR / safe_name

    destination.write_bytes(
        uploaded.getbuffer()
    )


pdf_files = sorted(
    PDF_DIR.glob("*.pdf")
)

if not pdf_files:
    workflow_stepper(
        [
            ("1. Ingestion & Index", "Upload and index RHP PDF"),
            ("2. RAG Extraction", "Extract 9 statutory sections"),
            ("3. Evidence Review", "Verify citations & approve"),
            ("4. Scoring & Q&A", "Fundamental score & Q&A"),
        ],
        active_idx=1,
    )
    st.info(
        "Upload an RHP/DRHP PDF to begin."
    )

    footer()

    st.stop()


selected_pdf = st.selectbox(
    "Select prospectus",
    pdf_files,
    format_func=lambda p: p.name
)


doc_id = doc_id_from_path(selected_pdf)
extraction_key = f"ipovision_extraction_{doc_id}"

existing_ext = st.session_state.get(extraction_key)
if not index_exists(doc_id):
    active_step = 1
elif existing_ext is None:
    active_step = 2
elif any(f.get("approved") for f in existing_ext.get("fields", {}).values()):
    active_step = 4
else:
    active_step = 3

workflow_stepper(
    [
        ("1. Ingestion & Index", "Upload and index RHP PDF"),
        ("2. RAG Extraction", "Extract 9 statutory sections"),
        ("3. Evidence Review", "Verify citations & approve"),
        ("4. Scoring & Q&A", "Fundamental score & Q&A"),
    ],
    active_idx=active_step,
)


# ---------------------------------------------------------
# REBUILD EXISTING DOCUMENT INDEX
# ---------------------------------------------------------


if index_exists(doc_id):

    with st.expander("Document index maintenance"):

        if st.button(
            "Rebuild index using updated extraction",
            key=f"rebuild_{doc_id}"
        ):

            with st.spinner("Rebuilding prospectus index..."):

                info = build_index(
                    selected_pdf,
                    get_embedder(),
                    doc_id=doc_id,
                )

                get_retriever.clear()

                st.success(
                    f"Re-indexed {info['pages']} pages "
                    f"and {info['chunks']} chunks."
                )

                st.rerun()


# ---------------------------------------------------------
# BUILD INDEX IF REQUIRED
# ---------------------------------------------------------

if not index_exists(doc_id):

    st.warning(
        "The selected document is not indexed yet."
    )

    if st.button(
        "Build prospectus index",
        type="primary"
    ):

        progress = st.progress(
            0.0,
            text="Indexing document..."
        )

        try:

            info = build_index(
                selected_pdf,
                get_embedder(),
                doc_id=doc_id,
                progress=lambda done, total: progress.progress(
                    min(done / max(total, 1), 1.0),
                    text=f"Processed {done}/{total} chunks"
                )
            )

            get_retriever.clear()

            st.success(
                f"Indexed {info['pages']} pages "
                f"and {info['chunks']} chunks."
            )

            st.rerun()

        except Exception as exc:

            st.exception(exc)

    footer()

    st.stop()


# ---------------------------------------------------------
# LLM CONFIGURATION
# ---------------------------------------------------------

settings = get_llm_settings()

if is_configured(settings):

    st.success(
        f"LLM: {settings['provider']} / {settings['model']}"
    )

else:

    st.warning(
        "No LLM is configured. "
        "Check your local .env configuration."
    )


retriever = get_retriever(doc_id)


# Unique extraction state for the selected prospectus.
extraction_key = f"ipovision_extraction_{doc_id}"


# ---------------------------------------------------------
# MAIN TABS
# ---------------------------------------------------------

analysis_tab, qa_tab = st.tabs([

    "📑 RHP Analysis & Scoring",

    "💬 Ask the Prospectus"

])


# =========================================================
# TAB 1 — RHP EXTRACTION AND SCORING
# =========================================================

with analysis_tab:

    st.header("2. Extract information using RAG")

    st.write(
        "The system retrieves relevant prospectus passages, "
        "extracts structured information and validates page citations."
    )

    run_extraction = st.button(
        "Analyse prospectus",
        type="primary",
        disabled=not is_configured(settings)
    )

    if run_extraction:

        all_fields = {}
        group_results = {}
        group_hits = {}

        total_groups = len(EXTRACTION_FIELDS)

        progress = st.progress(
            0.0,
            text="Starting prospectus analysis..."
        )

        try:

            for index, (topic, field_specs) in enumerate(
                EXTRACTION_FIELDS.items(),
                start=1
            ):

                progress.progress(
                    (index - 1) / total_groups,
                    text=f"Extracting ({index}/{total_groups}): {topic}"
                )

                query = RETRIEVAL_QUERIES[topic]

                hits = retriever.search(
                    query,
                    k=6,
                    pool=30
                )
                group_hits[topic] = hits

                result = extract_structured_fields(
                    topic=topic,
                    field_specs=field_specs,
                    hits=hits,
                    **settings
                )

                group_results[topic] = result

                all_fields.update(
                    result["fields"]
                )

            completed_sections = []
            partial_sections = []
            failed_sections = []
            verified_count = 0
            unverified_count = 0
            missing_count = 0

            for topic, res in group_results.items():
                t_fields = res.get("fields", {})
                v_cnt = sum(1 for f in t_fields.values() if f.get("status") == "verified")
                u_cnt = sum(1 for f in t_fields.values() if f.get("status") == "unverified")
                m_cnt = sum(1 for f in t_fields.values() if f.get("status") in ("not_found", "not_generated"))
                err_cnt = sum(1 for f in t_fields.values() if f.get("status") in ("invalid_json", "generation_error"))

                verified_count += v_cnt
                unverified_count += u_cnt
                missing_count += m_cnt

                if err_cnt > 0 or (u_cnt > 0 and v_cnt == 0):
                    failed_sections.append(topic)
                elif u_cnt > 0 and v_cnt > 0:
                    partial_sections.append(topic)
                elif v_cnt > 0 or m_cnt == len(t_fields):
                    completed_sections.append(topic)
                else:
                    failed_sections.append(topic)

            extraction_summary = {
                "total_sections": total_groups,
                "completed_sections": completed_sections,
                "partial_sections": partial_sections,
                "failed_sections": failed_sections,
                "verified_fields": verified_count,
                "unverified_fields": unverified_count,
                "missing_fields": missing_count,
            }

            st.session_state[extraction_key] = {
                "fields": all_fields,
                "groups": group_results,
                "group_hits": group_hits,
                "summary": extraction_summary,
                "document_id": doc_id,
            }

            progress.progress(
                1.0,
                text="Prospectus analysis completed."
            )

        except Exception as exc:

            st.exception(exc)

    extraction = st.session_state.get(
        extraction_key
    )

    fields = {}

    # -----------------------------------------------------
    # REVIEW EXTRACTED EVIDENCE
    # -----------------------------------------------------

    if extraction:

        fields = extraction.get(
            "fields", {}
        )
        summary = extraction.get("summary", {})
        group_results = extraction.get("groups", {})
        group_hits = extraction.get("group_hits", {})

        if summary:
            st.subheader("Extraction Summary")
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Sections Attempted", summary.get("total_sections", len(EXTRACTION_FIELDS)))
            sc2.metric("Sections Completed", len(summary.get("completed_sections", [])))
            sc3.metric("Partially Completed", len(summary.get("partial_sections", [])))
            sc4.metric("Failed Sections", len(summary.get("failed_sections", [])))

            fc1, fc2, fc3 = st.columns(3)
            fc1.metric("Verified Fields", summary.get("verified_fields", 0))
            fc2.metric("Unverified Fields", summary.get("unverified_fields", 0))
            fc3.metric("Missing / Not Found", summary.get("missing_fields", 0))

            if summary.get("failed_sections") or summary.get("partial_sections") or summary.get("unverified_fields", 0) > 0:
                st.warning(
                    f"Prospectus extraction completed with items requiring review: "
                    f"{len(summary.get('completed_sections', []))} completed, "
                    f"{len(summary.get('partial_sections', []))} partially completed, "
                    f"{len(summary.get('failed_sections', []))} failed. "
                    f"Review unverified fields below."
                )
            else:
                st.success("All sections completed and all extracted fields verified.")

            failed = summary.get("failed_sections", [])
            if failed:
                with st.expander("⚠️ Inspect passages for failed sections", expanded=False):
                    for f_topic in failed:
                        st.markdown(f"### {f_topic}")
                        res = group_results.get(f_topic, {})
                        if res.get("error"):
                            st.error(f"Error: {res['error']}")
                        f_hits = group_hits.get(f_topic, [])
                        for h in f_hits:
                            st.markdown(f"**Page {h['page']}**")
                            st.write(h["text"])

        st.header("3. Review extracted information")

        st.caption(
            "Approve only after checking the quotation against "
            "the actual prospectus page."
        )

        for topic, field_specs in EXTRACTION_FIELDS.items():

            with st.expander(
                topic,
                expanded=(topic == "Financial summary")
            ):

                for field_name, field_spec in field_specs.items():

                    item = fields.get(
                        field_name,
                        {}
                    )

                    status = item.get(
                        "status",
                        "not_found"
                    )
                    validation_reason = item.get("validation_reason")

                    status_badge = {
                        "verified": '<span class="candy-badge candy-badge-success">✓ Verified</span>',
                        "unverified": '<span class="candy-badge candy-badge-warning">⚠ Unverified</span>',
                        "not_found": '<span class="candy-badge candy-badge-secondary">Not Found</span>',
                        "invalid_json": '<span class="candy-badge candy-badge-error">Invalid JSON</span>',
                        "generation_error": '<span class="candy-badge candy-badge-error">Error</span>',
                    }.get(status, '<span class="candy-badge candy-badge-secondary">Pending</span>')

                    st.markdown(
                        f"<div style='display: flex; align-items: center; justify-content: space-between; margin-top: 1.2rem; margin-bottom: 0.4rem;'>"
                        f"<h4 style='margin: 0; color: #2e1a28;'>{field_name.replace('_', ' ').title()}</h4>"
                        f"{status_badge}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    if status == "verified":

                        st.success(
                            "Source quotation verified against retrieved document excerpts."
                        )

                    elif status == "not_found":

                        st.info(
                            "Information not found in excerpts."
                        )

                    elif status == "invalid_json":

                        st.error(
                            f"Invalid JSON from model: {item.get('error', '')}"
                        )

                    elif status == "generation_error":

                        st.error(
                            f"Generation error: {item.get('error', '')}"
                        )

                    else:

                        reason_msg = f": {validation_reason}" if validation_reason else ""
                        st.warning(
                            f"Evidence could not be verified{reason_msg}"
                        )

                    st.write("Extracted value:")
                    val = item.get("value")

                    if val is None:
                        st.caption("No value extracted / Not found in excerpts")
                    elif isinstance(val, (int, float)) and not isinstance(val, bool):
                        st.markdown(f"**`{val}`** {item.get('unit', '')}")
                    elif isinstance(val, str):
                        st.markdown(val)
                    elif isinstance(val, list):
                        if all(isinstance(x, str) for x in val):
                            for x in val:
                                st.markdown(f"- {x}")
                        elif all(isinstance(x, dict) for x in val):
                            st.dataframe(val, width="stretch", hide_index=True)
                        else:
                            st.json(val)
                    elif isinstance(val, dict):
                        st.json(val)
                    else:
                        st.write(str(val))

                    if item.get("converted"):
                        st.info(
                            f"Unit conversion: {item.get('conversion_note')}. "
                            f"(Original reported: {item.get('original_value')} {item.get('original_unit')})"
                        )
                    elif item.get("unit"):
                        st.caption(
                            f"Unit: {item['unit']}"
                        )

                    if item.get("statement_type") and item.get("statement_type") != "unspecified":
                        st.caption(
                            f"Statement type: {item['statement_type'].title()}"
                        )

                    if item.get("normalization_warning"):
                        st.caption(
                            f"ℹ️ {item['normalization_warning']}"
                        )

                    st.caption(
                        "Model-reported extraction confidence: "
                        f"{item.get('confidence', 0):.0%}"
                    )

                    for evidence in item.get(
                        "evidence", []
                    ):

                        st.markdown(
                            f"<div style='background: #fdfafd; border-left: 3px solid #e040a0; padding: 8px 12px; border-radius: 0 8px 8px 0; margin-bottom: 6px; font-size: 0.88rem; color: #4a3068;'>"
                            f"<strong style='color: #a02070;'>Page {evidence['page']}</strong> — <em>\"{evidence['quote']}\"</em>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    approve_key = (
                        f"approve_{doc_id}_{field_name}"
                    )

                    approved = st.checkbox(
                        "I verified this value and approve it for scoring",
                        value=bool(
                            item.get("approved", False)
                        ),
                        key=approve_key,
                        disabled=(status != "verified")
                    )

                    item["approved"] = (
                        approved and status == "verified"
                    )

                    fields[field_name] = item

        extraction["fields"] = fields

        st.session_state[extraction_key] = extraction

    else:

        st.info(
            "Run prospectus analysis to populate extracted evidence."
        )


    # -----------------------------------------------------
    # MANUAL QUALITATIVE INPUTS
    # -----------------------------------------------------

    st.header("4. Manual business judgement")

    st.caption(
        "Subjective ratings are not automatically assigned by AI."
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        business_quality = parse_rating(
            "Business quality",
            f"business_{doc_id}"
        )

    with c2:

        management = parse_rating(
            "Management quality",
            f"management_{doc_id}"
        )

    with c3:

        litigation = parse_rating(
            "Litigation severity",
            f"litigation_{doc_id}"
        )

    with c4:

        use_of_funds = parse_rating(
            "Use of funds quality",
            f"funds_{doc_id}"
        )


    manual_inputs = {

        "business_quality_rating": business_quality,

        "management_rating": management,

        "litigation_severity": litigation,

        "use_of_funds_rating": use_of_funds,

    }


    # -----------------------------------------------------
    # FUNDAMENTAL SCORE
    # -----------------------------------------------------

    st.header("5. Fundamental score")

    fundamental_inputs, mapping_warnings = (
        fundamental_inputs_from_evidence(
            fields,
            manual_overrides=manual_inputs
        )
    )

    for warning in mapping_warnings:
        st.warning(warning)

    fundamental_result = score_fundamental(
        fundamental_inputs
    )

    display_score(
        fundamental_result,
        "Fundamental score"
    )

    if fundamental_result["score"] is not None:

        with st.expander(
            "Calculated financial metrics"
        ):

            st.json(
                fundamental_result.get(
                    "metrics", {}
                )
            )


    # -----------------------------------------------------
    # LISTING SCORE
    # -----------------------------------------------------

    st.header("6. Listing score")

    st.caption(
        "GMP, subscription and market data must come from external "
        "market sources, not be inferred from an RHP."
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        gmp = parse_number(
            "Final GMP (%)",
            f"gmp_{doc_id}"
        )

        qib = parse_number(
            "QIB subscription (times)",
            f"qib_{doc_id}"
        )

        total = parse_number(
            "Total subscription (times)",
            f"total_{doc_id}"
        )

    with col2:

        nifty = parse_number(
            "Nifty 20-day return (%)",
            f"nifty_{doc_id}"
        )

        pe_premium = parse_number(
            "IPO P/E premium to peers (%)",
            f"premium_{doc_id}"
        )

        sector = parse_rating(
            "Sector sentiment",
            f"sector_{doc_id}"
        )

    with col3:

        issue_size = parse_number(
            "Issue size (₹ crore)",
            f"size_{doc_id}"
        )


    listing_inputs = ListingInputs(

        gmp_pct=gmp,

        qib_sub=qib,

        total_sub=total,

        nifty_ret_20d=nifty,

        pe_premium_pct=pe_premium,

        sector_sentiment_rating=sector,

        issue_size_cr=issue_size,

    )

    listing_result = score_listing(
        listing_inputs
    )

    display_score(
        listing_result,
        "Listing score"
    )


# =========================================================
# TAB 2 — PROSPECTUS Q&A
# =========================================================

with qa_tab:

    st.header("Ask questions about the RHP")

    st.caption(
        "Answers are grounded in retrieved document passages. "
        "Check every page citation before relying on a statement."
    )

    preset = st.selectbox(
        "Select a checklist question",
        ["(write my own)"] + list(CHECKLIST_QUESTIONS),
        key=f"preset_{doc_id}"
    )

    default_question = CHECKLIST_QUESTIONS.get(
        preset,
        ""
    )

    question = st.text_area(
        "Your question",
        value=default_question,
        key=f"question_{doc_id}_{preset}"
    )


    if st.button(
        "Ask prospectus",
        type="primary",
        disabled=not bool(question.strip()),
        key=f"ask_{doc_id}"
    ):

        query = RETRIEVAL_QUERIES.get(
            preset
        )

        if not (
            query
            and question == CHECKLIST_QUESTIONS.get(preset)
        ):

            query = question


        with st.spinner(
            "Retrieving evidence and generating answer..."
        ):

            hits = retriever.search(
                query,
                k=8,
                pool=40
            )

            response = answer_question(
                question,
                hits,
                **settings
            )


        cited_badges = (
            " ".join(
                f'<span class="candy-badge candy-badge-tertiary">Page {p}</span>'
                for p in response.get("pages", [])
            )
            if response.get("pages")
            else '<span style="color: #907898;">None cited</span>'
        )

        st.markdown(
            f"""
            <div class="candy-card" style="margin-top: 1rem; border-color: #dcc8e0;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                <span class="candy-badge candy-badge-primary">Grounded Response</span>
                <span style="font-size: 11px; color: #7c52aa; font-weight: 600; text-transform: uppercase;">Engine: {response.get('mode', 'rag')}</span>
              </div>
              <div style="font-size: 0.96rem; line-height: 1.65; color: #2e1a28; margin-bottom: 14px;">
                {response["answer"]}
              </div>
              <div style="border-top: 1px solid #f0e6f0; padding-top: 10px; font-size: 12px; color: #7c52aa; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <strong>Cited Pages:</strong> {cited_badges}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


        if response.get("error"):

            st.warning(
                "Generation failed. Retrieved excerpts are shown instead. "
                + str(response.get("hint") or response["error"])[:350]
            )


        if not response.get("citations_ok", False):

            st.error(
                "Citation verification failed. "
                "Check the original document before relying on this answer."
            )


        with st.expander(
            "View retrieved passages"
        ):

            for hit in hits:

                st.markdown(
                    f"**Page {hit['page']}**"
                )

                st.write(
                    hit["text"]
                )


footer()
