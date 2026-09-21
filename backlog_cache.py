import sqlite3

from config import BACKLOG_CACHE_FILE, PROTECTED_CATEGORIES


def initialize_backlog_cache():
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS backlog_messages (
                email_id TEXT PRIMARY KEY,
                sender TEXT,
                domain TEXT,
                subject TEXT,
                gmail_category TEXT,
                in_inbox INTEGER,
                internal_date TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )


def get_cache_meta(key, default=None):
    initialize_backlog_cache()
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        row = conn.execute(
            "SELECT value FROM cache_meta WHERE key = ?",
            (key,),
        ).fetchone()
    return row[0] if row else default


def set_cache_meta(key, value):
    initialize_backlog_cache()
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache_meta(key, value) VALUES (?, ?)",
            (key, str(value)),
        )


def save_backlog_metadata(
    email_id,
    sender,
    domain,
    subject,
    gmail_category,
    in_inbox,
    internal_date,
):
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO backlog_messages (
                email_id,
                sender,
                domain,
                subject,
                gmail_category,
                in_inbox,
                internal_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email_id,
                sender,
                domain,
                subject,
                gmail_category,
                int(in_inbox),
                internal_date,
            ),
        )


def get_cached_message_ids():
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        rows = conn.execute(
            """
            SELECT email_id
            FROM backlog_messages
            """
        ).fetchall()

    return {row[0] for row in rows}


def get_sender_analysis():
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                sender,
                domain,
                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN gmail_category = 'Promotions'
                        THEN 1
                        ELSE 0
                    END
                ) AS promotions_count,

                SUM(
                    CASE
                        WHEN gmail_category = 'Updates'
                        THEN 1
                        ELSE 0
                    END
                ) AS updates_count,

                SUM(
                    CASE
                        WHEN gmail_category = 'Primary'
                        THEN 1
                        ELSE 0
                    END
                ) AS primary_count,

                SUM(
                    CASE
                        WHEN gmail_category = 'Social'
                        THEN 1
                        ELSE 0
                    END
                ) AS social_count,

                SUM(
                    CASE
                        WHEN gmail_category = 'Forums'
                        THEN 1
                        ELSE 0
                    END
                ) AS forums_count,

                SUM(
                    CASE
                        WHEN gmail_category = 'Uncategorized'
                        THEN 1
                        ELSE 0
                    END
                ) AS uncategorized_count

            FROM backlog_messages

            GROUP BY sender, domain

            ORDER BY total DESC
            """
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]

def get_bulk_promotion_candidates():
    """
    Return cached messages belonging to senders that may
    qualify for historical bulk promotional processing.

    This function only retrieves data. Safety decisions
    happen elsewhere.
    """

    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                b.email_id,
                b.sender,
                b.domain,
                b.subject,
                b.gmail_category,
                b.in_inbox,
                b.internal_date

            FROM backlog_messages AS b

            WHERE b.gmail_category = 'Promotions'

            ORDER BY
                b.sender,
                b.internal_date ASC
            """
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]

def get_sender_sample_subjects(
    sender,
    limit=12,
):
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        rows = conn.execute(
            """
            SELECT subject
            FROM backlog_messages
            WHERE LOWER(sender) = LOWER(?)
              AND subject IS NOT NULL
              AND TRIM(subject) <> ''
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (
                sender,
                limit,
            ),
        ).fetchall()

    return [
        row[0]
        for row in rows
    ]

def save_sender_policy(
    sender,
    domain,
    result,
):
    from datetime import datetime

    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sender_policies (
                sender,
                domain,
                category,
                subcategory,
                sender_type,
                bulk_safe,
                bulk_action,
                confidence,
                reason,
                analyzed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sender,
                domain,
                result["category"],
                result["subcategory"],
                result["sender_type"],
                int(result["bulk_safe"]),
                result["bulk_action"],
                result["confidence"],
                result["reason"],
                datetime.now().isoformat(),
            ),
        )

def load_sender_policies():
    """
    Return all cached AI sender-policy decisions.
    """

    initialize_sender_policy_table()

    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                sender,
                domain,
                category,
                subcategory,
                sender_type,
                bulk_safe,
                bulk_action,
                confidence,
                reason,
                analyzed_at
            FROM sender_policies
            ORDER BY sender ASC
            """
        ).fetchall()

    policies = []

    for row in rows:
        policy = dict(row)

        # SQLite stores booleans as 0/1.
        policy["bulk_safe"] = bool(
            policy["bulk_safe"]
        )

        policies.append(policy)

    return policies
def sender_policy_exists(sender):
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        row = conn.execute(
            """
            SELECT sender
            FROM sender_policies
            WHERE LOWER(sender) = LOWER(?)
            """,
            (sender,),
        ).fetchone()

    return row is not None

