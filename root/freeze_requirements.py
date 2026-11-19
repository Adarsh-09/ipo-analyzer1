"""Write requirements.txt (and requirements-rag.txt) with the exact versions installed in this environment."""
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    "Data and numerics": ["numpy", "pandas", "scipy", "scikit-learn", "joblib"],
    "Data collection and parsing": ["requests", "beautifulsoup4", "lxml", "html5lib", "openpyxl",
                                    "PyYAML", "python-dotenv", "yfinance"],
    "Charts and app": ["matplotlib", "plotly", "streamlit"],
    "Testing": ["pytest"],
    "Notebooks (optional)": ["ipykernel", "jupyterlab", "notebook"],
}
RAG = ["PyMuPDF", "rank-bm25", "sentence-transformers", "chromadb", "google-genai"]


def pin(name):
    try:
        return f"{name}=={metadata.version(name)}"
    except metadata.PackageNotFoundError:
        return None


py = sys.version.split()[0]
lines, missing = [f"# IPOVision requirements, pinned from this environment (Python {py})", ""], []
for title, names in GROUPS.items():
    found = [p for p in map(pin, names) if p]
    missing += [n for n in names if pin(n) is None]
    if found:
        lines += [f"# {title}", *found, ""]
(ROOT / "requirements.txt").write_text("\n".join(lines), encoding="utf-8")

rag = [p for p in map(pin, RAG) if p]
if rag:
    (ROOT / "requirements-rag.txt").write_text(
        "\n".join([f"# Phase 5 (prospectus Q&A) requirements, pinned (Python {py})", "", *rag, ""]), encoding="utf-8")

print("\n".join(lines))
print("Not installed (fine unless the code needs them):", ", ".join(missing) or "none")
print("RAG packages found:", ", ".join(rag) or "none (install them when Phase 5 starts)")