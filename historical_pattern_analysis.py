from backlog_cache import (
    get_cached_messages,
)

from historical_pattern_rules import (
    analyze_sender_subjects,
)


MIN_MESSAGES = 5
MIN_CONSISTENCY = 0.90
DISPLAY_LIMIT = 100


def run_historical_pattern_analysis():

    print()
    print("=" * 78)
    print(
        "GMAIL AI ORGANIZER — "
        "SUBJECT PATTERN ANALYSIS"
    )
    print("=" * 78)

    print()
    print("READ ONLY")
    print("Gmail will NOT be modified.")
    print("OpenAI will NOT be called.")
    print()

    print(
        "Loading cached historical messages..."
    )

    messages = get_cached_messages()

    print(
        f"Messages loaded: "
        f"{len(messages):,}"
    )

    print()
    print(
        "Analyzing sender + subject patterns..."
    )

    patterns = analyze_sender_subjects(
        messages
    )

    strong_patterns = [
        pattern
        for pattern in patterns
        if (
            pattern["messages"]
            >= MIN_MESSAGES
            and
            pattern["consistency"]
            >= MIN_CONSISTENCY
        )
    ]

    print()
    print(
        f"Patterns discovered: "
        f"{len(patterns):,}"
    )

    print(
        f"Strong patterns:     "
        f"{len(strong_patterns):,}"
    )

    print()
    print("=" * 78)
    print("STRONG SUBJECT PATTERNS")
    print("=" * 78)

    for number, pattern in enumerate(
        strong_patterns[:DISPLAY_LIMIT],
        start=1,
    ):

        print()

        print(
            f"[{number}]"
        )

        print(
            f"SENDER:      "
            f"{pattern['sender']}"
        )

        print(
            f"SIGNATURE:   "
            f"{pattern['signature']}"
        )

        print(
            f"MESSAGES:    "
            f"{pattern['messages']:,}"
        )

        print(
            f"GMAIL TYPE:  "
            f"{pattern['gmail_category']}"
        )

        print(
            f"CONSISTENCY: "
            f"{pattern['consistency']:.1%}"
        )

        print("EXAMPLES:")

        for subject in pattern["examples"]:
            print(
                f"  - {subject}"
            )

    print()
    print("=" * 78)
    print("ANALYSIS COMPLETE")
    print("=" * 78)

    print()
    print(
        "NO GMAIL MESSAGES WERE MODIFIED."
    )

    print(
        "NO OPENAI API CALLS WERE MADE."
    )