import unittest

from src.rag.structured_extract import (
    build_field_result,
    validate_evidence,
)

from src.fundamental_analysis.evidence_mapper import (
    to_fundamental_inputs,
)


class TestStructuredExtraction(unittest.TestCase):

    def setUp(self):

        self.source = (
            "Revenue from operations for FY2024 "
            "was INR 500 crore."
        )

        self.evidence = [{
            "page": 10,
            "quote": (
                "Revenue from operations for FY2024 "
                "was INR 500 crore."
            )
        }]


    def test_exact_source_quote_is_verified(self):

        evidence = validate_evidence(
            self.evidence,
            {10: self.source}
        )

        self.assertEqual(len(evidence), 1)


    def test_wrong_page_is_rejected(self):

        evidence = validate_evidence(
            [{
                "page": 99,
                "quote": self.source
            }],
            {10: self.source}
        )

        self.assertEqual(evidence, [])


    def test_unverified_value_is_not_approved(self):

        result = build_field_result(
            "revenue",
            {
                "value": [
                    {
                        "period": "FY2024",
                        "amount": 500
                    }
                ],
                "evidence": [{
                    "page": 10,
                    "quote": "Made up quotation from another source."
                }],
                "confidence": 0.95
            },
            {10: self.source}
        )

        self.assertEqual(result["status"], "unverified")
        self.assertFalse(result["approved"])


    def test_verified_field_starts_unapproved(self):

        result = build_field_result(
            "revenue",
            {
                "value": [
                    {
                        "period": "FY2024",
                        "amount": 500
                    }
                ],
                "evidence": self.evidence,
                "confidence": 0.95
            },
            {10: self.source}
        )

        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["approved"])


    def test_unapproved_value_never_enters_scoring(self):

        fields = {
            "revenue": {
                "status": "verified",
                "approved": False,
                "value": [
                    {
                        "period": "FY2023",
                        "amount": 300
                    },
                    {
                        "period": "FY2024",
                        "amount": 500
                    }
                ]
            }
        }

        inputs = to_fundamental_inputs(fields)

        self.assertIsNone(inputs.revenue)


    def test_approved_values_enter_scoring(self):

        fields = {
            "revenue": {
                "status": "verified",
                "approved": True,
                "value": [
                    {
                        "period": "FY2023",
                        "amount": 300
                    },
                    {
                        "period": "FY2024",
                        "amount": 500
                    }
                ]
            },
            "pat": {
                "status": "verified",
                "approved": True,
                "value": [
                    {
                        "period": "FY2023",
                        "amount": 20
                    },
                    {
                        "period": "FY2024",
                        "amount": 40
                    }
                ]
            }
        }

        inputs = to_fundamental_inputs(fields)

        self.assertEqual(
            list(inputs.revenue),
            [300, 500]
        )

        self.assertEqual(
            list(inputs.pat),
            [20, 40]
        )


    def test_ebitda_margin_can_be_derived(self):

        fields = {
            "revenue": {
                "status": "verified",
                "approved": True,
                "value": [
                    {"period": "FY2024", "amount": 500}
                ]
            },
            "ebitda": {
                "status": "verified",
                "approved": True,
                "value": [
                    {"period": "FY2024", "amount": 100}
                ]
            }
        }

        inputs = to_fundamental_inputs(fields)

        self.assertAlmostEqual(
            inputs.ebitda_margin_pct,
            20.0
        )


if __name__ == "__main__":
    unittest.main()