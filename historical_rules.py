import re


# ---------------------------------------------------------------------
# PROTECTED / TRANSACTIONAL PATTERNS
#
# These are checked BEFORE promotional patterns.
# That is important because mixed senders such as retailers can send
# both advertisements and legitimate transactional messages.
# ---------------------------------------------------------------------

SECURITY_PATTERNS = [
    r"\bsecurity alert\b",
    r"\bsuspicious (?:activity|login|sign[- ]?in)\b",
    r"\bnew (?:login|sign[- ]?in)\b",
    r"\bpassword (?:changed|reset)\b",
    r"\breset your password\b",
    r"\bverification code\b",
    r"\bverify your (?:account|identity)\b",
    r"\btwo[- ]factor\b",
    r"\b2fa\b",
]

PAYMENT_PATTERNS = [
    r"\bpayment (?:has been |was )?received\b",
    r"\bpayment confirmation\b",
    r"\bpayment posted\b",
    r"\bpayment processed\b",
    r"\bwe received your payment\b",
    r"\bwe've received your payment\b",
    r"\byour payment\b",
    r"\bbilling statement\b",
    r"\bstatement (?:is )?available\b",
    r"\bstatement is ready\b",
    r"\bstatement ready\b",
    r"\bsavings statement\b",
    r"\bcard has been successfully linked\b",
    r"\bavailable balance\b",
    r"\bcurrent balance\b",
]

REFUND_PATTERNS = [
    r"\brefund issued\b",
    r"\brefund processed\b",
    r"\brefund complete\b",
    r"\byour refund\b",
    r"\brefund confirmation\b",
]

RECEIPT_PATTERNS = [
    r"\breceipt\b",
    r"\bthanks for your .* order\b",
    r"\bthank you for your .* order\b",
    r"\bpurchase confirmation\b",
    r"\border receipt\b",
    r"\bthanks for your (?:purchase|order)\b",
    r"\bthank you for your (?:purchase|order)\b",
]

ORDER_PATTERNS = [
    r"\bordered:",
    r"\border confirmation\b",
    r"\border confirmed\b",
    r"\byour order\b",
    r"\border #",
]

SHIPPING_PATTERNS = [
    r"\bshipped:",
    r"\byour order has shipped\b",
    r"\border shipped\b",
    r"\bout for delivery\b",
    r"\bdelivery update\b",
    r"\bdelivered:",
    r"\bpackage delivered\b",
    r"\btracking update\b",
]

# ---------------------------------------------------------------------
# PROMOTIONAL PATTERNS
# ---------------------------------------------------------------------

PROMOTION_PATTERNS = [
    r"\b\d{1,3}% off\b",
    r"\bsave \$?\d+",
    r"\bsave up to\b",
    r"\bup to \d{1,3}% off\b",
    r"\bbogo\b",
    r"\bbuy one[, ]+get one\b",
    r"\bflash sale\b",
    r"\bsale ends\b",
    r"\bends (?:today|tonight|soon)\b",
    r"\blast chance\b",
    r"\bhours left\b",
    r"\bshop now\b",
    r"\bshop the sale\b",
    r"\bfree shipping\b",
    r"\bfree ship\b",
    r"\bexclusive offer\b",
    r"\bspecial offer\b",
    r"\bcoupon\b",
    r"\bpromo code\b",
    r"\bdeal(?:s)?\b",
    r"\bclearance\b",
    r"\bnew arrivals\b",
]

# Words that make an apparently promotional message too risky
# for deterministic trash classification.
PROMOTION_BLOCKERS = [
    r"\breceipt\b",
    r"\border\b",
    r"\bshipped\b",
    r"\bdelivered\b",
    r"\brefund\b",
    r"\bpayment\b",
    r"\bbalance\b",
    r"\bstatement\b",
    r"\bsecurity\b",
    r"\bpassword\b",
    r"\bverification\b",
    r"\bappointment\b",
    r"\breservation\b",
    r"\bapplication\b",
]


def matches_any(text, patterns):
    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


def build_result(
    category,
    subcategory,
    importance,
    action_required,
    recommended_action,
    reason,
    email_state="informational",
    confidence=0.98,
):
    return {
        "category": category,
        "subcategory": subcategory,
        "email_state": email_state,
        "importance": importance,
        "action_required": action_required,
        "confidence": confidence,
        "recommended_action": recommended_action,
        "reason": reason,
        "classification_source": "historical_rule",
    }


