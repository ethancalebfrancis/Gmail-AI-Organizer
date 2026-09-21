from config import CONFIDENCE_THRESHOLD, PROTECTED_CATEGORIES


def determine_action(result):
    """Return the safest final organizer action for a classification."""
    category = result["category"]
    confidence = result["confidence"]
    recommended_action = result["recommended_action"]
    email_state = result.get("email_state", "unknown")

    if result["action_required"]:
        return "keep"

    if confidence < CONFIDENCE_THRESHOLD:
        return "review"

    if category in PROTECTED_CATEGORIES:
        if email_state == "active":
            return "keep"

        if email_state in ("completed", "informational"):
            if recommended_action == "archive":
                return "archive"

        if email_state == "promotional":
            if recommended_action in ("archive", "trash_candidate"):
                return "archive"

        if recommended_action == "archive":
            return "archive"
        if recommended_action == "trash_candidate":
            return "review"
        if recommended_action == "review":
            return "review"
        return "keep"

    if email_state == "active":
        return "keep"

    if email_state == "promotional":
        return "trash_candidate"

    if email_state == "completed":
        return "keep" if recommended_action == "keep" else "archive"

    if email_state == "informational":
        if recommended_action == "trash_candidate":
            return "trash_candidate"
        if recommended_action == "keep":
            return "keep"
        return "archive"

    if recommended_action in ("trash_candidate", "archive", "review"):
        return recommended_action

    return "keep"
