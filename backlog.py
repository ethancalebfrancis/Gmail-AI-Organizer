from collections import Counter
from datetime import datetime
from email.utils import parseaddr

from backlog_cache import (
    get_cached_message_ids,
    initialize_backlog_cache,
    save_backlog_metadata,
    set_cache_meta,
)
from config import (
    BACKLOG_PAGE_SIZE,
    BACKLOG_SCAN_LIMIT,
    BACKLOG_TOP_DOMAINS,
    BACKLOG_TOP_SENDERS,
)
from database import get_processed_email_ids
from gmail_service import (
    get_message_metadata,
    list_all_messages,
)


GMAIL_CATEGORY_LABELS = {
    "CATEGORY_PERSONAL": "Primary",
    "CATEGORY_PROMOTIONS": "Promotions",
    "CATEGORY_SOCIAL": "Social",
    "CATEGORY_UPDATES": "Updates",
    "CATEGORY_FORUMS": "Forums",
}


def extract_sender_email(sender_raw):
    """
    Extract the actual email address from a Gmail From header.

    Example:

    Amazon.com <shipment-tracking@amazon.com>

    becomes:

    shipment-tracking@amazon.com
    """

    _, email_address = parseaddr(
        sender_raw
    )

    return email_address.lower().strip()


def extract_domain(email_address):
    """
    Extract a domain from an email address.
    """

    if "@" not in email_address:
        return "unknown"

    return (
        email_address
        .rsplit("@", 1)[-1]
        .lower()
        .strip()
    )


def determine_gmail_category(label_ids):
    """
    Convert Gmail category labels into readable names.
    """

    for label_id, category_name in (
        GMAIL_CATEGORY_LABELS.items()
    ):
        if label_id in label_ids:
            return category_name

    return "Uncategorized"


def internal_date_to_datetime(
    internal_date
):
    """
    Convert Gmail's millisecond internalDate to datetime.
    """

    if not internal_date:
        return None

    try:
        timestamp = (
            int(internal_date) / 1000
        )

        return datetime.fromtimestamp(
            timestamp
        )

    except (ValueError, TypeError):
        return None


def print_counter(
    title,
    counter,
    limit,
):
    """
    Print the most common values in a Counter.
    """

    print()
    print(title)
    print("-" * 70)

    if not counter:
        print("No data.")
        return

    for position, (
        value,
        count,
    ) in enumerate(
        counter.most_common(limit),
        start=1,
    ):
        print(
            f"{position:>3}. "
            f"{count:>6,}  "
            f"{value}"
        )


