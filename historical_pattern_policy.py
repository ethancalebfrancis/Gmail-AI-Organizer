from collections import Counter

from backlog_cache import get_cached_messages

# These rules intentionally use sender + subject content.
# We do NOT blindly trust Gmail's Promotions / Updates category.

PATTERN_POLICIES = [
    # ---------------------------------------------------------
    # SHOPPING / ORDERS
    # ---------------------------------------------------------
    {
        "sender_contains": "amazon.com",
        "subject_contains": [
            "order",
            "shipped",
        ],
        "category": "Shopping & Orders",
        "subcategory": "Shipping",
        "action": "archive",
    },
    {
        "sender_contains": "amazon.com",
        "subject_contains": [
            "delivered",
        ],
        "category": "Shopping & Orders",
        "subcategory": "Delivery",
        "action": "archive",
    },
    {
        "sender_contains": "ups.com",
        "subject_contains": [
            "package",
        ],
        "category": "Shopping & Orders",
        "subcategory": "Shipping",
        "action": "archive",
    },

    # ---------------------------------------------------------
    # RECEIPTS
    # ---------------------------------------------------------
    {
        "sender_contains": "email.apple.com",
        "subject_contains": [
            "receipt",
        ],
        "category": "Receipts",
        "subcategory": "Digital Purchase",
        "action": "archive",
    },
    {
        "sender_contains": "googleplay-noreply@google.com",
        "subject_contains": [
            "receipt",
        ],
        "category": "Receipts",
        "subcategory": "Digital Purchase",
        "action": "archive",
    },
    {
        "sender_contains": "steampowered.com",
        "subject_contains": [
            "purchase",
        ],
        "category": "Receipts",
        "subcategory": "Gaming Purchase",
        "action": "archive",
    },
    {
        "sender_contains": "dndbeyond.com",
        "subject_contains": [
            "receipt",
        ],
        "category": "Receipts",
        "subcategory": "Subscription Receipt",
        "action": "archive",
    },

    # ---------------------------------------------------------
    # ACCOUNTS / SECURITY
    # ---------------------------------------------------------
    {
        "sender_contains": "bitwarden.com",
        "subject_contains": [
            "verification code",
        ],
        "category": "Accounts & Security",
        "subcategory": "Verification Code",
        "action": "keep",
    },
    {
        "sender_contains": "spotify.com",
        "subject_contains": [
            "new login",
        ],
        "category": "Accounts & Security",
        "subcategory": "Login Alert",
        "action": "keep",
    },
    {
        "sender_contains": "todoist.com",
        "subject_contains": [
            "new login",
        ],
        "category": "Accounts & Security",
        "subcategory": "Login Alert",
        "action": "keep",
    },
    {
        "sender_contains": "disneyplus.com",
        "subject_contains": [
            "new login",
        ],
        "category": "Accounts & Security",
        "subcategory": "Login Alert",
        "action": "keep",
    },
    {
        "sender_contains": "id.apple.com",
        "subject_contains": [
            "information has been updated",
        ],
        "category": "Accounts & Security",
        "subcategory": "Account Change",
        "action": "keep",
    },

    # ---------------------------------------------------------
    # FINANCIAL
    # ---------------------------------------------------------
    {
        "sender_contains": "bankofamerica.com",
        "subject_contains": [
            "available balance",
        ],
        "category": "Financial",
        "subcategory": "Balance Alert",
        "action": "keep",
    },
    {
        "sender_contains": "bankofamerica.com",
        "subject_contains": [
            "balance below",
        ],
        "category": "Financial",
        "subcategory": "Balance Alert",
        "action": "keep",
    },
    {
        "sender_contains": "bankofamerica.com",
        "subject_contains": [
            "debit card",
        ],
        "category": "Financial",
        "subcategory": "Transaction Alert",
        "action": "keep",
    },
    {
        "sender_contains": "bankofamerica.com",
        "subject_contains": [
            "direct deposit",
        ],
        "category": "Financial",
        "subcategory": "Deposit",
        "action": "keep",
    },
    {
        "sender_contains": "bankofamerica.com",
        "subject_contains": [
            "statement",
        ],
        "category": "Financial",
        "subcategory": "Statement",
        "action": "keep",
    },
    {
        "sender_contains": "capitalone.com",
        "subject_contains": [
            "received your payment",
        ],
        "category": "Financial",
        "subcategory": "Payment Confirmation",
        "action": "archive",
    },
    {
        "sender_contains": "discover.com",
        "subject_contains": [
            "received your payment",
        ],
        "category": "Financial",
        "subcategory": "Payment Confirmation",
        "action": "archive",
    },
    {
        "sender_contains": "discover.com",
        "subject_contains": [
            "scheduled payment",
        ],
        "category": "Financial",
        "subcategory": "Scheduled Payment",
        "action": "keep",
    },
    {
        "sender_contains": "applecard.apple",
        "subject_contains": [
            "payment has been received",
        ],
        "category": "Financial",
        "subcategory": "Payment Confirmation",
        "action": "archive",
    },
    {
        "sender_contains": "square.com",
        "subject_contains": [
            "payment received",
        ],
        "category": "Financial",
        "subcategory": "Payment",
        "action": "keep",
    },
    {
        "sender_contains": "santander.us",
        "subject_contains": [
            "balance",
        ],
        "category": "Financial",
        "subcategory": "Balance Alert",
        "action": "keep",
    },

    # ---------------------------------------------------------
    # WORK / CAREER
    # ---------------------------------------------------------
    {
        "sender_contains": "resume-library.com",
        "subject_contains": [
            "jobs",
        ],
        "category": "Work & Career",
        "subcategory": "Job Alert",
        "action": "archive",
    },
    {
        "sender_contains": "nexxt.com",
        "subject_contains": [
            "jobs",
        ],
        "category": "Work & Career",
        "subcategory": "Job Alert",
        "action": "archive",
    },
    {
        "sender_contains": "adzuna.com",
        "subject_contains": [
            "job",
        ],
        "category": "Work & Career",
        "subcategory": "Job Alert",
        "action": "archive",
    },
    {
        "sender_contains": "ziprecruiter.com",
        "subject_contains": [
            "job",
        ],
        "category": "Work & Career",
        "subcategory": "Job Alert",
        "action": "archive",
    },
    {
        "sender_contains": "jobs2web.com",
        "subject_contains": [
            "jobs",
        ],
        "category": "Work & Career",
        "subcategory": "Job Alert",
        "action": "archive",
    },
    {
        "sender_contains": "albertsons.com",
        "subject_contains": [
            "job opportunities",
        ],
        "category": "Work & Career",
        "subcategory": "Job Alert",
        "action": "archive",
    },

    # ---------------------------------------------------------
    # SCHOOL
    # ---------------------------------------------------------
    {
        "sender_contains": "fastweb.com",
        "subject_contains": [
            "scholarship",
        ],
        "category": "School",
        "subcategory": "Scholarship",
        "action": "archive",
    },

    # ---------------------------------------------------------
    # TRAVEL
    # ---------------------------------------------------------
    {
        "sender_contains": "noreply-travel@google.com",
        "subject_contains": [
            "tracked",
        ],
        "category": "Travel",
        "subcategory": "Flight Alert",
        "action": "archive",
    },

    # ---------------------------------------------------------
    # MARKETING
    # ---------------------------------------------------------
    {
        "sender_contains": "bestbuy.com",
        "subject_contains": [
            "today only",
            "save",
        ],
        "category": "Marketing",
        "subcategory": "Retail Promotion",
        "action": "trash_candidate",
    },
    {
        "sender_contains": "joinhoney.com",
        "subject_contains": [
            "price drops",
        ],
        "category": "Marketing",
        "subcategory": "Price Alert",
        "action": "trash_candidate",
    },
    {
        "sender_contains": "cheapoair.com",
        "subject_contains": [
            "deals",
        ],
        "category": "Marketing",
        "subcategory": "Travel Promotion",
        "action": "trash_candidate",
    },
    {
        "sender_contains": "macys.com",
        "subject_contains": [
            "sale",
        ],
        "category": "Marketing",
        "subcategory": "Retail Promotion",
        "action": "trash_candidate",
    },
    {
        "sender_contains": "dunkinrewards.com",
        "subject_contains": [
            "bonus",
        ],
        "category": "Marketing",
        "subcategory": "Rewards Promotion",
        "action": "trash_candidate",
    },
    {
        "sender_contains": "offers.shaws.com",
        "subject_contains": [
            "savings",
        ],
        "category": "Marketing",
        "subcategory": "Grocery Promotion",
        "action": "trash_candidate",
    },
]


