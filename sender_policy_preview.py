import time

from backlog_cache import (
    get_sender_analysis,
    get_sender_sample_subjects,
    initialize_sender_policy_table,
    save_sender_policy,
    sender_policy_exists,
)
from config import (
    BACKLOG_BULK_MIN_EMAILS,
    BACKLOG_BULK_PROMOTION_CONSISTENCY,
    SENDER_POLICY_CONFIDENCE_THRESHOLD,
    SENDER_POLICY_MAX_PER_RUN,
    SENDER_POLICY_OPENAI_DELAY_SECONDS,
    SENDER_POLICY_SAMPLE_SIZE,
    PROTECTED_CATEGORIES,
)
from sender_policy import analyze_sender_policy


def run_sender_policy_preview(limit=None, verbose=True):
    """Analyze promotion-heavy senders and persist safe sender policies.

    Despite the historical function name, this never modifies Gmail; it only
    stores sender-policy decisions in the local backlog cache.
    """
    initialize_sender_policy_table()
    limit = limit or SENDER_POLICY_MAX_PER_RUN

    rows = get_sender_analysis()
    candidates = []

    for row in rows:
        total = row["total"]
        if total < BACKLOG_BULK_MIN_EMAILS:
            continue

        promotions = row["promotions_count"]
        consistency = promotions / total if total else 0
        if consistency < BACKLOG_BULK_PROMOTION_CONSISTENCY:
            continue

        if sender_policy_exists(row["sender"]):
            continue

        candidates.append(row)

    candidates.sort(key=lambda row: row["total"], reverse=True)
    candidates = candidates[:limit]

    stats = {"selected": len(candidates), "saved": 0, "errors": 0}

    if verbose:
        print("\n" + "=" * 78)
        print("AI SENDER POLICY ANALYSIS")
        print("=" * 78)
        print(f"Senders selected: {len(candidates):,}")
        print("Gmail will NOT be modified.\n")

    for index, row in enumerate(candidates, start=1):
        sender = row["sender"]
        domain = row["domain"]
        subjects = get_sender_sample_subjects(sender, SENDER_POLICY_SAMPLE_SIZE)

        try:
            result = analyze_sender_policy(sender, domain, subjects)

            if (
                result.get("bulk_action") == "trash_candidate"
                and result.get("category") in PROTECTED_CATEGORIES
            ):
                result["bulk_safe"] = False
                result["bulk_action"] = "individual_classification"
                result["reason"] = (
                    "Safety override: protected categories are never eligible "
                    "for sender-wide bulk trash. "
                    f"Original reason: {result['reason']}"
                )

            if (
                result["bulk_safe"]
                and result["confidence"] < SENDER_POLICY_CONFIDENCE_THRESHOLD
            ):
                result["bulk_safe"] = False
                result["bulk_action"] = "individual_classification"
                result["reason"] = (
                    "Safety override: model confidence was below the required "
                    f"{SENDER_POLICY_CONFIDENCE_THRESHOLD:.0%} threshold. "
                    f"Original reason: {result['reason']}"
                )

            save_sender_policy(sender, domain, result)
            stats["saved"] += 1

            if verbose:
                print(
                    f"[{index}/{len(candidates)}] {sender} -> "
                    f"{result['bulk_action']} ({result['confidence']:.0%})"
                )

            if SENDER_POLICY_OPENAI_DELAY_SECONDS > 0:
                time.sleep(SENDER_POLICY_OPENAI_DELAY_SECONDS)

        except Exception as error:
            stats["errors"] += 1
            if verbose:
                print(f"ERROR analyzing {sender}: {error}")

    if verbose:
        print("=" * 78)
        print(
            f"Sender policies saved: {stats['saved']:,} | "
            f"Errors: {stats['errors']:,}"
        )
        print("=" * 78)

    return stats