def initialize_sender_policy_table():
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sender_policies (
                sender TEXT PRIMARY KEY,
                domain TEXT,
                category TEXT,
                subcategory TEXT,
                sender_type TEXT,
                bulk_safe INTEGER,
                bulk_action TEXT,
                confidence REAL,
                reason TEXT,
                analyzed_at TEXT
            )
            """
        )

def clear_sender_policies():
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.execute(
            """
            DELETE FROM sender_policies
            """
        )



def sanitize_sender_policies():
    """Downgrade unsafe persisted bulk-trash policies for protected categories."""
    initialize_sender_policy_table()
    protected = tuple(sorted(PROTECTED_CATEGORIES))
    placeholders = ",".join("?" for _ in protected)
    if not protected:
        return 0

    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        cursor = conn.execute(
            f"""
            UPDATE sender_policies
            SET bulk_safe = 0,
                bulk_action = 'individual_classification',
                reason = 'Safety migration: protected categories are not eligible for bulk trash. ' || COALESCE(reason, '')
            WHERE bulk_action = 'trash_candidate'
              AND category IN ({placeholders})
            """,
            protected,
        )
        return cursor.rowcount


def get_historical_policy_candidates(
    limit=250,
    offset=0,
):
    """
    Return historical messages belonging to senders
    with an approved bulk-safe sender policy.

    READ ONLY.

    This joins cached Gmail metadata against the cached
    AI sender-policy decisions.
    """

    initialize_backlog_cache()
    initialize_sender_policy_table()

    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                b.email_id,
                b.sender,
                b.domain,
                b.subject,
                b.gmail_category,
                b.in_inbox,
                b.internal_date,

                p.category AS policy_category,
                p.subcategory AS policy_subcategory,
                p.sender_type,
                p.bulk_safe,
                p.bulk_action,
                p.confidence,
                p.reason

            FROM backlog_messages AS b

            INNER JOIN sender_policies AS p
                ON LOWER(b.sender) = LOWER(p.sender)

            WHERE p.bulk_safe = 1

              AND p.bulk_action IN (
                  'trash_candidate',
                  'archive',
                  'keep'
              )

            ORDER BY
                CASE p.bulk_action
                    WHEN 'trash_candidate' THEN 1
                    WHEN 'archive' THEN 2
                    WHEN 'keep' THEN 3
                    ELSE 4
                END,
                p.confidence DESC,
                b.internal_date ASC

            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]

def get_individual_classification_candidates(
    limit=5000,
    offset=0,
):
    """
    Return historical messages that are NOT covered by a
    bulk-safe sender policy.

    These messages require individual classification.

    READ ONLY.
    """

    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                b.email_id,
                b.sender,
                b.domain,
                b.subject,
                b.gmail_category,
                b.in_inbox,
                b.internal_date,

                p.category AS policy_category,
                p.bulk_safe,
                p.bulk_action,
                p.confidence AS policy_confidence

            FROM backlog_messages AS b

            LEFT JOIN sender_policies AS p
                ON LOWER(b.sender) = LOWER(p.sender)

            WHERE
                p.sender IS NULL
                OR p.bulk_safe = 0
                OR p.bulk_action = 'individual_classification'

            ORDER BY b.internal_date DESC

            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]

def get_cached_messages(
    limit=None,
):
    """
    Return cached Gmail metadata for historical
    subject-pattern analysis.

    READ ONLY.
    """

    with sqlite3.connect(
        BACKLOG_CACHE_FILE
    ) as conn:

        conn.row_factory = sqlite3.Row

        sql = """
            SELECT
                email_id,
                sender,
                domain,
                subject,
                gmail_category,
                in_inbox,
                internal_date
            FROM backlog_messages
            WHERE sender IS NOT NULL
              AND TRIM(sender) <> ''
              AND subject IS NOT NULL
              AND TRIM(subject) <> ''
            ORDER BY internal_date DESC
        """

        parameters = ()

        if limit is not None:
            sql += " LIMIT ?"
            parameters = (
                limit,
            )

        rows = conn.execute(
            sql,
            parameters,
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]

def get_backlog_counts():
    """Return high-level cached backlog counts for progress reporting."""
    initialize_backlog_cache()
    initialize_sender_policy_table()
    with sqlite3.connect(BACKLOG_CACHE_FILE) as conn:
        total = conn.execute("SELECT COUNT(*) FROM backlog_messages").fetchone()[0]
        senders = conn.execute(
            "SELECT COUNT(DISTINCT LOWER(sender)) FROM backlog_messages "
            "WHERE sender IS NOT NULL AND TRIM(sender) <> ''"
        ).fetchone()[0]
        policies = conn.execute("SELECT COUNT(*) FROM sender_policies").fetchone()[0]
        bulk_safe = conn.execute(
            "SELECT COUNT(*) FROM sender_policies WHERE bulk_safe = 1"
        ).fetchone()[0]
    return {
        "total_messages": total,
        "unique_senders": senders,
        "sender_policies": policies,
        "bulk_safe_senders": bulk_safe,
    }
