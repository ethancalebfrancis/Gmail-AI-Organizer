from config import (
    PHASE3_LEARN_MIN_CONFIDENCE,
    PHASE3_LEARN_MIN_EXAMPLES,
    PROTECTED_CATEGORIES,
)
from database import get_phase3_learned_pattern
from historical_pattern_rules import get_subject_signature


def get_learned_pattern_classification(email):
    """Return a safe locally learned classification for one sender/subject pattern."""
    sender = (email.get("sender") or "").lower().strip()
    signature = get_subject_signature(email.get("subject") or "")
    if not sender or not signature:
        return None

    pattern = get_phase3_learned_pattern(
        sender,
        signature,
        min_examples=PHASE3_LEARN_MIN_EXAMPLES,
        min_confidence=PHASE3_LEARN_MIN_CONFIDENCE,
    )
    if not pattern:
        return None

    action = pattern["final_action"]
    category = pattern["category"]
    state = pattern.get("email_state") or "unknown"

    # Learned deletion is intentionally narrower than learned archive/keep.
    if action == "trash_candidate":
        if category in PROTECTED_CATEGORIES:
            return None
        if category not in {"Marketing", "Newsletters"}:
            return None
        if state != "promotional":
            return None

    return {
        "category": category,
        "subcategory": pattern.get("subcategory") or "Learned historical pattern",
        "email_state": state,
        "importance": "low" if action in {"archive", "trash_candidate"} else "medium",
        "action_required": False,
        "confidence": 0.97,
        "recommended_action": action,
        "reason": (
            "Matched a learned sender + subject pattern from "
            f"{pattern['examples']} consistent historical classifications."
        ),
        "classification_source": "learned_pattern",
    }
