import sqlite3
from datetime import datetime


DB_FILE = "emails.db"


def initialize_database():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_emails (
                email_id TEXT PRIMARY KEY,
                email_state TEXT,
                sender TEXT,
                subject TEXT,
                category TEXT,
                subcategory TEXT,
                importance TEXT,
                confidence REAL,
                action_required INTEGER,
                recommended_action TEXT,
                final_action TEXT,
                reason TEXT,
                classification_source TEXT,
                processed_at TEXT,
                cleanup_status TEXT,
                trashed_at TEXT
            )
            """
        )
def migrate_database():
    with sqlite3.connect(DB_FILE) as conn:
        columns = conn.execute(
            "PRAGMA table_info(processed_emails)"
        ).fetchall()

        column_names = [
            column[1]
            for column in columns
        ]

        if "classification_source" not in column_names:
            conn.execute(
                """
                ALTER TABLE processed_emails
                ADD COLUMN classification_source TEXT
                """
            )

        if "email_state" not in column_names:
            conn.execute(
                """
                ALTER TABLE processed_emails
                ADD COLUMN email_state TEXT
                """
            )

        if "cleanup_status" not in column_names:
            conn.execute(
                """
                ALTER TABLE processed_emails
                ADD COLUMN cleanup_status TEXT
                """
            )

        if "trashed_at" not in column_names:
            conn.execute(
                """
                ALTER TABLE processed_emails
                ADD COLUMN trashed_at TEXT
                """
            )

        # Existing trash candidates predate cleanup_status; treat them as
        # quarantined until cleanup proves otherwise.
        conn.execute(
            """
            UPDATE processed_emails
            SET cleanup_status = CASE
                WHEN final_action = 'trash_candidate' THEN 'quarantined'
                ELSE 'not_applicable'
            END
            WHERE cleanup_status IS NULL
            """
        )

def is_processed(email_id):
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute(
            """
            SELECT email_id
            FROM processed_emails
            WHERE email_id = ?
            """,
            (email_id,),
        ).fetchone()

    return row is not None


def save_result(email, result, final_action):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO processed_emails (
                email_id,
                email_state,
                sender,
                subject,
                category,
                subcategory,
                importance,
                confidence,
                action_required,
                recommended_action,
                final_action,
                reason,
                classification_source,
                processed_at,
                cleanup_status,
                trashed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email["id"],
                result.get("email_state", "unknown"),
                email["sender"],
                email["subject"],
                result["category"],
                result["subcategory"],
                result["importance"],
                result["confidence"],
                int(result["action_required"]),
                result["recommended_action"],
                final_action,
                result["reason"],
                result.get(
                    "classification_source",
                    "unknown"
                ),
                datetime.now().isoformat(),
                (
                    "quarantined"
                    if final_action == "trash_candidate"
                    else "not_applicable"
                ),
                None,
            ),
        )
def initialize_runs_table():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS organizer_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                completed_at TEXT,
                scanned INTEGER,
                already_processed INTEGER,
                processed INTEGER,
                openai_classifications INTEGER,
                local_rule_matches INTEGER,
                kept INTEGER,
                archived INTEGER,
                trash_candidates INTEGER,
                needs_review INTEGER,
                errors INTEGER,
                runtime_seconds REAL
            )
            """
        )


def save_run_stats(stats, runtime):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO organizer_runs (
                completed_at,
                scanned,
                already_processed,
                processed,
                openai_classifications,
                local_rule_matches,
                kept,
                archived,
                trash_candidates,
                needs_review,
                errors,
                runtime_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                stats["scanned"],
                stats["already_processed"],
                stats["processed"],
                stats["openai"],
                stats["local_rules"],
                stats["keep"],
                stats["archive"],
                stats["trash_candidate"],
                stats["review"],
                stats["errors"],
                runtime,
            ),
        )

