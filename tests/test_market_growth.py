import unittest

from market_growth import (
    build_market_growth_report,
    calculate_cagr,
    evidence_strength,
    market_metrics,
    validate_market_funnel,
)


class MarketGrowthTests(unittest.TestCase):
    def test_cagr(self):
        self.assertAlmostEqual(calculate_cagr(100, 121, 2), 10.0, places=6)

    def test_cagr_requires_positive_values_and_period(self):
        self.assertIsNone(calculate_cagr(0, 100, 2))
        self.assertIsNone(calculate_cagr(100, 120, 0))

    def test_market_funnel_warnings(self):
        warnings = validate_market_funnel(100, 120, 130)
        self.assertEqual(len(warnings), 2)
        self.assertIn("SAM is greater than TAM", warnings[0])

    def test_evidence_score_is_transparent_and_capped(self):
        data = {
            "evidence_checks": [
                "dated_sources",
                "customer_validation",
                "competitor_evidence",
                "pricing_evidence",
                "partner_evidence",
            ],
            "sources": "Source A (2025)\nSource B (2026)",
            "assumptions": "Projection remains subject to customer adoption.",
        }
        score, band, present = evidence_strength(data)
        self.assertEqual(score, 100)
        self.assertTrue(band.startswith("GREEN"))
        self.assertGreaterEqual(len(present), 7)

    def test_metrics_and_report(self):
        data = {
            "currency": "EUR",
            "start_year": 2026,
            "end_year": 2029,
            "start_value": 1_000_000,
            "end_value": 1_331_000,
            "tam": 10_000_000,
            "sam": 4_000_000,
            "som": 500_000,
            "figure_status": "Internal working estimate",
            "customer_segments": "European SMEs",
            "evidence_checks": [],
        }
        metrics = market_metrics(data)
        self.assertAlmostEqual(metrics["cagr"], 10.0, places=5)
        self.assertEqual(metrics["warnings"], [])
        title, body = build_market_growth_report(data, "VoltCo", "Energy")
        self.assertEqual(title, "Market Growth Report — VoltCo")
        self.assertIn("Calculated CAGR: 10.0%", body)
        self.assertIn("Internal working estimate", body)
        self.assertIn("not legal, financial", body.lower())


if __name__ == "__main__":
    unittest.main()
