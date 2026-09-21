from config import (
    BACKLOG_ANALYSIS_MIN_EMAILS,
    BACKLOG_ANALYSIS_TOP,
    BACKLOG_CATEGORY_CONSISTENCY,
)
from backlog_cache import (
    get_sender_analysis,
    initialize_backlog_cache,
)
from rules import load_rules


CATEGORY_FIELDS = {
    "Promotions": "promotions_count",
    "Updates": "updates_count",
    "Primary": "primary_count",
    "Social": "social_count",
    "Forums": "forums_count",
    "Uncategorized": "uncategorized_count",
}


def get_dominant_category(row):
    counts = {
        category: row[field]
        for category, field
        in CATEGORY_FIELDS.items()
    }

    category = max(
        counts,
        key=counts.get,
    )

    count = counts[category]

    total = row["total"]

    if not total:
        return category, 0, 0

    consistency = count / total

    return (
        category,
        count,
        consistency,
    )


def run_backlog_analysis():
    initialize_backlog_cache()

    rows = get_sender_analysis()

    rules = load_rules()

    sender_rules = rules.get(
        "sender_rules",
        {}
    )

    domain_rules = rules.get(
        "domain_rules",
        {}
    )

    print()
    print("=" * 78)
    print("GMAIL AI ORGANIZER — BACKLOG OPTIMIZATION")
    print("=" * 78)
    print()
    print("READ ONLY — Gmail will not be modified.")
    print("No OpenAI API calls will be made.")
    print()

    total_cached = sum(
        row["total"]
        for row in rows
    )

    print(
        f"Cached messages: "
        f"{total_cached:,}"
    )

    print(
        f"Unique senders:   "
        f"{len(rows):,}"
    )

    existing_rule_messages = 0
    strong_candidates = []
    mixed_senders = []

    for row in rows:
        sender = row["sender"]
        domain = row["domain"]
        total = row["total"]

        if (
            sender in sender_rules
            or domain in domain_rules
        ):
            existing_rule_messages += total
            continue

        if (
            total
            < BACKLOG_ANALYSIS_MIN_EMAILS
        ):
            continue

        (
            dominant_category,
            dominant_count,
            consistency,
        ) = get_dominant_category(row)

        result = {
            **row,
            "dominant_category": dominant_category,
            "dominant_count": dominant_count,
            "consistency": consistency,
        }

        if (
            consistency
            >= BACKLOG_CATEGORY_CONSISTENCY
        ):
            strong_candidates.append(result)
        else:
            mixed_senders.append(result)

    strong_candidates.sort(
        key=lambda row: row["total"],
        reverse=True,
    )

    mixed_senders.sort(
        key=lambda row: row["total"],
        reverse=True,
    )

    strong_message_count = sum(
        row["total"]
        for row in strong_candidates
    )

    print()
    print("=" * 78)
    print("OPTIMIZATION POTENTIAL")
    print("=" * 78)

    print(
        f"Covered by existing rules: "
        f"{existing_rule_messages:,}"
    )

    print(
        f"Strong bulk candidates:     "
        f"{strong_message_count:,}"
    )

    if total_cached:
        potential = (
            (
                existing_rule_messages
                + strong_message_count
            )
            / total_cached
            * 100
        )

        print(
            f"Potential local coverage:   "
            f"{potential:.1f}%"
        )

    print()
    print("=" * 78)
    print("STRONG BULK CANDIDATES")
    print("=" * 78)

    for row in strong_candidates[
        :BACKLOG_ANALYSIS_TOP
    ]:
        print(
            f"{row['total']:>6,}  "
            f"{row['consistency']:>6.1%}  "
            f"{row['dominant_category']:<13}  "
            f"{row['sender']}"
        )

    print()
    print("=" * 78)
    print("HIGH-VOLUME MIXED SENDERS")
    print("=" * 78)

    for row in mixed_senders[
        :50
    ]:
        print(
            f"{row['total']:>6,}  "
            f"{row['consistency']:>6.1%}  "
            f"{row['dominant_category']:<13}  "
            f"{row['sender']}"
        )

    print()
    print("=" * 78)
    print("ANALYSIS COMPLETE")
    print("=" * 78)