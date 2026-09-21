from collections import Counter
from datetime import datetime, timedelta, timezone

from backlog_cache import (
    get_historical_policy_candidates,
    sanitize_sender_policies,
)
from config import (
    HISTORICAL_BATCH_SIZE,
    HISTORICAL_PER_SENDER_LIMIT,
    HISTORICAL_QUARANTINE_DAYS,
)
from database import (
    get_historical_action_ids,
    get_processed_email_ids,
    save_historical_action,
)
from gmail_service import (
    archive_message,
    get_gmail_service,
    get_or_create_label,
    quarantine_message,
)


DEFAULT_PREVIEW_LIMIT = 250
DEFAULT_PER_SENDER_LIMIT = 10

TRASH_CANDIDATE_LABEL = "AI/Trash Candidates"
def format_internal_date(value):
    """
    Convert Gmail's cached internal date into
    something readable when possible.
    """

    if not value:
        return "Unknown"

    try:
        timestamp = int(value) / 1000

        return datetime.fromtimestamp(
            timestamp
        ).strftime(
            "%Y-%m-%d"
        )

    except (
        TypeError,
        ValueError,
        OSError,
    ):
        return str(value)


def get_unprocessed_candidates(
    limit=DEFAULT_PREVIEW_LIMIT,
    per_sender_limit=DEFAULT_PER_SENDER_LIMIT,
):
    """Retrieve bulk-safe historical candidates not yet handled.

    The cache is paged until enough unprocessed rows are found so the worker can
    continue through the entire mailbox instead of stalling after early pages.
    """
    processed_ids = get_processed_email_ids()
    historical_ids = get_historical_action_ids()
    excluded_ids = processed_ids | historical_ids

    page_size = max(min(limit * 4, 5000), 1000)
    offset = 0
    sender_counts = Counter()
    selected = []

    while len(selected) < limit:
        rows = get_historical_policy_candidates(
            limit=page_size,
            offset=offset,
        )
        if not rows:
            break

        for candidate in rows:
            email_id = candidate["email_id"]
            sender = (candidate["sender"] or "").lower()

            if email_id in excluded_ids:
                continue
            if sender_counts[sender] >= per_sender_limit:
                continue

            selected.append(candidate)
            sender_counts[sender] += 1
            if len(selected) >= limit:
                break

        offset += len(rows)
        if len(rows) < page_size:
            break

    return selected


def run_historical_preview(
    limit=DEFAULT_PREVIEW_LIMIT,
):
    """
    Preview historical bulk actions.

    READ ONLY.

    This function does NOT:
    - connect to Gmail
    - modify Gmail
    - call OpenAI
    - modify the organizer database
    """

    print()
    print("=" * 78)
    print(
        "GMAIL AI ORGANIZER — "
        "HISTORICAL BULK PREVIEW"
    )
    print("=" * 78)

    print()
    print(
        "READ ONLY — absolutely no Gmail changes."
    )
    print(
        "No OpenAI API calls will be made."
    )
    print()

    candidates = (
        get_unprocessed_candidates(
            limit=limit
        )
    )

    if not candidates:
        print(
            "No unprocessed bulk-safe "
            "historical messages were found."
        )
        print()
        print("=" * 78)
        return

    action_counts = Counter(
        candidate["bulk_action"]
        for candidate in candidates
    )

    sender_counts = Counter(
        candidate["sender"]
        for candidate in candidates
    )

    inbox_counts = Counter(
        bool(candidate["in_inbox"])
        for candidate in candidates
    )

    print(
        f"Preview batch size:       "
        f"{len(candidates):,}"
    )

    print(
        f"Unique senders:           "
        f"{len(sender_counts):,}"
    )

    print(
        f"Currently in Inbox:       "
        f"{inbox_counts.get(True, 0):,}"
    )

    print(
        f"Already outside Inbox:    "
        f"{inbox_counts.get(False, 0):,}"
    )

    print()
    print("-" * 78)
    print("PROPOSED ACTIONS")
    print("-" * 78)

    print(
        f"Trash quarantine:         "
        f"{action_counts.get('trash_candidate', 0):,}"
    )

    print(
        f"Archive:                  "
        f"{action_counts.get('archive', 0):,}"
    )

    print(
        f"Keep:                     "
        f"{action_counts.get('keep', 0):,}"
    )

    print()
    print("-" * 78)
    print("MESSAGES")
    print("-" * 78)

    for number, candidate in enumerate(
        candidates,
        start=1,
    ):
        sender = (
            candidate["sender"]
            or "(Unknown sender)"
        )

        subject = (
            candidate["subject"]
            or "(No subject)"
        )

        action = candidate[
            "bulk_action"
        ]

        confidence = (
            candidate["confidence"]
            or 0
        )

        date = format_internal_date(
            candidate["internal_date"]
        )

        location = (
            "Inbox"
            if candidate["in_inbox"]
            else "Archived"
        )

        print()

        print(
            f"[{number}/{len(candidates)}]"
        )

        print(
            f"FROM:       {sender}"
        )

        print(
            f"SUBJECT:    {subject}"
        )

        print(
            f"DATE:       {date}"
        )

        print(
            f"LOCATION:   {location}"
        )

        print(
            f"CATEGORY:   "
            f"{candidate['policy_category']}"
        )

        print(
            f"ACTION:     {action}"
        )

        print(
            f"CONFIDENCE: "
            f"{confidence:.0%}"
        )

    print()
    print("=" * 78)
    print("PREVIEW SUMMARY")
    print("=" * 78)

    print(
        f"Messages previewed:       "
        f"{len(candidates):,}"
    )

    print(
        f"Trash quarantine:         "
        f"{action_counts.get('trash_candidate', 0):,}"
    )

    print(
        f"Archive:                  "
        f"{action_counts.get('archive', 0):,}"
    )

    print(
        f"Keep:                     "
        f"{action_counts.get('keep', 0):,}"
    )

    print()
    print(
        "NO GMAIL MESSAGES WERE MODIFIED."
    )

    print(
        "NO OPENAI API CALLS WERE MADE."
    )

    print("=" * 78)