def get_trash_candidates():
    """
    Return emails that were classified as trash candidates.
    """

    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                email_id,
                sender,
                subject,
                category,
                subcategory,
                importance,
                action_required,
                confidence,
                email_state,
                final_action,
                processed_at
            FROM processed_emails
            WHERE final_action = 'trash_candidate'
              AND COALESCE(cleanup_status, 'quarantined') = 'quarantined'
            ORDER BY processed_at ASC
            """
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]

def get_processed_email_ids():
    """
    Return all Gmail message IDs already processed
    by the organizer.
    """

    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            """
            SELECT email_id
            FROM processed_emails
            """
        ).fetchall()

    return {
        row[0]
        for row in rows
    }

def initialize_historical_actions_table():
    """
    Create the historical cleanup ledger.

    This table tracks messages handled by the
    historical bulk processor separately from the
    normal processed_emails table.
    """

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_actions (
                email_id TEXT PRIMARY KEY,
                sender TEXT,
                subject TEXT,
                policy_category TEXT,
                policy_subcategory TEXT,
                bulk_action TEXT,
                originally_in_inbox INTEGER,
                status TEXT,
                policy_confidence REAL,
                quarantined_at TEXT,
                quarantine_until TEXT,
                completed_at TEXT,
                error_message TEXT
            )
            """
        )


def historical_action_exists(email_id):
    """
    Return True if the historical processor has
    already recorded this Gmail message.
    """

    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute(
            """
            SELECT email_id
            FROM historical_actions
            WHERE email_id = ?
            """,
            (email_id,),
        ).fetchone()

    return row is not None


def get_historical_action_ids():
    """
    Return all Gmail message IDs already recorded
    by the historical processor.
    """

    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            """
            SELECT email_id
            FROM historical_actions
            """
        ).fetchall()

    return {
        row[0]
        for row in rows
    }


def save_historical_action(
    candidate,
    status,
    quarantined_at=None,
    quarantine_until=None,
    completed_at=None,
    error_message=None,
):
    """
    Record or update a historical processing action.
    """

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO historical_actions (
                email_id,
                sender,
                subject,
                policy_category,
                policy_subcategory,
                bulk_action,
                originally_in_inbox,
                status,
                policy_confidence,
                quarantined_at,
                quarantine_until,
                completed_at,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate["email_id"],
                candidate["sender"],
                candidate["subject"],
                candidate["policy_category"],
                candidate["policy_subcategory"],
                candidate["bulk_action"],
                int(
                    bool(
                        candidate["in_inbox"]
                    )
                ),
                status,
                candidate["confidence"],
                quarantined_at,
                quarantine_until,
                completed_at,
                error_message,
            ),
        )


def get_expired_historical_quarantines(
    current_time,
):
    """
    Return historical trash candidates whose
    quarantine period has expired.

    This does NOT modify Gmail.
    """

    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT *
            FROM historical_actions

            WHERE bulk_action = 'trash_candidate'

              AND status = 'quarantined'

              AND quarantine_until IS NOT NULL

              AND quarantine_until <= ?

            ORDER BY quarantine_until ASC
            """,
            (current_time,),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def update_historical_action_status(
    email_id,
    status,
    completed_at=None,
    error_message=None,
):
    """
    Update the status of an existing historical
    action without replacing the entire record.
    """

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            UPDATE historical_actions

            SET
                status = ?,
                completed_at = ?,
                error_message = ?

            WHERE email_id = ?
            """,
            (
                status,
                completed_at,
                error_message,
                email_id,
            ),
        )

def update_processed_cleanup_status(
    email_id,
    status,
    trashed_at=None,
):
    """Record the terminal cleanup state for a normal/Phase 3 message."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            UPDATE processed_emails
            SET cleanup_status = ?, trashed_at = ?
            WHERE email_id = ?
            """,
            (status, trashed_at, email_id),
        )


def initialize_phase3_learning_table():
    """Store OpenAI historical observations used to learn safe local patterns."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS phase3_learning (
                email_id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                subject_signature TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                email_state TEXT,
                final_action TEXT NOT NULL,
                confidence REAL NOT NULL,
                observed_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_phase3_learning_pattern
            ON phase3_learning(sender, subject_signature)
            """
        )


