from collections import Counter

from backlog_cache import (
    get_individual_classification_candidates,
)
from database import (
    get_historical_action_ids,
    get_processed_email_ids,
)
from historical_rules import (
    check_historical_rule,
)
from historical_pattern_policy import (
    get_pattern_classification,
)
from rules import check_local_rule
from phase3_learning import get_learned_pattern_classification


DEFAULT_ANALYSIS_LIMIT = 1000


def build_minimal_email(candidate):
    """
    Convert cached backlog metadata into the minimum email
    structure required by the rule systems.

    No Gmail API request is performed here.
    """

    return {
        "id": candidate["email_id"],
        "sender": candidate["sender"] or "",
        "sender_raw": candidate["sender"] or "",
        "subject": candidate["subject"] or "",
        "body": "",
        "snippet": "",
    }


def get_phase3_candidates(
    limit=DEFAULT_ANALYSIS_LIMIT,
):
    """
    Retrieve Phase 3 candidates while excluding anything already handled.

    Results are paged through the entire backlog cache so processing cannot
    stall after the newest rows have already been handled.
    """

    processed_ids = get_processed_email_ids()
    historical_ids = get_historical_action_ids()
    excluded_ids = processed_ids | historical_ids

    page_size = max(min(limit * 2, 5000), 1000)
    offset = 0
    candidates = []

    while len(candidates) < limit:
        rows = get_individual_classification_candidates(
            limit=page_size,
            offset=offset,
        )

        if not rows:
            break

        for row in rows:
            if row["email_id"] in excluded_ids:
                continue
            candidates.append(row)
            if len(candidates) >= limit:
                break

        offset += len(rows)

        if len(rows) < page_size:
            break

    return candidates


def analyze_phase3_candidates(
    limit=DEFAULT_ANALYSIS_LIMIT,
):
    """
    READ-ONLY analysis of Phase 3 candidates.

    Processing order:

    1. Existing local sender/domain rules
    2. Sender + subject pattern policies
    3. Conservative historical rules
    4. OpenAI would be required

    No Gmail modifications.
    No OpenAI calls.
    """

    candidates = get_phase3_candidates(
        limit=limit
    )

    stats = Counter()

    examples = {
        "local_rule": [],
        "pattern_policy": [],
        "historical_rule": [],
        "needs_classification": [],
    }

    for candidate in candidates:

        stats["total"] += 1

        email = build_minimal_email(
            candidate
        )

        # =====================================================
        # 1. EXISTING LOCAL RULE
        # =====================================================

        local_result = check_local_rule(
            email
        )

        if local_result:

            stats["local_rule"] += 1

            action = local_result[
                "recommended_action"
            ]

            stats[
                f"local_{action}"
            ] += 1

            if (
                len(examples["local_rule"])
                < 20
            ):
                examples[
                    "local_rule"
                ].append(
                    (
                        candidate,
                        local_result,
                    )
                )

            continue

        # =====================================================
        # 2. SENDER + SUBJECT PATTERN POLICY
        # =====================================================

        pattern_result = (
            get_pattern_classification(
                email
            )
        )

        if pattern_result:

            stats["pattern_policy"] += 1

            action = pattern_result[
                "recommended_action"
            ]

            stats[
                f"pattern_{action}"
            ] += 1

            if (
                len(
                    examples[
                        "pattern_policy"
                    ]
                )
                < 30
            ):
                examples[
                    "pattern_policy"
                ].append(
                    (
                        candidate,
                        pattern_result,
                    )
                )

            continue

        # =====================================================
        # 3. CONSERVATIVE HISTORICAL RULE
        # =====================================================

        historical_result = (
            check_historical_rule(
                email,
                gmail_category=candidate[
                    "gmail_category"
                ],
            )
        )

        if historical_result:

            stats["historical_rule"] += 1

            action = historical_result[
                "recommended_action"
            ]

            stats[
                f"historical_{action}"
            ] += 1

            if (
                len(
                    examples[
                        "historical_rule"
                    ]
                )
                < 30
            ):
                examples[
                    "historical_rule"
                ].append(
                    (
                        candidate,
                        historical_result,
                    )
                )

            continue

        # =====================================================
        # 4. WOULD REQUIRE OPENAI
        # =====================================================

        stats[
            "needs_classification"
        ] += 1

        if (
            len(
                examples[
                    "needs_classification"
                ]
            )
            < 30
        ):
            examples[
                "needs_classification"
            ].append(
                candidate
            )

    return (
        candidates,
        stats,
        examples,
    )


