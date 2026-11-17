"""Answer generation with page citations, provider-agnostic, plus the checks that keep it honest."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

SYSTEM_PROMPT = (
    "You answer questions about an Indian IPO prospectus (RHP or DRHP). Use ONLY the numbered excerpts provided. "
    "After each claim cite the page like [p. 23]. If the excerpts do not contain the answer, reply exactly: "
    "'The retrieved excerpts do not contain this.' Quote figures exactly as written. Do not give investment advice.")
NOT_FOUND = "The retrieved excerpts do not contain this."
NO_MODEL = "No language model is configured, so these are the most relevant passages, not a written answer:"
CALL_FAILED = "The language model could not be used (see the error), so these are the most relevant passages, not a written answer:"
DEFAULT_MODELS = {"gemini": "gemini-3.5-flash", "anthropic": "claude-haiku-5-5", "ollama": None}
_CITE = re.compile(r"\[pp?\.?\s*(\d+)(?:\s*[-\u2013]\s*(\d+))?\]", re.I)


def get_llm_settings(load_env: bool = True) -> Dict:
    """Provider settings from the environment or a local .env. LLM_PROVIDER wins; otherwise the first key found."""
    if load_env:
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        except Exception:
            pass
    env = os.environ
    gem = env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
    ant = env.get("ANTHROPIC_API_KEY")
    provider = (env.get("LLM_PROVIDER") or "").strip().lower() or (
        "gemini" if gem else "anthropic" if ant else "ollama" if env.get("OLLAMA_MODEL") else None)
    if provider == "gemini":
        return {"provider": provider, "api_key": gem, "model": env.get("GEMINI_MODEL", DEFAULT_MODELS["gemini"]), "host": None}
    if provider == "anthropic":
        return {"provider": provider, "api_key": ant, "model": env.get("ANTHROPIC_MODEL", DEFAULT_MODELS["anthropic"]), "host": None}
    if provider == "ollama":
        return {"provider": provider, "api_key": None, "model": env.get("OLLAMA_MODEL"),
                "host": env.get("OLLAMA_HOST", "http://localhost:11434")}
    return {"provider": provider, "api_key": None, "model": None, "host": None}   # None, or an unknown name that surfaces as an error


def is_configured(settings: Dict) -> bool:
    p = settings.get("provider")
    if p in ("gemini", "anthropic"):
        return bool(settings.get("api_key"))
    if p == "ollama":
        return bool(settings.get("model"))
    return False


def error_hint(message: str) -> Optional[str]:
    m = (message or "").lower()
    if "permission_denied" in m or "billing" in m or "free tier" in m:
        return ("This Google project cannot use the Gemini API without billing. Enable billing in Google AI Studio, "
                "or set LLM_PROVIDER to anthropic or ollama in .env.")
    if "api key" in m or "unauthorized" in m or "401" in m:
        return "The API key was rejected. Check the key in .env."
    if "not found" in m and "model" in m:
        return "The model name was not found. Set GEMINI_MODEL, ANTHROPIC_MODEL or OLLAMA_MODEL to one your account can use."
    if "connection" in m or "refused" in m:
        return "Could not connect. For Ollama, start the Ollama app and check OLLAMA_HOST."
    return None


def generate_text(provider, system: str, prompt: str, api_key=None, model=None, host=None, client=None) -> str:
    if provider == "gemini":
        if client is None:
            from google import genai
            client = genai.Client(api_key=api_key)
        kwargs = {"model": model or DEFAULT_MODELS["gemini"], "contents": prompt}
        try:
            from google.genai import types
            kwargs["config"] = types.GenerateContentConfig(system_instruction=system, temperature=0.1, max_output_tokens=900)
        except ImportError:
            kwargs["contents"] = system + "\n\n" + prompt
        return (client.models.generate_content(**kwargs).text or "").strip()
    if provider == "anthropic":
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(model=model or DEFAULT_MODELS["anthropic"], max_tokens=900, system=system,
                                      messages=[{"role": "user", "content": prompt}])
        return "".join(getattr(b, "text", "") for b in resp.content).strip()
    if provider == "ollama":
        import requests
        r = requests.post(f"{(host or 'http://localhost:11434').rstrip('/')}/api/chat", timeout=300,
                          json={"model": model, "stream": False, "options": {"temperature": 0.1},
                                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
        r.raise_for_status()
        return (r.json()["message"]["content"] or "").strip()
    raise ValueError(f"Unknown provider: {provider!r}")


def build_prompt(question: str, hits: List[Dict]) -> str:
    excerpts = "\n\n".join(f"[p. {h['page']}] {h['text']}" for h in hits)
    return (f"EXCERPTS:\n\n{excerpts}\n\nQUESTION: {question}\n\n"
            "Answer using only the excerpts, citing pages like [p. 12].")


def cited_pages(text: str) -> Set[int]:
    pages: Set[int] = set()
    for a, b in _CITE.findall(text or ""):
        lo = int(a)
        hi = int(b) if b else lo
        pages.update(range(lo, hi + 1) if 0 <= hi - lo <= 10 else {lo, hi})
    return pages


def check_citations(answer: str, hits: List[Dict]) -> Dict:
    cited, allowed = cited_pages(answer), {h["page"] for h in hits}
    return {"cited": sorted(cited), "unsupported": sorted(cited - allowed), "has_citation": bool(cited)}


def retrieval_only_answer(hits: List[Dict], reason: str = NO_MODEL, n: int = 5, width: int = 300) -> str:
    lines = [reason, ""]
    for h in hits[:n]:
        t = h["text"] if len(h["text"]) <= width else h["text"][:width].rsplit(" ", 1)[0] + "..."
        lines.append(f"- [p. {h['page']}] {t}")
    return "\n".join(lines)


def answer_question(question: str, hits: List[Dict], api_key: Optional[str] = None, model: Optional[str] = None,
                    client=None, provider: Optional[str] = "gemini", host: Optional[str] = None) -> Dict:
    base = {"pages": sorted({h["page"] for h in hits}), "citations_ok": True, "unsupported_pages": [],
            "error": None, "hint": None, "provider": provider}
    if not hits:
        return {**base, "mode": "no-hits", "answer": NOT_FOUND}
    unknown = provider is not None and provider not in DEFAULT_MODELS            # a typo must surface as an error
    if client is None and not unknown and not is_configured({"provider": provider, "api_key": api_key, "model": model}):
        return {**base, "mode": "retrieval-only", "answer": retrieval_only_answer(hits, NO_MODEL)}
    try:
        text = generate_text(provider, SYSTEM_PROMPT, build_prompt(question, hits),
                             api_key=api_key, model=model, host=host, client=client)
    except Exception as exc:          # billing, quota, wrong model name, network, missing SDK ...
        msg = str(exc)
        return {**base, "mode": "retrieval-only", "answer": retrieval_only_answer(hits, CALL_FAILED),
                "error": msg, "hint": error_hint(msg)}
    chk = check_citations(text, hits)
    ok = not chk["unsupported"] and (chk["has_citation"] or NOT_FOUND in text)
    return {**base, "mode": provider, "answer": text, "citations_ok": ok, "unsupported_pages": chk["unsupported"]}