"""Central configuration for Gmail AI Organizer.

Most values can be overridden in ``.env`` without editing source code.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _env_float(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


CATEGORIES = [
    "School",
    "Work & Career",
    "Financial",
    "Accounts & Security",
    "Shopping & Orders",
    "Receipts",
    "Travel",
    "Events",
    "Personal",
    "Newsletters",
    "Marketing",
    "Other",
]

# Categories for which automatic trashing is deliberately conservative.
# Promotional messages in a protected category can still be archived.
PROTECTED_CATEGORIES = {
    "School",
    "Work & Career",
    "Financial",
    "Accounts & Security",
    "Shopping & Orders",
    "Receipts",
    "Travel",
    "Events",
    "Personal",
}

CONFIDENCE_THRESHOLD = _env_float("CONFIDENCE_THRESHOLD", 0.80)

MAX_EMAILS = _env_int("MAX_EMAILS", 250)
MAX_NEW_EMAILS_PER_RUN = _env_int("MAX_NEW_EMAILS_PER_RUN", 50)
MAX_BODY_CHARACTERS = _env_int("MAX_BODY_CHARACTERS", 8000)

DRY_RUN = _env_bool("DRY_RUN", False)

# Trash candidate quarantine settings. Messages are moved to Gmail Trash only
# after this retention window and another safety check.
TRASH_QUARANTINE_DAYS = _env_int("TRASH_QUARANTINE_DAYS", 14)
CLEANUP_LIVE = _env_bool("CLEANUP_LIVE", True)

# ---------------------------------------------------------
# BACKLOG SCANNER
# ---------------------------------------------------------
BACKLOG_SCAN_LIMIT = None
BACKLOG_PAGE_SIZE = _env_int("BACKLOG_PAGE_SIZE", 500)
BACKLOG_TOP_SENDERS = 50
BACKLOG_TOP_DOMAINS = 30

# ---------------------------------------------------------
# BACKLOG ANALYSIS
# ---------------------------------------------------------
BACKLOG_CACHE_FILE = os.getenv("BACKLOG_CACHE_FILE", "backlog_cache.db")
BACKLOG_ANALYSIS_MIN_EMAILS = _env_int("BACKLOG_ANALYSIS_MIN_EMAILS", 20)
BACKLOG_CATEGORY_CONSISTENCY = _env_float("BACKLOG_CATEGORY_CONSISTENCY", 0.95)
BACKLOG_ANALYSIS_TOP = 100

# ---------------------------------------------------------
# BACKLOG BULK PROCESSING
# ---------------------------------------------------------
BACKLOG_BULK_LIVE = _env_bool("BACKLOG_BULK_LIVE", False)
BACKLOG_BULK_MIN_EMAILS = _env_int("BACKLOG_BULK_MIN_EMAILS", 20)
BACKLOG_BULK_PROMOTION_CONSISTENCY = _env_float(
    "BACKLOG_BULK_PROMOTION_CONSISTENCY", 0.95
)
BACKLOG_BULK_MAX_PER_RUN = _env_int("BACKLOG_BULK_MAX_PER_RUN", 1000)

# ---------------------------------------------------------
# AI SENDER POLICY ANALYSIS
# ---------------------------------------------------------
SENDER_POLICY_SAMPLE_SIZE = _env_int("SENDER_POLICY_SAMPLE_SIZE", 12)
SENDER_POLICY_MAX_PER_RUN = _env_int("SENDER_POLICY_MAX_PER_RUN", 100)
SENDER_POLICY_CONFIDENCE_THRESHOLD = _env_float(
    "SENDER_POLICY_CONFIDENCE_THRESHOLD", 0.90
)
SENDER_POLICY_OPENAI_DELAY_SECONDS = _env_float(
    "SENDER_POLICY_OPENAI_DELAY_SECONDS", 0.75
)

# ---------------------------------------------------------
# HISTORICAL PROCESSING
# ---------------------------------------------------------
HISTORICAL_BATCH_SIZE = _env_int("HISTORICAL_BATCH_SIZE", 1000)
HISTORICAL_PER_SENDER_LIMIT = _env_int("HISTORICAL_PER_SENDER_LIMIT", 100)
HISTORICAL_QUARANTINE_DAYS = _env_int(
    "HISTORICAL_QUARANTINE_DAYS", TRASH_QUARANTINE_DAYS
)

# ---------------------------------------------------------
# PHASE 3 HISTORICAL INDIVIDUAL CLASSIFICATION
# ---------------------------------------------------------
PHASE3_BATCH_SIZE = _env_int("PHASE3_BATCH_SIZE", 250)
# A small pacing delay; API retry/backoff is handled separately.
PHASE3_OPENAI_DELAY_SECONDS = _env_float("PHASE3_OPENAI_DELAY_SECONDS", 0.75)
PHASE3_LEARN_MIN_EXAMPLES = _env_int("PHASE3_LEARN_MIN_EXAMPLES", 3)
PHASE3_LEARN_MIN_CONFIDENCE = _env_float("PHASE3_LEARN_MIN_CONFIDENCE", 0.90)

# ---------------------------------------------------------
# AUTOMATIC WORKER
# ---------------------------------------------------------
AUTO_BACKLOG_REFRESH_HOURS = _env_int("AUTO_BACKLOG_REFRESH_HOURS", 24)
AUTO_INBOX_BATCH_SIZE = _env_int("AUTO_INBOX_BATCH_SIZE", 50)
AUTO_SENDER_POLICY_BATCH_SIZE = _env_int("AUTO_SENDER_POLICY_BATCH_SIZE", 30)
AUTO_HISTORICAL_BULK_BATCH_SIZE = _env_int("AUTO_HISTORICAL_BULK_BATCH_SIZE", 1000)
AUTO_PHASE3_BATCH_SIZE = _env_int("AUTO_PHASE3_BATCH_SIZE", 250)
AUTO_IDLE_SECONDS = _env_int("AUTO_IDLE_SECONDS", 300)
AUTO_ACTIVE_PAUSE_SECONDS = _env_int("AUTO_ACTIVE_PAUSE_SECONDS", 5)
AUTO_CLEANUP_EVERY_CYCLES = _env_int("AUTO_CLEANUP_EVERY_CYCLES", 12)
AUTO_DASHBOARD_EVERY_CYCLES = _env_int("AUTO_DASHBOARD_EVERY_CYCLES", 12)
AUTO_SENDER_POLICY_ENABLED = _env_bool("AUTO_SENDER_POLICY_ENABLED", True)
AUTO_HISTORICAL_ENABLED = _env_bool("AUTO_HISTORICAL_ENABLED", True)
AUTO_PHASE3_ENABLED = _env_bool("AUTO_PHASE3_ENABLED", True)
