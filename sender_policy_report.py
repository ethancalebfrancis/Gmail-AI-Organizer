from collections import Counter

from backlog_cache import (
    get_sender_analysis,
    load_sender_policies,
)


def run_sender_policy_report():
    """
    Summarize cached AI sender policies and estimate
    how many historical Gmail messages they cover.

    READ ONLY:
    - Does not modify Gmail
    - Does not call OpenAI
    """

    policies = load_sender_policies()
    sender_analysis = get_sender_analysis()

    print()
    print("=" * 78)
    print("GMAIL AI ORGANIZER — SENDER POLICY REPORT")
    print("=" * 78)
    print()
    print("READ ONLY — Gmail will not be modified.")
    print("No OpenAI API calls will be made.")
    print()

    if not policies:
        print("No sender policies were found.")
        print()
        print(
            "Run python main.py "
            "--sender-policy-preview first."
        )
        print("=" * 78)
        return

    # ---------------------------------------------------------
    # Build sender -> historical message count lookup
    # ---------------------------------------------------------

    sender_counts = {
        row["sender"].lower(): row["total"]
        for row in sender_analysis
    }

    # ---------------------------------------------------------
    # Sender-level statistics
    # ---------------------------------------------------------

    total_policies = len(policies)

    bulk_safe_policies = [
        policy
        for policy in policies
        if policy["bulk_safe"]
    ]

    individual_policies = [
        policy
        for policy in policies
        if not policy["bulk_safe"]
    ]

    action_counts = Counter(
        policy["bulk_action"]
        for policy in policies
    )

    category_counts = Counter(
        policy["category"]
        for policy in policies
    )

    # ---------------------------------------------------------
    # Message-level statistics
    # ---------------------------------------------------------

    message_counts = {
        "trash_candidate": 0,
        "archive": 0,
        "keep": 0,
        "individual_classification": 0,
    }

    total_messages_covered = 0

    for policy in policies:
        sender = policy["sender"].lower()

        count = sender_counts.get(
            sender,
            0
        )

        total_messages_covered += count

        if policy["bulk_safe"]:
            action = policy["bulk_action"]

            if action in message_counts:
                message_counts[action] += count

        else:
            message_counts[
                "individual_classification"
            ] += count

    bulk_message_count = (
        message_counts["trash_candidate"]
        + message_counts["archive"]
        + message_counts["keep"]
    )

    if total_messages_covered:
        bulk_message_percentage = (
            bulk_message_count
            / total_messages_covered
            * 100
        )
    else:
        bulk_message_percentage = 0

    # ---------------------------------------------------------
    # Main summary
    # ---------------------------------------------------------

    print("=" * 78)
    print("SENDER COVERAGE")
    print("=" * 78)

    print(
        f"Sender policies analyzed:          "
        f"{total_policies:,}"
    )

    print(
        f"Bulk-safe senders:                 "
        f"{len(bulk_safe_policies):,}"
    )

    print(
        f"Individual-classification senders: "
        f"{len(individual_policies):,}"
    )

    if total_policies:
        sender_percentage = (
            len(bulk_safe_policies)
            / total_policies
            * 100
        )

        print(
            f"Bulk-safe sender percentage:       "
            f"{sender_percentage:.1f}%"
        )

    # ---------------------------------------------------------
    # Actions by sender
    # ---------------------------------------------------------

    print()
    print("=" * 78)
    print("SENDER ACTIONS")
    print("=" * 78)

    print(
        f"Trash candidate:                   "
        f"{action_counts.get('trash_candidate', 0):,}"
    )

    print(
        f"Archive:                           "
        f"{action_counts.get('archive', 0):,}"
    )

    print(
        f"Keep:                              "
        f"{action_counts.get('keep', 0):,}"
    )

    print(
        f"Individual classification:         "
        f"{action_counts.get('individual_classification', 0):,}"
    )

    # ---------------------------------------------------------
    # Historical message coverage
    # ---------------------------------------------------------

    print()
    print("=" * 78)
    print("HISTORICAL MESSAGE COVERAGE")
    print("=" * 78)

    print(
        f"Messages represented by policies:  "
        f"{total_messages_covered:,}"
    )

    print()
    print(
        f"Bulk trash candidates:             "
        f"{message_counts['trash_candidate']:,}"
    )

    print(
        f"Bulk archive:                      "
        f"{message_counts['archive']:,}"
    )

    print(
        f"Bulk keep:                         "
        f"{message_counts['keep']:,}"
    )

    print(
        f"Individual AI classification:      "
        f"{message_counts['individual_classification']:,}"
    )

    print()
    print(
        f"Messages eligible for bulk action: "
        f"{bulk_message_count:,}"
    )

    print(
        f"Potential bulk coverage:           "
        f"{bulk_message_percentage:.1f}%"
    )

    # ---------------------------------------------------------
    # Category distribution
    # ---------------------------------------------------------

    print()
    print("=" * 78)
    print("POLICY CATEGORY BREAKDOWN")
    print("=" * 78)

    for category, count in (
        category_counts.most_common()
    ):
        print(
            f"{category:<32}"
            f"{count:>8,}"
        )

    # ---------------------------------------------------------
    # Bulk-safe trash senders
    # ---------------------------------------------------------

    print()
    print("=" * 78)
    print("BULK-SAFE TRASH SENDERS")
    print("=" * 78)

    trash_policies = [
        policy
        for policy in policies
        if (
            policy["bulk_safe"]
            and policy["bulk_action"]
            == "trash_candidate"
        )
    ]

    trash_policies.sort(
        key=lambda policy: (
            sender_counts.get(
                policy["sender"].lower(),
                0
            )
        ),
        reverse=True,
    )

    if not trash_policies:
        print("None")
    else:
        for policy in trash_policies:
            sender = policy["sender"]

            count = sender_counts.get(
                sender.lower(),
                0
            )

            confidence = policy["confidence"]

            print(
                f"{count:>6,}  "
                f"{confidence:>6.0%}  "
                f"{sender}"
            )

    # ---------------------------------------------------------
    # Bulk-safe archive senders
    # ---------------------------------------------------------

    print()
    print("=" * 78)
    print("BULK-SAFE ARCHIVE SENDERS")
    print("=" * 78)

    archive_policies = [
        policy
        for policy in policies
        if (
            policy["bulk_safe"]
            and policy["bulk_action"]
            == "archive"
        )
    ]

    archive_policies.sort(
        key=lambda policy: (
            sender_counts.get(
                policy["sender"].lower(),
                0
            )
        ),
        reverse=True,
    )

    if not archive_policies:
        print("None")
    else:
        for policy in archive_policies:
            sender = policy["sender"]

            count = sender_counts.get(
                sender.lower(),
                0
            )

            confidence = policy["confidence"]

            print(
                f"{count:>6,}  "
                f"{confidence:>6.0%}  "
                f"{sender}"
            )

    # ---------------------------------------------------------
    # Individual classification senders
    # ---------------------------------------------------------

    print()
    print("=" * 78)
    print("SENDERS REQUIRING INDIVIDUAL CLASSIFICATION")
    print("=" * 78)

    individual_policies.sort(
        key=lambda policy: (
            sender_counts.get(
                policy["sender"].lower(),
                0
            )
        ),
        reverse=True,
    )

    for policy in individual_policies:
        sender = policy["sender"]

        count = sender_counts.get(
            sender.lower(),
            0
        )

        confidence = policy["confidence"]

        print(
            f"{count:>6,}  "
            f"{confidence:>6.0%}  "
            f"{policy['category']:<20}  "
            f"{sender}"
        )

    print()
    print("=" * 78)
    print("REPORT COMPLETE")
    print("=" * 78)
    print()
    print("No Gmail messages were modified.")
    print("No OpenAI API calls were made.")