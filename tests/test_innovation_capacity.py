import unittest

from innovation_capacity import DIMENSIONS, build_innovation_capacity_report, capacity_metrics


class InnovationCapacityTests(unittest.TestCase):
    def test_metrics_are_bounded_and_ranked(self):
        data = {
            "dimensions": {
                key: {"maturity": 3, "evidence": 2, "notes": "Documented practice."}
                for key in DIMENSIONS
            }
        }
        metrics = capacity_metrics(data)
        self.assertAlmostEqual(metrics["overall"], 72.9, places=1)
        self.assertEqual(metrics["confidence"], 67)
        self.assertEqual(metrics["band"], "Established but uneven")
        self.assertEqual(len(metrics["rows"]), 8)

    def test_missing_data_produces_early_band(self):
        metrics = capacity_metrics({})
        self.assertEqual(metrics["overall"], 0.0)
        self.assertEqual(metrics["band"], "Early or fragile capacity")
        self.assertTrue(metrics["warnings"])

    def test_report_includes_case_and_actions(self):
        data = {"dimensions": {"strategy": {"maturity": 2, "evidence": 1, "notes": "Draft plan."}}}
        title, body = build_innovation_capacity_report(data, "VoltCo", "GreenTech")
        self.assertEqual(title, "Innovation Capacity Report — VoltCo")
        self.assertIn("90-Day Action Plan", body)
        self.assertIn("Innovation strategy", body)
        self.assertIn("Advisory only", body)


if __name__ == "__main__":
    unittest.main()
