"""Autonomous Gmail organizer worker.

This is the production path: current Inbox mail is organized continuously while
historical mail is drained in resumable batches. Trash candidates remain in the
quarantine label until cleanup later moves them to Gmail Trash.
"""

import time
from datetime import datetime, timedelta

from cleanup import run_cleanup
from backlog import run_backlog_scan
from backlog_cache import get_cache_meta, sanitize_sender_policies
from config import (
    AUTO_ACTIVE_PAUSE_SECONDS,
    AUTO_BACKLOG_REFRESH_HOURS,
    AUTO_CLEANUP_EVERY_CYCLES,
    AUTO_DASHBOARD_EVERY_CYCLES,
    AUTO_HISTORICAL_BULK_BATCH_SIZE,
    AUTO_HISTORICAL_ENABLED,
    AUTO_IDLE_SECONDS,
    AUTO_INBOX_BATCH_SIZE,
    AUTO_PHASE3_BATCH_SIZE,
    AUTO_PHASE3_ENABLED,
    AUTO_SENDER_POLICY_BATCH_SIZE,
    AUTO_SENDER_POLICY_ENABLED,
    HISTORICAL_PER_SENDER_LIMIT,
)
from database import (
    initialize_database,
    initialize_historical_actions_table,
    initialize_phase3_learning_table,
    initialize_runs_table,
    migrate_database,
)
from gmail_service import get_gmail_service
from historical_classifier import run_phase3_classification_live
from historical_processor import run_historical_batch
from inbox_processor import run_inbox_batch
from phase3_dashboard import get_dashboard_data, run_phase3_dashboard
from sender_policy_preview import run_sender_policy_preview


def initialize_runtime():
    initialize_database()
    migrate_database()
    initialize_runs_table()
    initialize_historical_actions_table()
    initialize_phase3_learning_table()
    sanitize_sender_policies()



def refresh_backlog_if_needed(service, force=False, verbose=True):
    """Refresh cached Gmail metadata at a low cadence.

    The full Gmail ID listing is read-only; only messages that are not already
    cached require metadata fetches. This keeps a long-running worker aware of
    mail that arrived after the original historical scan.
    """
    last_scan = get_cache_meta("last_full_scan_at")
    refresh_due = force or not last_scan

    if last_scan and not force:
        try:
            last_scan_at = datetime.fromisoformat(last_scan)
            refresh_due = (
                datetime.now() - last_scan_at
                >= timedelta(hours=AUTO_BACKLOG_REFRESH_HOURS)
            )
        except (TypeError, ValueError):
            refresh_due = True

    if not refresh_due:
        return False

    if verbose:
        print("\nRefreshing historical mailbox cache...")

    run_backlog_scan(service)
    return True

