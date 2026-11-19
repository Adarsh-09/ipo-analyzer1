import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.answer import (
    answer_question,
    error_hint,
    get_llm_settings,
    is_configured,
    extract_structured_fields,
)

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

    def test_structured_extraction_validates_source_quote(self):
        import json
        payload = {
            "fields": {
                "promoter_status": {
                    "value": "No shares pledged",
                    "unit": "",
                    "confidence": 0.95,
                    "evidence": [{
                        "page": 5,
                        "quote": "The promoters have not pledged any shares."
                    }]
                }
            }
        }
        class Fake:
            models = SimpleNamespace(
                generate_content=lambda **kw: SimpleNamespace(
                    text=json.dumps(payload)
                )
            )
        result = extract_structured_fields(
            topic="Promoter details",
            field_specs={
                "promoter_status": {
                    "type": "text",
                    "description": "Promoter pledge status."
                }
            },
            hits=HITS,
            api_key="k",
            client=Fake()
        )
        field = result["fields"]["promoter_status"]
        self.assertEqual(field["status"], "verified")
        self.assertFalse(field["approved"])
        self.assertEqual(field["evidence"][0]["page"], 5)
        self.assertTrue(result["citations_ok"])

    def test_structured_extraction_rejects_wrong_page(self):
        import json
        payload = {
            "fields": {
                "promoter_status": {
                    "value": "No shares pledged",
                    "unit": "",
                    "confidence": 0.95,
                    "evidence": [{
                        "page": 99,
                        "quote": "The promoters have not pledged any shares."
                    }]
                }
            }
        }
        class Fake:
            models = SimpleNamespace(
                generate_content=lambda **kw: SimpleNamespace(
                    text=json.dumps(payload)
                )
            )
        result = extract_structured_fields(
            topic="Promoter details",
            field_specs={
                "promoter_status": {
                    "type": "text",
                    "description": "Promoter pledge status."
                }
            },
            hits=HITS,
            api_key="k",
            client=Fake()
        )
        field = result["fields"]["promoter_status"]
        self.assertEqual(field["status"], "unverified")
        self.assertFalse(field["approved"])
        self.assertFalse(result["citations_ok"])

    def test_structured_extraction_rejects_invalid_financial_series(self):
        import json
        payload = {
            "fields": {
                "revenue": {
                    "value": [
                        {
                            "period": "FY2024",
                            "amount": "500 crore"
                        }
                    ],
                    "unit": "INR crore",
                    "confidence": 0.9,
                    "evidence": [{
                        "page": 5,
                        "quote": "The promoters have not pledged any shares."
                    }]
                }
            }
        }
        class Fake:
            models = SimpleNamespace(
                generate_content=lambda **kw: SimpleNamespace(
                    text=json.dumps(payload)
                )
            )
        result = extract_structured_fields(
            topic="Financial summary",
            field_specs={
                "revenue": {
                    "type": "series",
                    "unit": "INR crore",
                    "description": "Historical revenue."
                }
            },
            hits=HITS,
            api_key="k",
            client=Fake()
        )

        self.assertEqual(
            result["fields"]["revenue"]["status"],
            "unverified"
        )

    def test_gemini_valid_json_response(self):
        import json
        payload = {
            "statement_type": "consolidated",
            "financial_unit": "INR crore",
            "fields": {
                "revenue": {
                    "value": [{"period": "FY2023", "amount": 100.0}, {"period": "FY2024", "amount": 150.0}],
                    "unit": "INR crore",
                    "confidence": 0.95,
                    "evidence": [{"page": 5, "quote": "The promoters have not pledged any shares."}]
                }
            }
        }
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload))))
        res = extract_structured_fields("Financial summary", {"revenue": {"type": "series", "unit": "INR crore"}}, HITS, client=client, api_key="k")
        self.assertEqual(res["fields"]["revenue"]["status"], "verified")
        self.assertFalse(res["fields"]["revenue"]["approved"])
        self.assertEqual(res["fields"]["revenue"]["statement_type"], "consolidated")

    def test_gemini_prose_response_triggers_repair(self):
        import json
        prose = "The company is a market leader in financial technology services."
        repaired = {
            "fields": {
                "business_overview": {
                    "value": "Market leader in financial technology services.",
                    "unit": "",
                    "confidence": 0.9,
                    "evidence": [{"page": 5, "quote": "The promoters have not pledged any shares."}]
                }
            }
        }
        calls = []
        def fake_generate(**kw):
            calls.append(kw)
            if len(calls) == 1:
                return SimpleNamespace(text=prose)
            return SimpleNamespace(text=json.dumps(repaired))
        client = SimpleNamespace(models=SimpleNamespace(generate_content=fake_generate))
        res = extract_structured_fields("Business overview", {"business_overview": {"type": "text"}}, HITS, client=client, api_key="k")
        self.assertEqual(len(calls), 2)
        self.assertEqual(res["fields"]["business_overview"]["status"], "verified")
        self.assertEqual(res["fields"]["business_overview"]["value"], "Market leader in financial technology services.")

    def test_invalid_json_after_repair_marked_safely(self):
        prose = "The company reported strong results but cannot provide json."
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=prose)))
        res = extract_structured_fields("Business overview", {"business_overview": {"type": "text"}}, HITS, client=client, api_key="k")
        field = res["fields"]["business_overview"]
        self.assertEqual(field["status"], "invalid_json")
        self.assertIsNone(field["value"])
        self.assertIn("invalid JSON", field["error"])
        self.assertEqual(field["validation_reason"], "Invalid JSON response")
        self.assertEqual(res["pages"], [5, 9])

    def test_gemini_api_error_stored_outside_value(self):
        class BrokenClient:
            models = SimpleNamespace(generate_content=lambda **kw: (_ for _ in ()).throw(RuntimeError("API quota exceeded")))
        res = extract_structured_fields("Business overview", {"business_overview": {"type": "text"}}, HITS, client=BrokenClient(), api_key="k")
        field = res["fields"]["business_overview"]
        self.assertEqual(field["status"], "generation_error")
        self.assertIsNone(field["value"])
        self.assertIn("quota exceeded", field["error"])
        self.assertIn("quota exceeded", field["validation_reason"])
        self.assertEqual(res["pages"], [5, 9])

    def test_invalid_response_schema_retries_and_handles(self):
        import json
        bad_schema = {"not_fields": 123}
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(bad_schema))))
        res = extract_structured_fields("Business overview", {"business_overview": {"type": "text"}}, HITS, client=client, api_key="k")
        field = res["fields"]["business_overview"]
        self.assertEqual(field["status"], "invalid_json")
        self.assertIsNone(field["value"])

    def test_missing_evidence_marked_unverified(self):
        import json
        payload = {
            "fields": {
                "business_overview": {
                    "value": "Company Overview",
                    "evidence": []
                }
            }
        }
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload))))
        res = extract_structured_fields("Business overview", {"business_overview": {"type": "text"}}, HITS, client=client, api_key="k")
        field = res["fields"]["business_overview"]
        self.assertEqual(field["status"], "unverified")
        self.assertEqual(field["validation_reason"], "Missing evidence")

    def test_fabricated_quotation_marked_unverified(self):
        import json
        payload = {
            "fields": {
                "business_overview": {
                    "value": "Company Overview",
                    "evidence": [{"page": 5, "quote": "Fabricated quote that does not exist in document passage."}]
                }
            }
        }
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload))))
        res = extract_structured_fields("Business overview", {"business_overview": {"type": "text"}}, HITS, client=client, api_key="k")
        field = res["fields"]["business_overview"]
        self.assertEqual(field["status"], "unverified")
        self.assertEqual(field["validation_reason"], "Quotation not found")

    def test_evidence_supporting_every_list_item(self):
        import json
        hits = [{"page": 1, "text": "Risk 1: High dependence on key suppliers. Risk 2: Foreign exchange volatility."}]
        payload_all = {
            "fields": {
                "top_risk_factors": {
                    "value": ["High dependence on key suppliers", "Foreign exchange volatility"],
                    "evidence": [
                        {"page": 1, "quote": "High dependence on key suppliers"},
                        {"page": 1, "quote": "Foreign exchange volatility"}
                    ]
                }
            }
        }
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload_all))))
        res = extract_structured_fields("Top risk factors", {"top_risk_factors": {"type": "list"}}, hits, client=client, api_key="k")
        self.assertEqual(res["fields"]["top_risk_factors"]["status"], "verified")

        payload_partial = {
            "fields": {
                "top_risk_factors": {
                    "value": ["High dependence on key suppliers", "Regulatory penalty risk with no citation"],
                    "evidence": [{"page": 1, "quote": "High dependence on key suppliers"}]
                }
            }
        }
        client2 = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload_partial))))
        res2 = extract_structured_fields("Top risk factors", {"top_risk_factors": {"type": "list"}}, hits, client=client2, api_key="k")
        self.assertEqual(res2["fields"]["top_risk_factors"]["status"], "unverified")
        self.assertEqual(res2["fields"]["top_risk_factors"]["validation_reason"], "Incomplete evidence")

    def test_financial_series_descending_order_normalized(self):
        import json
        payload = {
            "fields": {
                "revenue": {
                    "value": [
                        {"period": "FY2025", "amount": 300.0},
                        {"period": "FY2024", "amount": 200.0},
                        {"period": "FY2023", "amount": 100.0}
                    ],
                    "unit": "INR crore",
                    "evidence": [{"page": 5, "quote": "The promoters have not pledged any shares."}]
                }
            }
        }
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload))))
        res = extract_structured_fields("Financial summary", {"revenue": {"type": "series", "unit": "INR crore"}}, HITS, client=client, api_key="k")
        field = res["fields"]["revenue"]
        self.assertEqual(field["status"], "verified")
        self.assertEqual([r["period"] for r in field["value"]], ["FY2023", "FY2024", "FY2025"])
        self.assertEqual([r["amount"] for r in field["value"]], [100.0, 200.0, 300.0])
        self.assertIsNotNone(field["normalization_warning"])
        self.assertIn("newest-to-oldest", field["normalization_warning"])

    def test_duplicate_financial_periods_rejected(self):
        import json
        payload = {
            "fields": {
                "revenue": {
                    "value": [
                        {"period": "FY2024", "amount": 200.0},
                        {"period": "FY2024", "amount": 250.0}
                    ],
                    "unit": "INR crore",
                    "evidence": [{"page": 5, "quote": "The promoters have not pledged any shares."}]
                }
            }
        }
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload))))
        res = extract_structured_fields("Financial summary", {"revenue": {"type": "series", "unit": "INR crore"}}, HITS, client=client, api_key="k")
        field = res["fields"]["revenue"]
        self.assertEqual(field["status"], "unverified")
        self.assertEqual(field["validation_reason"], "Duplicate financial periods")

    def test_revenue_pat_period_mismatch_and_approval_exclusion(self):
        from src.fundamental_analysis.scoring import fundamental_inputs_from_evidence
        fields = {
            "revenue": {
                "status": "verified",
                "approved": True,
                "value": [{"period": "FY2023", "amount": 100.0}, {"period": "FY2024", "amount": 200.0}]
            },
            "pat": {
                "status": "verified",
                "approved": True,
                "value": [{"period": "FY2022", "amount": 10.0}, {"period": "FY2023", "amount": 20.0}]
            }
        }
        inp, warnings = fundamental_inputs_from_evidence(fields)
        self.assertIsNone(inp.revenue)
        self.assertIsNone(inp.pat)
        self.assertTrue(any("do not match" in w for w in warnings))

        fields["revenue"]["approved"] = False
        fields["pat"]["approved"] = False
        inp_unapp, _ = fundamental_inputs_from_evidence(fields)
        self.assertIsNone(inp_unapp.revenue)
        self.assertIsNone(inp_unapp.pat)

    def test_unit_conversion_from_inr_million_to_crore(self):
        import json
        payload = {
            "statement_type": "consolidated",
            "financial_unit": "INR million",
            "fields": {
                "revenue": {
                    "value": [{"period": "FY2024", "amount": 13423.7}],
                    "unit": "INR million",
                    "evidence": [{"page": 5, "quote": "The promoters have not pledged any shares."}]
                }
            }
        }
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload))))
        res = extract_structured_fields("Financial summary", {"revenue": {"type": "series", "unit": "INR crore"}}, HITS, client=client, api_key="k")
        field = res["fields"]["revenue"]
        self.assertEqual(field["status"], "verified")
        self.assertTrue(field["converted"])
        self.assertEqual(field["unit"], "INR crore")
        self.assertEqual(field["original_unit"], "INR million")
        self.assertAlmostEqual(field["value"][0]["amount"], 1342.37)
        self.assertIn("divided by 10", field["conversion_note"])

    def test_missing_financial_unit_not_silently_converted(self):
        import json
        payload = {
            "fields": {
                "revenue": {
                    "value": [{"period": "FY2024", "amount": 500.0}],
                    "unit": "",
                    "evidence": [{"page": 5, "quote": "The promoters have not pledged any shares."}]
                }
            }
        }
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload))))
        res = extract_structured_fields("Financial summary", {"revenue": {"type": "series"}}, HITS, client=client, api_key="k")
        field = res["fields"]["revenue"]
        self.assertFalse(field["converted"])
        self.assertEqual(field["original_unit"], "")

if __name__ == "__main__":
    unittest.main()