def run_phase3_analysis():
    """
    Show how much historical mail can already be handled
    without OpenAI.
    """

    print()
    print("=" * 78)
    print(
        "GMAIL AI ORGANIZER — "
        "PHASE 3 ANALYSIS"
    )
    print("=" * 78)

    print()
    print("READ ONLY")
    print("Gmail will NOT be modified.")
    print("OpenAI will NOT be called.")
    print()

    (
        candidates,
        stats,
        examples,
    ) = analyze_phase3_candidates()

    # =========================================================
    # SUMMARY
    # =========================================================

    print(
        f"Candidates analyzed:       "
        f"{stats['total']:,}"
    )

    print()

    print(
        f"Existing local rules:      "
        f"{stats['local_rule']:,}"
    )

    print(
        f"  → Trash candidates:      "
        f"{stats['local_trash_candidate']:,}"
    )

    print(
        f"  → Archive:               "
        f"{stats['local_archive']:,}"
    )

    print(
        f"  → Keep:                  "
        f"{stats['local_keep']:,}"
    )

    print()

    print(
        f"Pattern policy matches:    "
        f"{stats['pattern_policy']:,}"
    )

    print(
        f"  → Trash candidates:      "
        f"{stats['pattern_trash_candidate']:,}"
    )

    print(
        f"  → Archive:               "
        f"{stats['pattern_archive']:,}"
    )

    print(
        f"  → Keep:                  "
        f"{stats['pattern_keep']:,}"
    )

    print()

    print(
        f"Historical rules:          "
        f"{stats['historical_rule']:,}"
    )

    print(
        f"  → Trash candidates:      "
        f"{stats['historical_trash_candidate']:,}"
    )

    print(
        f"  → Archive:               "
        f"{stats['historical_archive']:,}"
    )

    print(
        f"  → Keep:                  "
        f"{stats['historical_keep']:,}"
    )

    print()

    print(
        f"Need OpenAI/classifier:    "
        f"{stats['needs_classification']:,}"
    )

    # =========================================================
    # API AVOIDANCE
    # =========================================================

    if stats["total"]:

        avoided_count = (
            stats["local_rule"]
            + stats["pattern_policy"]
            + stats["historical_rule"]
        )

        avoided = (
            avoided_count
            / stats["total"]
        )

        print(
            f"Total API avoidance:       "
            f"{avoided:.1%}"
        )

        print(
            f"API calls avoided:         "
            f"{avoided_count:,}"
        )

    # =========================================================
    # LOCAL RULE EXAMPLES
    # =========================================================

    print()
    print("-" * 78)
    print("LOCAL RULE EXAMPLES")
    print("-" * 78)

    if not examples["local_rule"]:
        print("None found.")

    for candidate, result in (
        examples["local_rule"]
    ):

        print()

        print(
            f"FROM:    "
            f"{candidate['sender']}"
        )

        print(
            f"SUBJECT: "
            f"{candidate['subject']}"
        )

        print(
            f"RULE:    "
            f"{result['category']} / "
            f"{result['recommended_action']}"
        )

    # =========================================================
    # PATTERN POLICY EXAMPLES
    # =========================================================

    print()
    print("-" * 78)
    print("PATTERN POLICY EXAMPLES")
    print("-" * 78)

    if not examples["pattern_policy"]:
        print("None found.")

    for candidate, result in (
        examples["pattern_policy"]
    ):

        print()

        print(
            f"FROM:    "
            f"{candidate['sender']}"
        )

        print(
            f"SUBJECT: "
            f"{candidate['subject']}"
        )

        print(
            f"GMAIL:   "
            f"{candidate['gmail_category']}"
        )

        print(
            f"RESULT:  "
            f"{result['category']} / "
            f"{result['recommended_action']}"
        )

        print(
            f"CONFIDENCE: "
            f"{result['confidence']:.0%}"
        )

    # =========================================================
    # HISTORICAL RULE EXAMPLES
    # =========================================================

    print()
    print("-" * 78)
    print("HISTORICAL RULE EXAMPLES")
    print("-" * 78)

    if not examples["historical_rule"]:
        print("None found.")

    for candidate, result in (
        examples["historical_rule"]
    ):

        print()

        print(
            f"FROM:    "
            f"{candidate['sender']}"
        )

        print(
            f"SUBJECT: "
            f"{candidate['subject']}"
        )

        print(
            f"GMAIL:   "
            f"{candidate['gmail_category']}"
        )

        print(
            f"RESULT:  "
            f"{result['category']} / "
            f"{result['recommended_action']}"
        )

        print(
            f"RULE CONFIDENCE: "
            f"{result['confidence']:.0%}"
        )

    # =========================================================
    # OPENAI REQUIRED EXAMPLES
    # =========================================================

    print()
    print("-" * 78)
    print("WOULD REQUIRE CLASSIFICATION")
    print("-" * 78)

    if not examples[
        "needs_classification"
    ]:
        print("None found.")

    for candidate in (
        examples[
            "needs_classification"
        ]
    ):

        print()

        print(
            f"FROM:    "
            f"{candidate['sender']}"
        )

        print(
            f"SUBJECT: "
            f"{candidate['subject']}"
        )

        print(
            f"GMAIL:   "
            f"{candidate['gmail_category']}"
        )

    # =========================================================
    # COMPLETE
    # =========================================================

    print()
    print("=" * 78)
    print("PHASE 3 ANALYSIS COMPLETE")
    print("=" * 78)

    print()

    print(
        "NO GMAIL MESSAGES WERE MODIFIED."
    )

    print(
        "NO OPENAI API CALLS WERE MADE."
    )