def match_pattern_policy(sender, subject):
    """
    Return a pattern policy when both sender and subject
    requirements match.

    Returns None when no safe rule exists.
    """

    sender = (sender or "").lower().strip()
    subject = (subject or "").lower().strip()

    for policy in PATTERN_POLICIES:
        sender_match = (
            policy["sender_contains"].lower()
            in sender
        )

        if not sender_match:
            continue

        required_terms = policy.get(
            "subject_contains",
            [],
        )

        subject_match = all(
            term.lower() in subject
            for term in required_terms
        )

        if not subject_match:
            continue

        return {
            "category": policy["category"],
            "subcategory": policy["subcategory"],
            "recommended_action": policy["action"],
            "confidence": 0.99,
            "classification_source": "pattern_policy",
        }

    return None


def run_pattern_policy_preview(limit=1000):
    """
    Test pattern policies against cached historical mail.

    READ ONLY:
    - no Gmail modifications
    - no OpenAI calls
    - no database writes
    """

    print()
    print("=" * 78)
    print(
        "GMAIL AI ORGANIZER — "
        "HISTORICAL PATTERN POLICY PREVIEW"
    )
    print("=" * 78)
    print()
    print("READ ONLY")
    print("Gmail will NOT be modified.")
    print("OpenAI will NOT be called.")
    print()

    messages = get_cached_messages(
        limit=limit
    )

    matched = []
    unmatched = []

    for message in messages:
        sender = message.get(
            "sender",
            ""
        )

        subject = message.get(
            "subject",
            ""
        )

        policy = match_pattern_policy(
            sender,
            subject,
        )

        if policy:
            matched.append(
                {
                    "sender": sender,
                    "subject": subject,
                    **policy,
                }
            )

        else:
            unmatched.append(message)

    action_counts = Counter(
        item["recommended_action"]
        for item in matched
    )

    category_counts = Counter(
        item["category"]
        for item in matched
    )

    total = len(messages)

    coverage = (
        len(matched) / total
        if total
        else 0
    )

    print(f"Messages analyzed:       {total:,}")
    print(f"Pattern matches:         {len(matched):,}")
    print(f"Still unclassified:      {len(unmatched):,}")
    print(f"Pattern coverage:        {coverage:.1%}")

    print()
    print("-" * 78)
    print("MATCHED CATEGORIES")
    print("-" * 78)

    for category, count in category_counts.most_common():
        print(
            f"{category:<28} {count:>6,}"
        )

    print()
    print("-" * 78)
    print("PROPOSED ACTIONS")
    print("-" * 78)

    for action, count in action_counts.most_common():
        print(
            f"{action:<28} {count:>6,}"
        )

    print()
    print("-" * 78)
    print("MATCH EXAMPLES")
    print("-" * 78)

    for item in matched[:50]:
        print()
        print(
            f"FROM:       {item['sender']}"
        )
        print(
            f"SUBJECT:    {item['subject']}"
        )
        print(
            f"CATEGORY:   {item['category']}"
        )
        print(
            f"SUBCATEGORY:{item['subcategory']}"
        )
        print(
            f"ACTION:     "
            f"{item['recommended_action']}"
        )

    print()
    print("=" * 78)
    print("PATTERN POLICY PREVIEW COMPLETE")
    print("=" * 78)
    print()
    print("NO GMAIL MESSAGES WERE MODIFIED.")
    print("NO OPENAI API CALLS WERE MADE.")
    print("=" * 78)

def get_pattern_classification(email):
    """
    Convert a matched pattern policy into the same
    classification structure used by the organizer.

    Returns None when no pattern policy matches.
    """

    sender = email.get(
        "sender",
        ""
    )

    subject = email.get(
        "subject",
        ""
    )

    policy = match_pattern_policy(
        sender,
        subject,
    )

    if not policy:
        return None

    action = policy[
        "recommended_action"
    ]

    if action == "keep":
        email_state = "active"

    elif action == "trash_candidate":
        email_state = "promotional"

    else:
        email_state = "informational"

    return {
        "category": policy["category"],
        "subcategory": policy["subcategory"],
        "email_state": email_state,
        "importance": (
            "medium"
            if action == "keep"
            else "low"
        ),
        "action_required": False,
        "confidence": policy["confidence"],
        "recommended_action": action,
        "reason": (
            "Matched a verified sender + "
            "subject pattern policy."
        ),
        "classification_source":
            "pattern_policy",
    }