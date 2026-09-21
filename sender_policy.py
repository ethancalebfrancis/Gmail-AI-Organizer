import os
import time
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from pydantic import BaseModel

from config import CATEGORIES


load_dotenv()

_client = None


def get_openai_client():
    """Create the OpenAI client lazily so non-AI modes work without a key."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to .env before running AI classification."
            )
        _client = OpenAI(api_key=api_key)
    return _client


class SenderPolicy(BaseModel):
    category: Literal[
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

    subcategory: str

    bulk_safe: bool

    bulk_action: Literal[
        "trash_candidate",
        "archive",
        "keep",
        "individual_classification",
    ]

    confidence: float

    sender_type: str

    reason: str


def _analyze_sender_policy(
    sender,
    domain,
    subjects,
):
    categories = ", ".join(CATEGORIES)

    subject_text = "\n".join(
        f"- {subject}"
        for subject in subjects
    )

    instructions = f"""
You are analyzing an email sender for a personal Gmail
organization system.

The available categories are:

{categories}

You are NOT classifying one email.

You are deciding whether emails from this sender are
consistent enough to safely process in bulk.

You will receive:
- sender email address
- sender domain
- representative historical subject lines

Determine:

- category
- subcategory
- sender_type
- whether the sender is safe for bulk processing
- the appropriate bulk action
- confidence
- a concise reason

BULK SAFE:

bulk_safe should be true ONLY when the sender has a clear,
consistent purpose and applying the same organizational
policy to historical messages from this sender is unlikely
to hide important mail.

bulk_safe must be false when the sender could reasonably
send multiple materially different types of messages.

Examples of potentially mixed senders:
- retailers that send both receipts and advertisements
- banks
- financial institutions
- account/security systems
- schools or universities
- employers
- recruiters
- government services
- shipping services
- marketplaces
- travel providers
- personal correspondents

When uncertain, bulk_safe must be false.

BULK ACTION:

trash_candidate:
Use ONLY for highly consistent low-value advertising,
sales campaigns, generic promotions, coupons, product
advertisements, repetitive promotional campaigns, and
similar content with little future value.

archive:
Use for consistent informational/newsletter content that
may have historical or reference value but does not need
to remain visible.

keep:
Use only when this sender's messages generally deserve to
remain visible.

individual_classification:
Use when messages from this sender should continue to be
classified individually.

IMPORTANT SAFETY RULES:

Do not bulk-trash:
- school or university communications
- admissions communications
- employment or recruiting messages
- financial messages
- receipts
- account/security messages
- government messages
- personal correspondence
- order confirmations
- shipping/tracking messages
- travel reservations
- appointments
- messages that may contain required actions

A sender being categorized by Gmail as Promotions does NOT
prove that its messages are disposable.

College recruiting and admissions marketing should be
categorized as School and should NOT be bulk trashed.

Job alerts and recruiting should be Work & Career and
should NOT be bulk trashed.

Be conservative. individual_classification is preferred
whenever sender behavior may be mixed.
"""

    input_text = f"""
SENDER:
{sender}

DOMAIN:
{domain}

REPRESENTATIVE HISTORICAL SUBJECTS:

{subject_text}
"""

    response = get_openai_client().responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        store=False,
        instructions=instructions,
        input=input_text,
        text_format=SenderPolicy,
    )

    result = response.output_parsed

    if result is None:
        raise ValueError(
            "No valid sender policy was returned."
        )

    return result.model_dump()


def analyze_sender_policy(
    sender,
    domain,
    subjects,
    max_retries=3,
):
    for attempt in range(max_retries):
        try:
            return _analyze_sender_policy(
                sender,
                domain,
                subjects,
            )

        except RateLimitError:
            if attempt == max_retries - 1:
                raise

            wait_time = 10 * (attempt + 1)

            print(
                f"Rate limit reached. "
                f"Waiting {wait_time} seconds..."
            )

            time.sleep(wait_time)
