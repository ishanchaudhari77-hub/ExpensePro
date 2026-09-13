import unittest


APP_IMPORT_ERROR = None
try:
    import app
except Exception as exc:  # pragma: no cover - environment dependent import guard
    app = None
    APP_IMPORT_ERROR = exc


@unittest.skipIf(app is None, f"app import failed: {APP_IMPORT_ERROR}")
class RupyChatReplyTests(unittest.TestCase):
    def _snapshot(self):
        return {
            "month_label": "March 2026",
            "today_total": 850.0,
            "today_count": 3,
            "today_category_totals": {"Food": 420.0, "Transport": 220.0, "Shopping": 210.0},
            "top_today_category": {"category": "Food", "amount": 420.0},
            "yesterday_total": 640.0,
            "yesterday_count": 2,
            "yesterday_category_totals": {"Food": 340.0, "Transport": 300.0},
            "top_yesterday_category": {"category": "Food", "amount": 340.0},
            "monthly_budget": 12000.0,
            "monthly_expense": 7400.0,
            "monthly_remaining": 4600.0,
            "monthly_spent_percent": 61.7,
            "daily_budget_cap": 400.0,
            "monthly_forecast": {"forecast_over_by": 0.0},
            "weekly_summary": {
                "total": 3200.0,
                "transactions": 11,
                "weekend_total": 980.0,
            },
            "weekly_category_totals": {"Food": 1340.0, "Transport": 800.0, "Shopping": 1060.0},
            "weekly_top_category": {"category": "Food", "share_percent": 42.0},
            "monthly_category_totals": {"Food": 2800.0, "Transport": 1800.0, "Shopping": 1900.0, "Bills": 900.0},
            "top_month_category": {"category": "Food", "amount": 2800.0, "share_percent": 37.8},
            "monthly_income": 18000.0,
            "monthly_net": 10600.0,
            "streak_days": 8,
            "best_streak": 11,
            "level": 4,
            "level_title": "Money Apprentice",
            "total_xp": 790,
            "xp_in_level": 90,
            "xp_needed": 400,
            "inactive_24h": False,
        }

    def test_today_spend_reply_has_expected_intent(self):
        reply = app._build_rupy_chat_reply("How much did I spend today?", self._snapshot())
        self.assertEqual(reply["intent"], "today_spend")
        self.assertIn("Food", reply["answer"])
        self.assertIn("\u20b9", reply["answer"])

    def test_budget_warning_reply_when_budget_crossed(self):
        snapshot = self._snapshot()
        snapshot["monthly_remaining"] = -1500.0
        snapshot["monthly_spent_percent"] = 112.0
        reply = app._build_rupy_chat_reply("Budget left this month?", snapshot)
        self.assertEqual(reply["intent"], "budget_status")
        self.assertEqual(reply["state"], "warning")
        self.assertEqual(reply["event_type"], "high_spending")

    def test_no_spend_day_reply_triggers_money_rain(self):
        snapshot = self._snapshot()
        snapshot["today_total"] = 0.0
        snapshot["today_count"] = 0
        snapshot["top_today_category"] = {"category": "", "amount": 0.0}
        reply = app._build_rupy_chat_reply("no spend day status", snapshot)
        self.assertEqual(reply["intent"], "no_spend_day")
        self.assertEqual(reply["state"], "money-rain")
        self.assertEqual(reply["event_type"], "no_spend_day")

    def test_followup_aur_kal_uses_context(self):
        reply = app._build_rupy_chat_reply(
            "aur kal?",
            self._snapshot(),
            context={"last_intent": "today_spend", "last_timeframe": "today", "last_category": "Food"},
        )
        self.assertEqual(reply["intent"], "yesterday_spend")
        self.assertIn("Kal spend", reply["answer"])

    def test_category_followup_uses_last_category(self):
        reply = app._build_rupy_chat_reply(
            "us category ka kya?",
            self._snapshot(),
            context={"last_intent": "top_category", "last_timeframe": "monthly", "last_category": "Food"},
        )
        self.assertEqual(reply["intent"], "category_followup")
        self.assertEqual(reply["focus_category"], "Food")
        self.assertIn("Food", reply["answer"])

    def test_context_derivation_from_reply(self):
        reply = {"intent": "top_category"}
        context = app._derive_rupy_chat_context(reply, snapshot=self._snapshot())
        self.assertEqual(context["last_intent"], "top_category")
        self.assertEqual(context["last_timeframe"], "monthly")
        self.assertEqual(context["last_category"], "Food")


if __name__ == "__main__":
    unittest.main()
