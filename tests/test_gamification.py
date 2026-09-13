import unittest
from datetime import date


APP_IMPORT_ERROR = None
try:
    import app
except Exception as exc:  # pragma: no cover - environment dependent import guard
    app = None
    APP_IMPORT_ERROR = exc


@unittest.skipIf(app is None, f"app import failed: {APP_IMPORT_ERROR}")
class GamificationProgressTests(unittest.TestCase):
    def test_level_progress_formula(self):
        base = app._derive_level_progress(0)
        self.assertEqual(base["level"], 1)
        self.assertEqual(base["xp_in_level"], 0)
        self.assertEqual(base["xp_needed"], 100)

        level_two = app._derive_level_progress(100)
        self.assertEqual(level_two["level"], 2)
        self.assertEqual(level_two["xp_in_level"], 0)
        self.assertEqual(level_two["xp_needed"], 200)

        level_three_partial = app._derive_level_progress(350)
        self.assertEqual(level_three_partial["level"], 3)
        self.assertEqual(level_three_partial["xp_in_level"], 50)
        self.assertEqual(level_three_partial["xp_needed"], 300)

    def test_streak_metrics(self):
        expenses = [
            {"date": "2026-03-05", "amount": 100},
            {"date": "2026-03-06", "amount": 120},
            {"date": "2026-03-07", "amount": 80},
            {"date": "2026-03-02", "amount": 20},
        ]
        metrics = app._build_streak_metrics(expenses, today_value=date(2026, 3, 7))
        self.assertEqual(metrics["streak_days"], 3)
        self.assertGreaterEqual(metrics["best_streak"], 3)
        self.assertEqual(metrics["today_expense_count"], 1)

    def test_daily_challenge_progress(self):
        today_value = date(2026, 3, 7)
        stats = {
            "today_expense_count": 3,
            "today_expense_total": 500.0,
            "monthly_budget": 30000.0,
        }
        challenge = app._build_daily_challenge(stats, today_value=today_value)
        self.assertIn(challenge["key"], {"track3", "daily_cap", "no_spend"})
        self.assertGreaterEqual(challenge["target"], 1)

    def test_achievement_unlocks(self):
        stats = {
            "total_expenses": 55,
            "streak_days": 8,
            "today_expense_count": 0,
            "categories": ["Food", "Investment", "Emergency Fund"],
            "has_budget": True,
            "monthly_under_budget": True,
            "monthly_savings": 5200,
        }
        new_keys, status = app._evaluate_gamification_achievements(stats, unlocked_keys=set())
        self.assertTrue(new_keys)
        self.assertTrue(any(item["key"] == "investor_mode" and item["unlocked"] for item in status))


if __name__ == "__main__":
    unittest.main()
