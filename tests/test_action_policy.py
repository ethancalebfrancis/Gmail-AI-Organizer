import unittest

from action_policy import determine_action


class ActionPolicyTests(unittest.TestCase):
    def base(self, **updates):
        result = {
            "category": "Marketing",
            "confidence": 0.99,
            "recommended_action": "trash_candidate",
            "email_state": "promotional",
            "action_required": False,
        }
        result.update(updates)
        return result

    def test_marketing_promotion_can_quarantine(self):
        self.assertEqual(determine_action(self.base()), "trash_candidate")

    def test_financial_never_auto_trashes(self):
        result = self.base(category="Financial")
        self.assertNotEqual(determine_action(result), "trash_candidate")

    def test_receipt_never_auto_trashes(self):
        result = self.base(category="Receipts")
        self.assertNotEqual(determine_action(result), "trash_candidate")

    def test_work_career_never_auto_trashes(self):
        result = self.base(category="Work & Career")
        self.assertNotEqual(determine_action(result), "trash_candidate")

    def test_low_confidence_goes_to_review(self):
        result = self.base(confidence=0.50)
        self.assertEqual(determine_action(result), "review")

    def test_action_required_is_kept(self):
        result = self.base(action_required=True)
        self.assertEqual(determine_action(result), "keep")

    def test_travel_promotional_is_not_trashed(self):
        result = self.base(
            category="Travel",
            email_state="promotional",
            recommended_action="trash_candidate",
            confidence=0.99,
        )
        self.assertEqual(determine_action(result), "archive")

    def test_events_promotional_is_not_trashed(self):
        result = self.base(
            category="Events",
            email_state="promotional",
            recommended_action="trash_candidate",
            confidence=0.99,
        )
        self.assertEqual(determine_action(result), "archive")


if __name__ == "__main__":
    unittest.main()
