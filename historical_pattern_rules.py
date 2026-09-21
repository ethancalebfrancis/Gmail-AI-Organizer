import re
from collections import Counter, defaultdict


# Words that usually carry very little information when
# determining what type of email something is.
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
    "you",
    "your",
}


def normalize_subject(subject):
    """
    Normalize an email subject so similar historical
    subjects can be compared.

    Examples:

        "Shipped: 1 Kitchen item"
        "Shipped: 2 Electronics items"

    become structurally similar.
    """

    if not subject:
        return ""

    subject = subject.lower().strip()

    # Remove common reply/forward prefixes.
    subject = re.sub(
        r"^(re|fw|fwd)\s*:\s*",
        "",
        subject,
    )

    # Replace numbers with a common token.
    subject = re.sub(
        r"\b\d+(?:[.,]\d+)?\b",
        "<num>",
        subject,
    )

    # Replace currency amounts.
    subject = re.sub(
        r"\$\s*<num>",
        "<money>",
        subject,
    )

    # Remove most punctuation while preserving words.
    subject = re.sub(
        r"[^\w\s<>]",
        " ",
        subject,
    )

    # Collapse whitespace.
    subject = re.sub(
        r"\s+",
        " ",
        subject,
    ).strip()

    return subject


def get_subject_tokens(subject):
    """
    Return meaningful normalized words from a subject.
    """

    normalized = normalize_subject(subject)

    tokens = []

    for token in normalized.split():

        if token in STOP_WORDS:
            continue

        if len(token) < 3:
            continue

        tokens.append(token)

    return tokens


def get_subject_signature(subject):
    """
    Produce a conservative signature for a subject.

    This is NOT yet used to modify Gmail.
    """

    tokens = get_subject_tokens(subject)

    if not tokens:
        return ""

    # Keep the first few meaningful words.
    return " ".join(
        tokens[:5]
    )


def analyze_sender_subjects(messages):
    """
    Analyze recurring subject signatures by sender.

    messages should contain:

        sender
        subject
        gmail_category

    Returns potential patterns only.
    """

    groups = defaultdict(list)

    for message in messages:

        sender = (
            message.get("sender")
            or ""
        ).lower()

        subject = (
            message.get("subject")
            or ""
        )

        if not sender:
            continue

        signature = get_subject_signature(
            subject
        )

        if not signature:
            continue

        groups[
            (sender, signature)
        ].append(message)

    results = []

    for (
        sender,
        signature,
    ), group in groups.items():

        if len(group) < 3:
            continue

        categories = Counter(
            message.get(
                "gmail_category",
                "Unknown",
            )
            for message in group
        )

        dominant_category, count = (
            categories.most_common(1)[0]
        )

        consistency = (
            count / len(group)
        )

        results.append(
            {
                "sender": sender,
                "signature": signature,
                "messages": len(group),
                "gmail_category":
                    dominant_category,
                "consistency":
                    consistency,
                "examples": [
                    message.get(
                        "subject",
                        "",
                    )
                    for message in group[:5]
                ],
            }
        )

    results.sort(
        key=lambda item: (
            item["messages"],
            item["consistency"],
        ),
        reverse=True,
    )

    return results