def save_phase3_learning_observation(email, result, final_action, subject_signature):
    # Learn only non-actionable archive/trash behavior. Learning a keep/review
    # pattern could suppress future action-required labels, so those decisions
    # deliberately remain individually classified.
    if (
        not subject_signature
        or result.get("action_required")
        or final_action not in {"archive", "trash_candidate"}
    ):
        return
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO phase3_learning (
                email_id, sender, subject_signature, category, subcategory,
                email_state, final_action, confidence, observed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email["id"],
                (email.get("sender") or "").lower(),
                subject_signature,
                result["category"],
                result.get("subcategory", ""),
                result.get("email_state", "unknown"),
                final_action,
                result["confidence"],
                datetime.now().isoformat(),
            ),
        )


def get_phase3_learned_pattern(
    sender,
    subject_signature,
    min_examples=3,
    min_confidence=0.90,
):
    """Return one unanimous learned pattern without scanning the whole table."""
    initialize_phase3_learning_table()
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT
                sender,
                subject_signature,
                COUNT(*) AS examples,
                MIN(confidence) AS min_confidence,
                COUNT(DISTINCT category) AS category_count,
                COUNT(DISTINCT final_action) AS action_count,
                MAX(category) AS category,
                MAX(subcategory) AS subcategory,
                MAX(email_state) AS email_state,
                MAX(final_action) AS final_action
            FROM phase3_learning
            WHERE sender = ? AND subject_signature = ?
            GROUP BY sender, subject_signature
            HAVING COUNT(*) >= ?
               AND MIN(confidence) >= ?
               AND COUNT(DISTINCT category) = 1
               AND COUNT(DISTINCT final_action) = 1
            """,
            (sender, subject_signature, min_examples, min_confidence),
        ).fetchone()
    return dict(row) if row else None


def get_phase3_learned_patterns(min_examples=3, min_confidence=0.90):
    """Return only unanimous, high-confidence learned patterns."""
    initialize_phase3_learning_table()
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                sender,
                subject_signature,
                COUNT(*) AS examples,
                MIN(confidence) AS min_confidence,
                COUNT(DISTINCT category) AS category_count,
                COUNT(DISTINCT final_action) AS action_count,
                MAX(category) AS category,
                MAX(subcategory) AS subcategory,
                MAX(email_state) AS email_state,
                MAX(final_action) AS final_action
            FROM phase3_learning
            GROUP BY sender, subject_signature
            HAVING COUNT(*) >= ?
               AND MIN(confidence) >= ?
               AND COUNT(DISTINCT category) = 1
               AND COUNT(DISTINCT final_action) = 1
            """,
            (min_examples, min_confidence),
        ).fetchall()
    return [dict(row) for row in rows]


def get_phase3_stats():
    """Return aggregate Phase 3/organizer processing statistics."""
    initialize_database()
    migrate_database()
    initialize_phase3_learning_table()
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        processed = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN classification_source = 'openai_historical' THEN 1 ELSE 0 END) AS openai_historical,
                SUM(CASE WHEN COALESCE(classification_source, 'unknown') <> 'openai_historical' THEN 1 ELSE 0 END) AS local_or_rule,
                SUM(CASE WHEN final_action = 'keep' THEN 1 ELSE 0 END) AS kept,
                SUM(CASE WHEN final_action = 'archive' THEN 1 ELSE 0 END) AS archived,
                SUM(CASE WHEN final_action = 'trash_candidate' THEN 1 ELSE 0 END) AS trash_candidates,
                SUM(CASE WHEN final_action = 'review' THEN 1 ELSE 0 END) AS review
            FROM processed_emails
            """
        ).fetchone()
        learned = conn.execute(
            "SELECT COUNT(*) AS observations FROM phase3_learning"
        ).fetchone()
    return {
        **dict(processed),
        "learning_observations": learned["observations"],
    }
