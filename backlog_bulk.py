from collections import Counter

from backlog_cache import (
    get_bulk_promotion_candidates,
    get_sender_analysis,
)
from config import (
    BACKLOG_BULK_LIVE,
    BACKLOG_BULK_MAX_PER_RUN,
    BACKLOG_BULK_MIN_EMAILS,
    BACKLOG_BULK_PROMOTION_CONSISTENCY,
)
from database import get_processed_email_ids
from rules import load_rules


# ---------------------------------------------------------
# High-risk / mixed-purpose sources
#
# Even if Gmail frequently calls these Promotions, we do
# not want historical bulk processing based only on sender.
# ---------------------------------------------------------

BLOCKED_BULK_DOMAINS = {
    "amazon.com",
    "google.com",
    "gmail.com",
    "accounts.google.com",

    # Financial institutions / financial services
    "notification.capitalone.com",
    "ealerts.bankofamerica.com",

    # Shipping / government-type transactional sources
    "email.informeddelivery.usps.com",
    "usps.com",
}


BLOCKED_BULK_SENDERS = {
    # Add individual senders here as we discover
    # mixed-purpose or sensitive sources.
}


def build_sender_stats():
    """
    Convert sender analysis into a lookup dictionary.
    """

    rows = get_sender_analysis()

    return {
        row["sender"]: row
        for row in rows
    }


def sender_qualifies(
    sender,
    domain,
    sender_stats,
    rules,
):
    """
    Determine whether a sender is safe enough to be
    considered for bulk promotional processing.
    """

    if sender in BLOCKED_BULK_SENDERS:
        return False, "blocked sender"

    if domain in BLOCKED_BULK_DOMAINS:
        return False, "blocked domain"

    sender_rules = rules.get(
        "sender_rules",
        {}
    )

    domain_rules = rules.get(
        "domain_rules",
        {}
    )

    protected_senders = {
        value.lower()
        for value in rules.get(
            "protected_senders",
            []
        )
    }

    protected_domains = {
        value.lower()
        for value in rules.get(
            "protected_domains",
            []
        )
    }

    if sender in protected_senders:
        return False, "protected sender"

    if domain in protected_domains:
        return False, "protected domain"

    if sender in sender_rules:
        return False, "existing sender rule"

    if domain in domain_rules:
        return False, "existing domain rule"

    stats = sender_stats.get(sender)

    if not stats:
        return False, "no sender statistics"

    total = stats["total"]

    if total < BACKLOG_BULK_MIN_EMAILS:
        return False, "insufficient history"

    promotions = stats[
        "promotions_count"
    ]

    consistency = (
        promotions / total
        if total
        else 0
    )

    if (
        consistency
        < BACKLOG_BULK_PROMOTION_CONSISTENCY
    ):
        return False, "mixed Gmail categories"

    return True, "qualified"


def run_backlog_bulk_preview():
    """
    Analyze historical Promotions that could potentially
    be classified locally in bulk.

    This phase does NOT modify Gmail.
    """

    print()
    print("=" * 78)
    print("GMAIL AI ORGANIZER — BULK PROMOTION PREVIEW")
    print("=" * 78)
    print()

    if BACKLOG_BULK_LIVE:
        print(
            "WARNING: BACKLOG_BULK_LIVE is enabled."
        )
    else:
        print("MODE: PREVIEW ONLY")

    print()
    print(
        "This command does not call OpenAI."
    )

    if not BACKLOG_BULK_LIVE:
        print(
            "This preview will not modify Gmail."
        )

    print()

    rules = load_rules()

    sender_stats = build_sender_stats()

    processed_ids = (
        get_processed_email_ids()
    )

    candidates = (
        get_bulk_promotion_candidates()
    )

    qualified_messages = []
    qualified_senders = Counter()

    skipped_processed = 0
    skipped_safety = 0

    reason_counter = Counter()

    for message in candidates:
        email_id = message["email_id"]

        if email_id in processed_ids:
            skipped_processed += 1
            continue

        sender = message["sender"].lower()
        domain = message["domain"].lower()

        qualifies, reason = sender_qualifies(
            sender,
            domain,
            sender_stats,
            rules,
        )

        if not qualifies:
            skipped_safety += 1
            reason_counter[reason] += 1
            continue

        qualified_messages.append(
            message
        )

        qualified_senders[sender] += 1

    print("=" * 78)
    print("PREVIEW SUMMARY")
    print("=" * 78)

    print(
        f"Cached Gmail Promotions:    "
        f"{len(candidates):,}"
    )

    print(
        f"Already processed:          "
        f"{skipped_processed:,}"
    )

    print(
        f"Safety/rule exclusions:     "
        f"{skipped_safety:,}"
    )

    print(
        f"Qualified messages:         "
        f"{len(qualified_messages):,}"
    )

    print(
        f"Qualified senders:          "
        f"{len(qualified_senders):,}"
    )

    print()

    if candidates:
        percent = (
            len(qualified_messages)
            / len(candidates)
            * 100
        )

        print(
            f"Promotion backlog eligible: "
            f"{percent:.1f}%"
        )

    print()
    print("=" * 78)
    print("TOP QUALIFIED SENDERS")
    print("=" * 78)

    for (
        sender,
        count,
    ) in qualified_senders.most_common(100):

        stats = sender_stats[sender]

        total = stats["total"]

        promotions = stats[
            "promotions_count"
        ]

        consistency = (
            promotions / total
            if total
            else 0
        )

        print(
            f"{count:>6,}  "
            f"{consistency:>6.1%}  "
            f"{sender}"
        )

    print()
    print("=" * 78)
    print("EXCLUSION REASONS")
    print("=" * 78)

    for reason, count in (
        reason_counter.most_common()
    ):
        print(
            f"{count:>7,}  {reason}"
        )

    print()
    print("=" * 78)
    print("SAMPLE QUALIFIED MESSAGES")
    print("=" * 78)

    for message in qualified_messages[:50]:
        print()
        print(
            f"FROM:    {message['sender']}"
        )
        print(
            f"SUBJECT: {message['subject']}"
        )

    print()
    print("=" * 78)

    if BACKLOG_BULK_LIVE:
        print(
            "LIVE PROCESSING HAS NOT YET BEEN "
            "IMPLEMENTED."
        )
    else:
        print(
            "PREVIEW COMPLETE — Gmail was not modified."
        )

    print(
        "No OpenAI API calls were made."
    )

    print("=" * 78)