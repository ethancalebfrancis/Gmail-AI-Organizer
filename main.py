"""Command-line entry point for Gmail AI Organizer."""

import sys

from backlog import run_backlog_scan
from backlog_analysis import run_backlog_analysis
from backlog_bulk import run_backlog_bulk_preview
from cleanup import run_cleanup
from gmail_service import get_gmail_service
from historical_classifier import (
    run_phase3_analysis,
    run_phase3_classification_live,
    run_phase3_classification_preview,
)
from historical_pattern_analysis import run_historical_pattern_analysis
from historical_pattern_policy import run_pattern_policy_preview
from historical_processor import run_historical_batch, run_historical_preview
from inbox_processor import run_inbox_batch
from learning import analyze_senders
from phase3_dashboard import run_phase3_dashboard
from production_runner import run_auto, run_once
from sender_policy_preview import run_sender_policy_preview
from sender_policy_report import run_sender_policy_report
from backlog_cache import clear_sender_policies
from database import initialize_database, migrate_database


def _confirm_live(message):
    print(message)
    return input("Type LIVE to continue: ").strip() == "LIVE"


def run_learning_mode():
    initialize_database()
    migrate_database()
    recommendations = analyze_senders()
    if not recommendations:
        print("No new sender-rule recommendations yet.")
        return
    for item in recommendations:
        print(
            f"{item['sender']} | {item['category']} | {item['action']} | "
            f"{item['consistency']:.0%} | {item['emails']} emails"
        )


def main():
    args = sys.argv[1:]

    if not args:
        print("Gmail AI Organizer — Inbox")
        service = get_gmail_service()
        run_inbox_batch(service)
        return

    if len(args) > 1:
        print("ERROR: Use one command-line mode at a time.")
        return

    command = args[0]

    if command == "--auto":
        run_auto()
    elif command == "--once":
        run_once(verbose=True)
    elif command == "--cleanup":
        run_cleanup(get_gmail_service())
    elif command == "--phase3-dashboard":
        run_phase3_dashboard()
    elif command == "--learn":
        run_learning_mode()
    elif command == "--backlog-scan":
        run_backlog_scan(get_gmail_service())
    elif command == "--backlog-analyze":
        run_backlog_analysis()
    elif command == "--backlog-bulk-preview":
        run_backlog_bulk_preview()
    elif command == "--sender-policy-preview":
        run_sender_policy_preview()
    elif command == "--sender-policy-report":
        run_sender_policy_report()
    elif command == "--reset-sender-policies":
        clear_sender_policies()
        print("Sender policy analysis reset.")
    elif command == "--historical-patterns":
        run_historical_pattern_analysis()
    elif command == "--historical-pattern-policy-preview":
        run_pattern_policy_preview(limit=1000)
    elif command == "--historical-preview":
        run_historical_preview()
    elif command == "--historical-live":
        if _confirm_live(
            "WARNING: This will modify Gmail using approved bulk historical policies."
        ):
            run_historical_batch()
        else:
            print("Cancelled. No Gmail changes were made.")
    elif command == "--historical-classify-preview":
        run_phase3_analysis()
    elif command == "--historical-classify-run-preview":
        run_phase3_classification_preview()
    elif command == "--historical-classify-live":
        if _confirm_live(
            "WARNING: This will classify and organize a live historical batch."
        ):
            run_phase3_classification_live()
        else:
            print("Cancelled. No Gmail changes were made.")
    else:
        print(f"ERROR: Unknown command-line option: {command}")
        print("No Gmail changes were made.")


if __name__ == "__main__":
    main()