def check_historical_rule(email, gmail_category=None):
    """
    Conservative subject/sender-based historical classifier.

    Returns a classification dictionary when a deterministic
    rule is sufficiently safe.

    Returns None when the message should continue to another
    classifier.

    IMPORTANT:
    Transactional/protected patterns are checked before
    promotional patterns.
    """

    sender = (
        email.get("sender")
        or ""
    ).lower()

    subject = (
        email.get("subject")
        or ""
    ).strip()

    if not subject:
        return None

    # -------------------------------------------------------------
    # 1. SECURITY
    # -------------------------------------------------------------

    if matches_any(
        subject,
        SECURITY_PATTERNS,
    ):
        return build_result(
            category="Accounts & Security",
            subcategory="Account security notification",
            importance="high",
            action_required=False,
            recommended_action="archive",
            reason=(
                "Historical rule detected an account/security "
                "notification."
            ),
            confidence=0.99,
        )

    # -------------------------------------------------------------
    # 2. PAYMENTS / FINANCIAL INFORMATION
    # -------------------------------------------------------------

    if matches_any(
        subject,
        PAYMENT_PATTERNS,
    ):
        return build_result(
            category="Financial",
            subcategory="Payment or account notification",
            importance="medium",
            action_required=False,
            recommended_action="archive",
            reason=(
                "Historical rule detected a financial/payment "
                "notification."
            ),
            confidence=0.99,
        )

    # -------------------------------------------------------------
    # 3. REFUNDS
    # -------------------------------------------------------------

    if matches_any(
        subject,
        REFUND_PATTERNS,
    ):
        return build_result(
            category="Shopping & Orders",
            subcategory="Refund notification",
            importance="medium",
            action_required=False,
            recommended_action="archive",
            reason=(
                "Historical rule detected a refund notification."
            ),
            confidence=0.99,
        )

    # -------------------------------------------------------------
    # 4. RECEIPTS
    # -------------------------------------------------------------

    if matches_any(
        subject,
        RECEIPT_PATTERNS,
    ):
        return build_result(
            category="Receipts",
            subcategory="Purchase receipt",
            importance="medium",
            action_required=False,
            recommended_action="archive",
            reason=(
                "Historical rule detected a receipt or purchase "
                "confirmation."
            ),
            confidence=0.99,
        )

    # -------------------------------------------------------------
    # 5. SHIPPING
    # -------------------------------------------------------------

    if matches_any(
        subject,
        SHIPPING_PATTERNS,
    ):
        return build_result(
            category="Shopping & Orders",
            subcategory="Shipping or delivery notification",
            importance="medium",
            action_required=False,
            recommended_action="archive",
            reason=(
                "Historical rule detected a shipping/delivery "
                "notification."
            ),
            confidence=0.99,
        )

    # -------------------------------------------------------------
    # 6. ORDERS
    # -------------------------------------------------------------

    if matches_any(
        subject,
        ORDER_PATTERNS,
    ):
        return build_result(
            category="Shopping & Orders",
            subcategory="Order notification",
            importance="medium",
            action_required=False,
            recommended_action="archive",
            reason=(
                "Historical rule detected an order notification."
            ),
            confidence=0.98,
        )

    # -------------------------------------------------------------
    # 7. PROMOTIONS
    #
    # Require Gmail to ALSO believe it is promotional.
    #
    # This gives us two independent signals:
    #     subject looks promotional
    #             +
    #     Gmail categorized it Promotions
    #
    # That's much safer than relying on keywords alone.
    # -------------------------------------------------------------

    promotional_subject = matches_any(
        subject,
        PROMOTION_PATTERNS,
    )

    blocked = matches_any(
        subject,
        PROMOTION_BLOCKERS,
    )

    if (
        gmail_category == "Promotions"
        and promotional_subject
        and not blocked
    ):
        return build_result(
            category="Marketing",
            subcategory="Historical promotion",
            importance="low",
            action_required=False,
            recommended_action="trash_candidate",
            reason=(
                "Historical rule detected an obvious promotion "
                "and Gmail independently categorized the message "
                "as Promotions."
            ),
            email_state="promotional",
            confidence=0.99,
        )

    # -------------------------------------------------------------
    # Unknown / mixed / ambiguous.
    # -------------------------------------------------------------

    return None