# =====================================================================
# PHASE 3 CONTROLLED CLASSIFICATION PROCESSOR
# =====================================================================


def _classify_candidate(candidate, service=None):
    """Classify one candidate using the cheapest safe path first."""
    from classifier import classify_email
    from gmail_service import get_message

    email = build_minimal_email(candidate)

    result = check_local_rule(email)
    if result:
        return email, result, False

    result = get_pattern_classification(email)
    if result:
        return email, result, False

    result = get_learned_pattern_classification(email)
    if result:
        return email, result, False

    result = check_historical_rule(
        email,
        gmail_category=candidate["gmail_category"],
    )
    if result:
        return email, result, False

    if service is None:
        raise RuntimeError(
            "A Gmail service is required for OpenAI classification "
            "because the full message body must be retrieved."
        )

    email = get_message(service, candidate["email_id"])
    result = classify_email(email)
    result["classification_source"] = "openai_historical"
    return email, result, True


def _print_classification(index, total, email, result, final_action):
    print()
    print("-" * 78)
    print(f"[{index}/{total}]")
    print(f"FROM:       {email.get('sender_raw') or email.get('sender', '')}")
    print(f"SUBJECT:    {email.get('subject', '')}")
    print(f"SOURCE:     {result.get('classification_source', 'unknown')}")
    print(f"CATEGORY:   {result['category']}")
    print(f"SUBCATEGORY:{result['subcategory']}")
    print(f"STATE:      {result.get('email_state', 'unknown')}")
    print(f"IMPORTANCE: {result['importance']}")
    print(f"CONFIDENCE: {result['confidence']:.0%}")
    print(f"ACTION REQ: {result['action_required']}")
    print(f"FINAL:      {final_action}")
    print(f"REASON:     {result['reason']}")


def run_phase3_classification_preview(limit=None):
    """Classify a small Phase 3 batch without modifying Gmail or SQLite."""
    import time
    from action_policy import determine_action
    from config import PHASE3_BATCH_SIZE, PHASE3_OPENAI_DELAY_SECONDS
    from gmail_service import get_gmail_service

    limit = limit or PHASE3_BATCH_SIZE
    candidates = get_phase3_candidates(limit=limit)

    print()
    print("=" * 78)
    print("GMAIL AI ORGANIZER — PHASE 3 CLASSIFICATION PREVIEW")
    print("=" * 78)
    print()
    print("PREVIEW MODE")
    print("Gmail will NOT be modified.")
    print("SQLite will NOT be modified.")
    print("OpenAI MAY be called for messages not covered by rules.")
    print()

    if not candidates:
        print("No eligible Phase 3 candidates found.")
        return

    service = get_gmail_service()
    stats = Counter()

    for index, candidate in enumerate(candidates, start=1):
        try:
            email, result, used_openai = _classify_candidate(candidate, service)
            final_action = determine_action(result)
            _print_classification(index, len(candidates), email, result, final_action)

            stats["classified"] += 1
            stats["openai" if used_openai else "rules"] += 1
            stats[final_action] += 1

            if used_openai:
                time.sleep(PHASE3_OPENAI_DELAY_SECONDS)
        except Exception as exc:
            stats["errors"] += 1
            print(f"\nERROR {candidate['email_id']}: {exc}")

    print()
    print("=" * 78)
    print("PHASE 3 PREVIEW SUMMARY")
    print("=" * 78)
    print(f"Candidates:              {len(candidates):,}")
    print(f"Classified:              {stats['classified']:,}")
    print(f"Rule/pattern matches:    {stats['rules']:,}")
    print(f"OpenAI classifications: {stats['openai']:,}")
    print(f"Keep:                    {stats['keep']:,}")
    print(f"Archive:                 {stats['archive']:,}")
    print(f"Trash quarantine:        {stats['trash_candidate']:,}")
    print(f"Needs review:            {stats['review']:,}")
    print(f"Errors:                  {stats['errors']:,}")
    print()
    print("NO GMAIL MESSAGES WERE MODIFIED.")
    print("NO SQLITE RECORDS WERE WRITTEN.")
    print("=" * 78)


