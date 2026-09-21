import unittest

from historical_rules import check_historical_rule


class HistoricalRuleTests(unittest.TestCase):
    def classify(self, subject, gmail_category="Updates"):
        return check_historical_rule(
            {"sender": "sender@example.com", "subject": subject},
            gmail_category=gmail_category,
        )

    def test_savings_statement_is_financial_not_marketing(self):
        result = self.classify("Your Savings statement is ready", "Promotions")
        self.assertEqual(result["category"], "Financial")
        self.assertEqual(result["recommended_action"], "archive")

    def test_card_linked_is_financial_not_marketing(self):
        result = self.classify("Your card has been successfully linked", "Promotions")
        self.assertEqual(result["category"], "Financial")
        self.assertEqual(result["recommended_action"], "archive")

    def test_promotion_requires_promotions_category(self):
        self.assertIsNone(self.classify("40% Off Today", "Primary"))

    def test_promotion_can_be_quarantined_when_gmail_agrees(self):
        result = self.classify("40% Off Today", "Promotions")
        self.assertEqual(result["category"], "Marketing")
        self.assertEqual(result["recommended_action"], "trash_candidate")


if __name__ == "__main__":
    unittest.main()
