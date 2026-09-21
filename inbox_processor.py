"""Processing for current Inbox messages."""

import time
from collections import Counter

from action_policy import determine_action
from classifier import classify_email
from config import MAX_EMAILS, MAX_NEW_EMAILS_PER_RUN, PHASE3_OPENAI_DELAY_SECONDS
from database import (
    initialize_database,
    initialize_historical_actions_table,
    initialize_runs_table,
    is_processed,
    migrate_database,
    save_result,
    save_run_stats,
)
from gmail_service import (
    apply_label,
    archive_message,
    get_message,
    list_inbox_messages,
    quarantine_message,
    get_or_create_label,
)
from rules import check_local_rule


def _process_one(service, message, verbose=True):
    email = get_message(service, message["id"])
    result = check_local_rule(email)
    used_openai = result is None

    if used_openai:
        result = classify_email(email)
        result["classification_source"] = "openai"

    final_action = determine_action(result)

    if verbose:
        print("\n" + "-" * 70)
        print(f"FROM: {email['sender_raw']}")
        print(f"SUBJECT: {email['subject']}")
        print(f"CATEGORY: {result['category']}")
        print(f"STATE: {result.get('email_state', 'unknown')}")
        print(f"CONFIDENCE: {result['confidence']:.0%}")
        print(f"FINAL: {final_action}")

    apply_label(service, email["id"], f"AI/{result['category']}")

    if result["importance"] == "high":
        apply_label(service, email["id"], "AI/Important")

    if result["action_required"]:
        apply_label(service, email["id"], "AI/Needs Action")

    if final_action == "review":
        apply_label(service, email["id"], "AI/Needs Review")
    elif final_action == "trash_candidate":
        trash_label_id = get_or_create_label(service, "AI/Trash Candidates")
        quarantine_message(service, email["id"], trash_label_id)
    elif final_action == "archive":
        archive_message(service, email["id"])

    # Gmail action succeeds before the result is marked processed.
    save_result(email, result, final_action)
    return used_openai, final_action


def run_inbox_batch(service, max_new=None, scan_limit=None, verbose=True):
    """Organize one batch of current Inbox mail and return counters."""
    initialize_database()
    migrate_database()
    initialize_historical_actions_table()
    initialize_runs_table()

    max_new = max_new or MAX_NEW_EMAILS_PER_RUN
    scan_limit = scan_limit or max(MAX_EMAILS, max_new * 5)
    messages = list_inbox_messages(service, scan_limit)

    stats = Counter(
        scanned=len(messages),
        already_processed=0,
        processed=0,
        openai=0,
        local_rules=0,
        keep=0,
        archive=0,
        trash_candidate=0,
        review=0,
        errors=0,
    )

    start = time.time()

    for message in messages:
        if is_processed(message["id"]):
            stats["already_processed"] += 1
            continue
        if stats["processed"] >= max_new:
            break

        try:
            used_openai, final_action = _process_one(service, message, verbose=verbose)
            stats["processed"] += 1
            stats["openai" if used_openai else "local_rules"] += 1
            stats[final_action] += 1
            if used_openai and PHASE3_OPENAI_DELAY_SECONDS > 0:
                time.sleep(PHASE3_OPENAI_DELAY_SECONDS)
        except Exception as error:
            stats["errors"] += 1
            if verbose:
                print(f"ERROR processing {message['id']}: {error}")

    runtime = time.time() - start
    save_run_stats(stats, runtime)

    if verbose:
        print("\n" + "=" * 70)
        print("INBOX BATCH SUMMARY")
        print("=" * 70)
        print(f"Scanned:          {stats['scanned']:,}")
        print(f"Processed:        {stats['processed']:,}")
        print(f"OpenAI:           {stats['openai']:,}")
        print(f"Local rules:      {stats['local_rules']:,}")
        print(f"Kept:             {stats['keep']:,}")
        print(f"Archived:         {stats['archive']:,}")
        print(f"Quarantined:      {stats['trash_candidate']:,}")
        print(f"Needs review:     {stats['review']:,}")
        print(f"Errors:           {stats['errors']:,}")
        print("=" * 70)

    return dict(stats)