def run_phase3_classification_live(
    limit=None,
    service=None,
    verbose=True,
):
    """Classify and organize one resumable Phase 3 historical batch."""
    import time
    from action_policy import determine_action
    from config import (
        HISTORICAL_QUARANTINE_DAYS,
        PHASE3_BATCH_SIZE,
        PHASE3_OPENAI_DELAY_SECONDS,
    )
    from database import (
        initialize_database,
        initialize_historical_actions_table,
        migrate_database,
        save_result,
        initialize_phase3_learning_table,
        save_phase3_learning_observation,
    )
    from gmail_service import (
        apply_label,
        archive_message,
        get_gmail_service,
        get_or_create_label,
        quarantine_message,
    )

    limit = limit or PHASE3_BATCH_SIZE
    initialize_database()
    migrate_database()
    initialize_historical_actions_table()
    initialize_phase3_learning_table()

    candidates = get_phase3_candidates(limit=limit)
    stats = Counter()
    stats["candidates"] = len(candidates)

    if verbose:
        print()
        print("=" * 78)
        print("GMAIL AI ORGANIZER — PHASE 3 CLASSIFICATION LIVE")
        print("=" * 78)
        print(f"Batch limit: {limit}")
        print(f"Trash quarantine: {HISTORICAL_QUARANTINE_DAYS} days")
        print("No message will be permanently deleted by this run.")
        print()

    if not candidates:
        if verbose:
            print("No eligible Phase 3 candidates found.")
        return dict(stats)

    if service is None:
        service = get_gmail_service()

    trash_label_id = get_or_create_label(service, "AI/Trash Candidates")

    for index, candidate in enumerate(candidates, start=1):
        try:
            email, result, used_openai = _classify_candidate(candidate, service)
            final_action = determine_action(result)

            if verbose:
                _print_classification(index, len(candidates), email, result, final_action)

            apply_label(service, email["id"], f"AI/{result['category']}")

            if result["importance"] == "high":
                apply_label(service, email["id"], "AI/Important")

            if result["action_required"]:
                apply_label(service, email["id"], "AI/Needs Action")

            if final_action == "review":
                apply_label(service, email["id"], "AI/Needs Review")
                stats["review"] += 1

            elif final_action == "trash_candidate":
                quarantine_message(service, email["id"], trash_label_id)
                stats["trash_candidate"] += 1

            elif final_action == "archive":
                archive_message(service, email["id"])
                stats["archive"] += 1

            else:
                stats["keep"] += 1

            # Save only after the Gmail action succeeds. This makes interruption
            # safe: completed rows are skipped on the next run; failed rows retry.
            save_result(email, result, final_action)

            if used_openai:
                from historical_pattern_rules import get_subject_signature
                save_phase3_learning_observation(
                    email,
                    result,
                    final_action,
                    get_subject_signature(email.get("subject", "")),
                )

            stats["processed"] += 1
            stats["openai" if used_openai else "rules"] += 1

            if verbose and stats["processed"] % 25 == 0:
                print(
                    f"\nPROGRESS: {stats['processed']:,}/{len(candidates):,} "
                    f"processed | {stats['openai']:,} OpenAI | "
                    f"{stats['rules']:,} local/rule | {stats['errors']:,} errors"
                )

            if used_openai and PHASE3_OPENAI_DELAY_SECONDS > 0:
                time.sleep(PHASE3_OPENAI_DELAY_SECONDS)

        except Exception as exc:
            stats["errors"] += 1
            if verbose:
                print(f"\nERROR {candidate['email_id']}: {exc}")

    if verbose:
        print()
        print("=" * 78)
        print("PHASE 3 LIVE SUMMARY")
        print("=" * 78)
        print(f"Candidates:              {len(candidates):,}")
        print(f"Processed:               {stats['processed']:,}")
        print(f"Rule/pattern matches:    {stats['rules']:,}")
        print(f"OpenAI classifications: {stats['openai']:,}")
        print(f"Keep:                    {stats['keep']:,}")
        print(f"Archive:                 {stats['archive']:,}")
        print(f"Trash quarantined:       {stats['trash_candidate']:,}")
        print(f"Needs review:            {stats['review']:,}")
        print(f"Errors:                  {stats['errors']:,}")
        print("NO MESSAGES WERE PERMANENTLY DELETED.")
        print("=" * 78)

    return dict(stats)
