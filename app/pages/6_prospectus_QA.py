import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import streamlit as st

from app.components.common import footer
from src.rag.answer import answer_question, get_llm_settings, is_configured
from src.rag.index import RAG_DIR, build_index, doc_id_from_path, index_exists
from src.rag.questions import CHECKLIST_QUESTIONS, RETRIEVAL_QUERIES
from src.rag.retrieve import HybridRetriever

st.set_page_config(page_title="Prospectus Q&A - IPOVision", page_icon="📈", layout="wide")
st.title("Ask the prospectus")
st.caption("Questions are answered only from passages retrieved from the PDF, with page citations. "
           "Always check the cited page. This is not investment advice.")
PDF_DIR = RAG_DIR / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)


@st.cache_resource(show_spinner="Loading the embedding model...")
def get_embedder():
    from src.rag.embeddings import default_embedder
    return default_embedder()


@st.cache_resource(show_spinner=False)
def get_retriever(doc_id):
    return HybridRetriever(doc_id, get_embedder())


settings = get_llm_settings()
if is_configured(settings):
    where = "locally" if settings["provider"] == "ollama" else "to " + settings["provider"]
    st.success(f"Language model: {settings['provider']} ({settings['model']}). Retrieved excerpts are sent {where}.")
else:
    st.info("No language model configured, so the page shows the most relevant passages with page numbers. "
            "Set a provider in `.env` (see the project README) for written answers.")

up = st.file_uploader("Upload an RHP/DRHP PDF (text PDF, not a scan)", type="pdf")
if up is not None:
    (PDF_DIR / up.name).write_bytes(up.getbuffer())
pdfs = sorted(PDF_DIR.glob("*.pdf"))
if not pdfs:
    st.info(f"Upload a prospectus above, or put PDFs in `{PDF_DIR}`.")
    footer()
    st.stop()

choice = st.selectbox("Prospectus", pdfs, format_func=lambda p: p.name)
doc_id = doc_id_from_path(choice)
if not index_exists(doc_id):
    st.warning("This document is not indexed yet. Indexing a full RHP takes a few minutes on CPU.")
    if st.button("Build index"):
        bar = st.progress(0.0, text="Embedding passages...")
        try:
            info = build_index(choice, get_embedder(), doc_id=doc_id,
                               progress=lambda d, t: bar.progress(d / t, text=f"Embedded {d} of {t} passages"))
        except ValueError as exc:
            st.error(str(exc))
        else:
            get_retriever.clear()
            st.success(f"Indexed {info['pages']} pages into {info['chunks']} passages.")
            st.rerun()
    footer()
    st.stop()

preset = st.selectbox("Checklist question", ["(write my own)"] + list(CHECKLIST_QUESTIONS))
question = st.text_area("Question", value=CHECKLIST_QUESTIONS.get(preset, ""), key=f"q_{preset}")
if st.button("Ask", type="primary") and question.strip():
    query = RETRIEVAL_QUERIES.get(preset) if question == CHECKLIST_QUESTIONS.get(preset) else question
    hits = get_retriever(doc_id).search(query, k=8)
    res = answer_question(question, hits, **settings)
    st.markdown(res["answer"])
    st.caption(f"Mode: {res['mode']} | pages retrieved: {', '.join(map(str, res['pages'])) or 'none'}")
    if res["error"]:
        st.warning(f"The language model call failed, so passages are shown instead. {res['hint'] or res['error'][:300]}")
    if not res["citations_ok"]:
        st.error("Citation check failed: the answer cites pages that were not retrieved, or cites nothing. "
                 "Do not rely on it. Unsupported pages: " + (", ".join(map(str, res["unsupported_pages"])) or "none"))
    with st.expander("Retrieved passages"):
        for h in hits:
            st.markdown(f"**p. {h['page']}** (dense rank {h['dense_rank']}, keyword rank {h['bm25_rank']})")
            st.write(h["text"])
footer()