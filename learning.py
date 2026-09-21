import sqlite3
from collections import Counter

from database import DB_FILE


MIN_EMAILS_FOR_RULE = 5
MIN_CONSISTENCY = 0.90


def analyze_senders():
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            """
            SELECT
                sender,
                category,
                recommended_action
            FROM processed_emails
            WHERE sender IS NOT NULL
            AND classification_source = 'openai'
            """
        ).fetchall()

    senders = {}

    for sender, category, action in rows:
        sender = sender.lower()

        if sender not in senders:
            senders[sender] = []

        senders[sender].append(
            (category, action)
        )

    recommendations = []

    for sender, classifications in senders.items():
        total = len(classifications)

        if total < MIN_EMAILS_FOR_RULE:
            continue

        counts = Counter(classifications)

        most_common, count = counts.most_common(1)[0]

        consistency = count / total

        if consistency >= MIN_CONSISTENCY:
            category, action = most_common

            recommendations.append(
                {
                    "sender": sender,
                    "emails": total,
                    "category": category,
                    "action": action,
                    "consistency": consistency,
                }
            )

    return recommendations