def run_historical_batch(
    service=None,
    limit=None,
    per_sender_limit=None,
    verbose=True,
):
    """Process one live batch of approved bulk-safe historical mail."""
    limit = limit or HISTORICAL_BATCH_SIZE
    per_sender_limit = per_sender_limit or HISTORICAL_PER_SENDER_LIMIT
    sanitize_sender_policies()

    candidates = get_unprocessed_candidates(
        limit=limit,
        per_sender_limit=per_sender_limit,
    )

    stats = {
        "candidates": len(candidates),
        "quarantined": 0,
        "archived": 0,
        "kept": 0,
        "errors": 0,
    }

    if verbose:
        print()
        print("=" * 78)
        print("GMAIL AI ORGANIZER — HISTORICAL BULK PROCESSOR")
        print("=" * 78)
        print(f"Batch size: {len(candidates):,}")
        print(f"Trash quarantine: {HISTORICAL_QUARANTINE_DAYS} days")
        print()

    if not candidates:
        if verbose:
            print("No eligible unprocessed historical messages were found.")
        return stats

    if service is None:
        service = get_gmail_service()

    trash_label_id = get_or_create_label(service, TRASH_CANDIDATE_LABEL)

    for number, candidate in enumerate(candidates, start=1):
        email_id = candidate["email_id"]
        action = candidate["bulk_action"]

        if verbose:
            sender = candidate["sender"] or "(Unknown sender)"
            subject = candidate["subject"] or "(No subject)"
            print(f"[{number}/{len(candidates)}] {sender}")
            print(f"    {subject[:100]}")
            print(f"    Action: {action}")

        try:
            if action == "trash_candidate":
                now = datetime.now(timezone.utc)
                quarantine_until = now + timedelta(days=HISTORICAL_QUARANTINE_DAYS)

                quarantine_message(service, email_id, trash_label_id)
                save_historical_action(
                    candidate=candidate,
                    status="quarantined",
                    quarantined_at=now.isoformat(),
                    quarantine_until=quarantine_until.isoformat(),
                )
                stats["quarantined"] += 1

            elif action == "archive":
                archive_message(service, email_id)
                save_historical_action(
                    candidate=candidate,
                    status="completed",
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
                stats["archived"] += 1

            elif action == "keep":
                save_historical_action(
                    candidate=candidate,
                    status="completed",
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
                stats["kept"] += 1

            else:
                raise ValueError(f"Unsupported historical action: {action}")

        except Exception as error:
            stats["errors"] += 1
            if verbose:
                print(f"    ERROR: {error}")

    if verbose:
        print()
        print("=" * 78)
        print("HISTORICAL BATCH COMPLETE")
        print("=" * 78)
        print(f"Candidates:               {stats['candidates']:,}")
        print(f"Quarantined:              {stats['quarantined']:,}")
        print(f"Archived:                 {stats['archived']:,}")
        print(f"Kept:                     {stats['kept']:,}")
        print(f"Errors:                   {stats['errors']:,}")
        print("NO MESSAGES WERE PERMANENTLY DELETED.")
        print("=" * 78)

    return stats