def run_backlog_scan(service):
    """
    Analyze the historical Gmail mailbox without modifying it.
    """

    print()
    print("=" * 70)
    print("GMAIL AI ORGANIZER — BACKLOG SCAN")
    print("=" * 70)

    print()
    print(
        "This scan is READ ONLY."
    )

    print(
        "No Gmail messages will be modified."
    )

    print(
        "No OpenAI classifications will be performed."
    )

    print()

    if BACKLOG_SCAN_LIMIT is None:
        print(
            "Scan scope: Entire Gmail mailbox"
        )
    else:
        print(
            f"Scan limit: "
            f"{BACKLOG_SCAN_LIMIT:,} messages"
        )

    print()
    print("Discovering Gmail messages...")

    initialize_backlog_cache()

    cached_ids = get_cached_message_ids()

    print(
        f"Metadata already cached: "
        f"{len(cached_ids):,}"
    )
    print()
    messages = list_all_messages(
        service,
        max_messages=BACKLOG_SCAN_LIMIT,
        page_size=BACKLOG_PAGE_SIZE,
    )

    total_messages = len(messages)

    if not messages:
        print("No messages found.")
        return

    print()
    print(
        f"Found {total_messages:,} messages."
    )

    print()
    print(
        "Loading organizer history..."
    )

    processed_ids = (
        get_processed_email_ids()
    )

    sender_counter = Counter()
    domain_counter = Counter()
    category_counter = Counter()
    inbox_counter = Counter()

    processed_count = 0
    unprocessed_count = 0

    oldest_date = None
    newest_date = None

    metadata_errors = 0

    print()
    print(
        "Analyzing message metadata..."
    )
    print()

    for index, message in enumerate(
        messages,
        start=1,
    ):
        message_id = message["id"]

        try:
            if message_id in cached_ids:
                continue

            metadata = (
                get_message_metadata(
                    service,
                    message_id,
                )
            )

            sender = extract_sender_email(
                metadata["sender_raw"]
            )

            if not sender:
                sender = "unknown"

            domain = extract_domain(
                sender
            )

            sender_counter[sender] += 1
            domain_counter[domain] += 1

            gmail_category = (
                determine_gmail_category(
                    metadata["label_ids"]
                )
            )
            save_backlog_metadata(
                email_id=message_id,
                sender=sender,
                domain=domain,
                subject=metadata["subject"],
                gmail_category=gmail_category,
                in_inbox=(
                        "INBOX"
                        in metadata["label_ids"]
                ),
                internal_date=metadata["internal_date"],
            )

            category_counter[
                gmail_category
            ] += 1

            if (
                "INBOX"
                in metadata["label_ids"]
            ):
                inbox_counter["Inbox"] += 1
            else:
                inbox_counter[
                    "Not in Inbox"
                ] += 1

            if message_id in processed_ids:
                processed_count += 1
            else:
                unprocessed_count += 1

            message_date = (
                internal_date_to_datetime(
                    metadata["internal_date"]
                )
            )

            if message_date:
                if (
                    oldest_date is None
                    or message_date
                    < oldest_date
                ):
                    oldest_date = message_date

                if (
                    newest_date is None
                    or message_date
                    > newest_date
                ):
                    newest_date = message_date

        except Exception as error:
            metadata_errors += 1

            print()
            print(
                f"ERROR reading "
                f"{message_id}: {error}"
            )

        if (
            index % 100 == 0
            or index == total_messages
        ):
            print(
                f"\rAnalyzed "
                f"{index:,}/{total_messages:,} "
                f"messages...",
                end="",
                flush=True,
            )

    print()
    print()

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    print("=" * 70)
    print("MAILBOX OVERVIEW")
    print("=" * 70)

    print(
        f"Messages discovered:      "
        f"{total_messages:,}"
    )

    print(
        f"Already processed:        "
        f"{processed_count:,}"
    )

    print(
        f"Unprocessed backlog:      "
        f"{unprocessed_count:,}"
    )

    if total_messages:
        percent_processed = (
            processed_count
            / total_messages
            * 100
        )

        print(
            f"Organizer coverage:       "
            f"{percent_processed:.1f}%"
        )

    print(
        f"Metadata errors:           "
        f"{metadata_errors:,}"
    )

    if oldest_date:
        print(
            f"Oldest message:            "
            f"{oldest_date.strftime('%Y-%m-%d')}"
        )

    if newest_date:
        print(
            f"Newest message:            "
            f"{newest_date.strftime('%Y-%m-%d')}"
        )

    # ---------------------------------------------------------
    # GMAIL LOCATION
    # ---------------------------------------------------------

    print_counter(
        "GMAIL LOCATION",
        inbox_counter,
        10,
    )

    # ---------------------------------------------------------
    # GMAIL CATEGORIES
    # ---------------------------------------------------------

    print_counter(
        "GMAIL CATEGORY BREAKDOWN",
        category_counter,
        10,
    )

    # ---------------------------------------------------------
    # SENDERS
    # ---------------------------------------------------------

    print_counter(
        "TOP SENDERS",
        sender_counter,
        BACKLOG_TOP_SENDERS,
    )

    # ---------------------------------------------------------
    # DOMAINS
    # ---------------------------------------------------------

    print_counter(
        "TOP DOMAINS",
        domain_counter,
        BACKLOG_TOP_DOMAINS,
    )

    print()
    print("=" * 70)
    print("BACKLOG SCAN COMPLETE")
    print("=" * 70)

    print()
    print(
        "No Gmail messages were modified."
    )

    print(
        "No OpenAI API calls were made."
    )

    set_cache_meta(
        "last_full_scan_at",
        datetime.now().isoformat(),
    )