def run_automatic_cycle(service, cycle_number=1, verbose=True):
    """Run one complete production cycle and return summary counters."""
    summary = {
        "inbox_processed": 0,
        "sender_policies": 0,
        "bulk_processed": 0,
        "phase3_processed": 0,
        "cleanup_trashed": 0,
        "errors": 0,
    }

    if verbose:
        print("\n" + "=" * 78)
        print(f"AUTOMATIC ORGANIZER CYCLE {cycle_number} — {datetime.now():%Y-%m-%d %H:%M:%S}")
        print("=" * 78)

    try:
        refresh_backlog_if_needed(service, verbose=verbose)
    except Exception as exc:
        # A cache-refresh failure should never stop current Inbox processing.
        summary["errors"] += 1
        if verbose:
            print(f"Backlog refresh error: {exc}")

    try:
        inbox = run_inbox_batch(
            service,
            max_new=AUTO_INBOX_BATCH_SIZE,
            verbose=verbose,
        )
        summary["inbox_processed"] = inbox.get("processed", 0)
        summary["errors"] += inbox.get("errors", 0)
    except Exception as exc:
        summary["errors"] += 1
        if verbose:
            print(f"Inbox stage error: {exc}")

    policy_stats = {"selected": 0, "saved": 0, "errors": 0}
    if AUTO_SENDER_POLICY_ENABLED:
        try:
            policy_stats = run_sender_policy_preview(
                limit=AUTO_SENDER_POLICY_BATCH_SIZE,
                verbose=verbose,
            )
            summary["sender_policies"] = policy_stats.get("saved", 0)
            summary["errors"] += policy_stats.get("errors", 0)
        except Exception as exc:
            summary["errors"] += 1
            if verbose:
                print(f"Sender-policy stage error: {exc}")

    if AUTO_HISTORICAL_ENABLED:
        try:
            bulk = run_historical_batch(
                service=service,
                limit=AUTO_HISTORICAL_BULK_BATCH_SIZE,
                per_sender_limit=HISTORICAL_PER_SENDER_LIMIT,
                verbose=verbose,
            )
            summary["bulk_processed"] = (
                bulk.get("quarantined", 0)
                + bulk.get("archived", 0)
                + bulk.get("kept", 0)
            )
            summary["errors"] += bulk.get("errors", 0)
        except Exception as exc:
            summary["errors"] += 1
            if verbose:
                print(f"Historical bulk stage error: {exc}")

    # Finish analyzing promotion-heavy senders before spending per-message API
    # calls on them. Once that queue is empty, Phase 3 drains the remainder.
    if AUTO_PHASE3_ENABLED and policy_stats.get("selected", 0) == 0:
        try:
            phase3 = run_phase3_classification_live(
                limit=AUTO_PHASE3_BATCH_SIZE,
                service=service,
                verbose=verbose,
            )
            summary["phase3_processed"] = phase3.get("processed", 0)
            summary["errors"] += phase3.get("errors", 0)
        except Exception as exc:
            summary["errors"] += 1
            if verbose:
                print(f"Phase 3 stage error: {exc}")

    if cycle_number == 1 or cycle_number % AUTO_CLEANUP_EVERY_CYCLES == 0:
        try:
            cleanup = run_cleanup(service, verbose=verbose)
            summary["cleanup_trashed"] = (
                cleanup.get("trashed", 0) + cleanup.get("historical_trashed", 0)
            )
            summary["errors"] += cleanup.get("errors", 0)
        except Exception as exc:
            summary["errors"] += 1
            if verbose:
                print(f"Cleanup stage error: {exc}")

    if verbose and (
        cycle_number == 1 or cycle_number % AUTO_DASHBOARD_EVERY_CYCLES == 0
    ):
        run_phase3_dashboard()

    return summary


def run_once(verbose=True):
    initialize_runtime()
    service = get_gmail_service()
    return run_automatic_cycle(service, cycle_number=1, verbose=verbose)


def run_auto():
    """Run continuously until stopped; after backlog completion, poll the Inbox."""
    initialize_runtime()
    service = get_gmail_service()
    cycle = 0

    print("Gmail AI Organizer — automatic mode started.")
    print("Press Ctrl+C to stop safely. Completed messages are resumable.")

    try:
        while True:
            cycle += 1
            summary = run_automatic_cycle(service, cycle_number=cycle, verbose=True)
            dashboard = get_dashboard_data()

            active_work = (
                summary["inbox_processed"]
                + summary["sender_policies"]
                + summary["bulk_processed"]
                + summary["phase3_processed"]
            )

            if dashboard["remaining"] == 0 and active_work == 0:
                print(f"\nHistorical backlog complete. Checking Inbox again in {AUTO_IDLE_SECONDS}s.")
                time.sleep(AUTO_IDLE_SECONDS)
            elif active_work == 0:
                print(f"\nNo work completed this cycle. Retrying in {AUTO_IDLE_SECONDS}s.")
                time.sleep(AUTO_IDLE_SECONDS)
            else:
                time.sleep(AUTO_ACTIVE_PAUSE_SECONDS)

    except KeyboardInterrupt:
        print("\nAutomatic organizer stopped safely.")
