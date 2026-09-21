"""Quarantine cleanup.

Potential trash is never removed immediately. After the retention window this
module re-checks Gmail state and only then moves eligible messages to Gmail
Trash. Gmail performs its own Trash retention afterward.
"""

from datetime import datetime, timedelta, timezone

from config import CLEANUP_LIVE, PROTECTED_CATEGORIES, TRASH_QUARANTINE_DAYS
from database import (
    get_expired_historical_quarantines,
    get_trash_candidates,
    update_historical_action_status,
    update_processed_cleanup_status,
)
from gmail_service import (
    get_label_id,
    get_message_label_ids,
    list_messages_with_label,
    remove_label,
    trash_message,
)

TRASH_LABEL = "AI/Trash Candidates"
PROTECTED_AI_LABELS = ["AI/Important", "AI/Needs Action", "AI/Needs Review"]


def _say(verbose, message=""):
    if verbose:
        print(message)


def _protected_label_ids(service):
    return {
        label_id
        for name in PROTECTED_AI_LABELS
        if (label_id := get_label_id(service, name))
    }


def run_cleanup(service, verbose=True):
    """Move expired, still-safe quarantine candidates to Gmail Trash."""
    now_local = datetime.now()
    cutoff = now_local - timedelta(days=TRASH_QUARANTINE_DAYS)

    # Important: list_messages_with_label pages the entire label, not just the
    # first 500 rows. Otherwise large quarantines could be mistaken for rescues.
    gmail_candidate_ids = {
        message["id"] for message in list_messages_with_label(service, TRASH_LABEL)
    }
    protected_label_ids = _protected_label_ids(service)

    normal_candidates = get_trash_candidates()
    stats = {
        "database_candidates": len(normal_candidates),
        "still_quarantined": 0,
        "eligible": 0,
        "trashed": 0,
        "rescued": 0,
        "skipped": 0,
        "historical_expired": 0,
        "historical_trashed": 0,
        "historical_skipped": 0,
        "errors": 0,
    }

    _say(verbose, "\n" + "=" * 70)
    _say(verbose, "TRASH QUARANTINE CLEANUP")
    _say(verbose, "=" * 70)
    _say(verbose, f"Mode: {'LIVE' if CLEANUP_LIVE else 'PREVIEW'}")
    _say(verbose, f"Quarantine period: {TRASH_QUARANTINE_DAYS} days\n")

    for candidate in normal_candidates:
        email_id = candidate["email_id"]
        try:
            processed_at = datetime.fromisoformat(candidate["processed_at"])

            if email_id not in gmail_candidate_ids:
                update_processed_cleanup_status(email_id, "rescued")
                stats["rescued"] += 1
                continue

            if candidate["category"] in PROTECTED_CATEGORIES or candidate["action_required"]:
                remove_label(service, email_id, TRASH_LABEL)
                update_processed_cleanup_status(email_id, "protected")
                stats["skipped"] += 1
                continue

            if processed_at > cutoff:
                stats["still_quarantined"] += 1
                continue

            label_ids = set(get_message_label_ids(service, email_id))
            if "STARRED" in label_ids or "INBOX" in label_ids:
                remove_label(service, email_id, TRASH_LABEL)
                update_processed_cleanup_status(email_id, "rescued")
                stats["rescued"] += 1
                continue

            if label_ids & protected_label_ids:
                remove_label(service, email_id, TRASH_LABEL)
                update_processed_cleanup_status(email_id, "protected")
                stats["skipped"] += 1
                continue

            stats["eligible"] += 1
            if CLEANUP_LIVE:
                trash_message(service, email_id)
                update_processed_cleanup_status(
                    email_id,
                    "trashed",
                    trashed_at=datetime.now(timezone.utc).isoformat(),
                )
                stats["trashed"] += 1

        except Exception as error:
            stats["errors"] += 1
            _say(verbose, f"ERROR cleaning {email_id}: {error}")

    historical_candidates = get_expired_historical_quarantines(
        datetime.now(timezone.utc).isoformat()
    )
    stats["historical_expired"] = len(historical_candidates)

    for candidate in historical_candidates:
        email_id = candidate["email_id"]
        try:
            if email_id not in gmail_candidate_ids:
                update_historical_action_status(
                    email_id,
                    "rescued",
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
                stats["historical_skipped"] += 1
                continue

            if candidate["policy_category"] in PROTECTED_CATEGORIES:
                remove_label(service, email_id, TRASH_LABEL)
                update_historical_action_status(
                    email_id,
                    "protected",
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
                stats["historical_skipped"] += 1
                continue

            label_ids = set(get_message_label_ids(service, email_id))
            if "STARRED" in label_ids or "INBOX" in label_ids or label_ids & protected_label_ids:
                remove_label(service, email_id, TRASH_LABEL)
                update_historical_action_status(
                    email_id,
                    "rescued",
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
                stats["historical_skipped"] += 1
                continue

            if CLEANUP_LIVE:
                trash_message(service, email_id)
                update_historical_action_status(
                    email_id,
                    "trashed",
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
                stats["historical_trashed"] += 1

        except Exception as error:
            stats["errors"] += 1
            update_historical_action_status(email_id, "error", error_message=str(error))
            _say(verbose, f"ERROR cleaning historical {email_id}: {error}")

    _say(verbose, "=" * 70)
    _say(verbose, f"Quarantined:          {stats['still_quarantined']:,}")
    _say(verbose, f"Moved to Gmail Trash: {stats['trashed'] + stats['historical_trashed']:,}")
    _say(verbose, f"Rescued/protected:    {stats['rescued'] + stats['skipped'] + stats['historical_skipped']:,}")
    _say(verbose, f"Errors:               {stats['errors']:,}")
    _say(verbose, "=" * 70)

    return stats
