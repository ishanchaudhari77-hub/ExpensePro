import unittest


APP_IMPORT_ERROR = None
try:
    import app
except Exception as exc:  # pragma: no cover - environment dependent import guard
    app = None
    APP_IMPORT_ERROR = exc


@unittest.skipIf(app is None, f"app import failed: {APP_IMPORT_ERROR}")
class BudgetSnapshotTests(unittest.TestCase):
    def test_rollover_with_positive_carry(self):
        budget_limits = {"2026-01": 1000.0, "2026-02": 1000.0, "2026-03": 1000.0}
        expenses = {"2026-01": 800.0, "2026-02": 700.0, "2026-03": 600.0}
        prefs = {"rollover_enabled": True, "carry_forward_deficit": True}

        snapshot = app._compute_budget_snapshot("2026-03", budget_limits, expenses, prefs)

        self.assertAlmostEqual(snapshot["carry_in"], 500.0)
        self.assertAlmostEqual(snapshot["effective_budget"], 1500.0)
        self.assertAlmostEqual(snapshot["remaining"], 900.0)

    def test_rollover_without_deficit_carry(self):
        budget_limits = {"2026-01": 1000.0, "2026-02": 1000.0}
        expenses = {"2026-01": 1400.0, "2026-02": 900.0}
        prefs = {"rollover_enabled": True, "carry_forward_deficit": False}

        snapshot = app._compute_budget_snapshot("2026-02", budget_limits, expenses, prefs)

        self.assertAlmostEqual(snapshot["carry_in"], 0.0)
        self.assertAlmostEqual(snapshot["effective_budget"], 1000.0)
        self.assertAlmostEqual(snapshot["remaining"], 100.0)

    def test_rollover_with_deficit_carry(self):
        budget_limits = {"2026-01": 1000.0, "2026-02": 1000.0}
        expenses = {"2026-01": 1400.0, "2026-02": 900.0}
        prefs = {"rollover_enabled": True, "carry_forward_deficit": True}

        snapshot = app._compute_budget_snapshot("2026-02", budget_limits, expenses, prefs)

        self.assertAlmostEqual(snapshot["carry_in"], -400.0)
        self.assertAlmostEqual(snapshot["effective_budget"], 600.0)
        self.assertAlmostEqual(snapshot["remaining"], -300.0)


@unittest.skipIf(app is None, f"app import failed: {APP_IMPORT_ERROR}")
class AnomalyTests(unittest.TestCase):
    def test_overall_and_category_anomaly_detected(self):
        expenses = [
            {"date": "2025-12-05", "amount": 1000.0, "category": "Food"},
            {"date": "2026-01-10", "amount": 1000.0, "category": "Food"},
            {"date": "2026-02-08", "amount": 1000.0, "category": "Food"},
            {"date": "2026-03-11", "amount": 1600.0, "category": "Food"},
            {"date": "2026-03-16", "amount": 200.0, "category": "Travel"},
        ]

        summary = app._analyze_spending_anomalies(
            expenses,
            "2026-03",
            threshold_percent=40.0,
            min_amount_delta=100.0,
            baseline_months_count=3,
        )

        self.assertTrue(summary["triggered"])
        self.assertIsNotNone(summary["overall"])
        self.assertGreaterEqual(summary["overall"]["percent"], 40.0)
        self.assertTrue(any(item["category"] == "Food" for item in summary["categories"]))

    def test_no_anomaly_under_threshold(self):
        expenses = [
            {"date": "2025-12-05", "amount": 1000.0, "category": "Food"},
            {"date": "2026-01-10", "amount": 1000.0, "category": "Food"},
            {"date": "2026-02-08", "amount": 1000.0, "category": "Food"},
            {"date": "2026-03-11", "amount": 1200.0, "category": "Food"},
        ]

        summary = app._analyze_spending_anomalies(
            expenses,
            "2026-03",
            threshold_percent=40.0,
            min_amount_delta=100.0,
            baseline_months_count=3,
        )

        self.assertFalse(summary["triggered"])
        self.assertIsNone(summary["overall"])
        self.assertEqual(summary["categories"], [])


@unittest.skipIf(app is None, f"app import failed: {APP_IMPORT_ERROR}")
class MonthShiftTests(unittest.TestCase):
    def test_shift_month_key(self):
        self.assertEqual(app._shift_month_key("2026-01", -1), "2025-12")
        self.assertEqual(app._shift_month_key("2026-12", 1), "2027-01")


if __name__ == "__main__":
    unittest.main()
