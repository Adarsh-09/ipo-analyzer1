import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.answer import answer_question, error_hint, get_llm_settings, is_configured

HITS = [{"page": 5, "text": "The promoters have not pledged any shares."}, {"page": 9, "text": "Other text."}]


class TestProviders(unittest.TestCase):
    def test_settings_autodetect_and_override(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(get_llm_settings(load_env=False)["provider"])
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "k"}, clear=True):
            s = get_llm_settings(load_env=False)
            self.assertEqual((s["provider"], s["api_key"]), ("gemini", "k")); self.assertTrue(is_configured(s))
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "a"}, clear=True):
            self.assertEqual(get_llm_settings(load_env=False)["provider"], "anthropic")
        with mock.patch.dict(os.environ, {"OLLAMA_MODEL": "llama3.1:8b"}, clear=True):
            s = get_llm_settings(load_env=False)
            self.assertEqual((s["provider"], s["host"]), ("ollama", "http://localhost:11434"))
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "k", "ANTHROPIC_API_KEY": "a", "LLM_PROVIDER": "anthropic"}, clear=True):
            self.assertEqual(get_llm_settings(load_env=False)["provider"], "anthropic")

    def test_anthropic_dispatch(self):
        class Fake:
            messages = SimpleNamespace(create=lambda **kw: SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Nothing pledged [p. 5].")]))
        r = answer_question("pledge?", HITS, api_key="a", provider="anthropic", client=Fake())
        self.assertEqual((r["mode"], r["citations_ok"]), ("anthropic", True))

    def test_ollama_dispatch_uses_the_configured_host(self):
        resp = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"message": {"content": "None pledged [p. 5]."}})
        with mock.patch("requests.post", return_value=resp) as post:
            r = answer_question("pledge?", HITS, provider="ollama", model="llama3.1:8b", host="http://box:1234")
        self.assertEqual(r["mode"], "ollama")
        self.assertIn("http://box:1234/api/chat", post.call_args.args[0])

    def test_honest_fallback_messages(self):
        none = answer_question("q", HITS, api_key=None)
        self.assertIn("No language model is configured", none["answer"])

        class Denied:
            models = SimpleNamespace(generate_content=lambda **kw: (_ for _ in ()).throw(
                RuntimeError("403 PERMISSION_DENIED: free tier is not available")))
        failed = answer_question("q", HITS, api_key="k", client=Denied())
        self.assertEqual(failed["mode"], "retrieval-only")
        self.assertIn("could not be used", failed["answer"]); self.assertNotIn("No language model is configured", failed["answer"])
        self.assertIn("billing", failed["hint"])
        bad = answer_question("q", HITS, api_key="k", provider="nope")
        self.assertIn("Unknown provider", bad["error"])

    def test_error_hints(self):
        self.assertIn("billing", error_hint("PERMISSION_DENIED"))
        self.assertIn("key", error_hint("Invalid API key"))
        self.assertIsNone(error_hint("something unrelated"))


if __name__ == "__main__":
    unittest.main()