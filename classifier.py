import os
import time
from datetime import datetime, timezone
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from pydantic import BaseModel

from config import CATEGORIES, MAX_BODY_CHARACTERS


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


class EmailClassification(BaseModel):
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

    email_state: Literal[
        "active",
        "completed",
        "informational",
        "promotional",
        "unknown",
    ]

    importance: Literal[
        "low",
        "medium",
        "high",
    ]

    action_required: bool

    confidence: float

    recommended_action: Literal[
        "keep",
        "archive",
        "review",
        "trash_candidate",
    ]

    reason: str


def _classify_email(email):
    body = email["body"] or email["snippet"]
    body = body[:MAX_BODY_CHARACTERS]

    categories = ", ".join(CATEGORIES)

    instructions = f"""
You are an email classification system for a personal Gmail inbox.

Classify each email into exactly one of these categories:

{categories}

Return:
- category
- subcategory
- email_state
- importance
- whether action is actually required from the user
- confidence
- recommended action
- a short reason


EMAIL STATE:

Determine the current lifecycle state of the email.

Use exactly one of:

active:
The email relates to something currently ongoing, upcoming,
unresolved, or still useful for a current transaction, event,
task, reservation, delivery, appointment, application, repair,
ticket, payment, or other matter.

Examples:
- package currently shipping
- package out for delivery
- upcoming movie or event ticket
- upcoming hotel reservation
- active repair
- active job application
- upcoming appointment
- payment currently due
- unresolved account issue
- deadline that has not passed

completed:
The underlying transaction, task, or event has finished and the
email is primarily useful as a historical record.

Examples:
- payment received confirmation
- delivered package
- completed refund
- completed return
- completed repair
- past appointment
- completed reservation
- ordinary receipt for a completed purchase

informational:
The email provides information or reference material but does not
represent an active obligation, unresolved transaction, or
promotional offer.

Examples:
- news digest
- informational newsletter
- educational material
- general account information
- product or service update
- policy information
- informational announcement

promotional:
The primary purpose is advertising, selling, promoting, offering,
or encouraging optional engagement.

Examples:
- retail sales
- coupons
- product advertisements
- streaming recommendations
- promotional newsletters
- optional game rewards
- limited-time offers
- loyalty promotions
- upgrade offers

unknown:
Use only when there is not enough information to reliably determine
the lifecycle state.

IMPORTANT EMAIL STATE RULES:

A limited-time promotion is promotional, NOT active.

An optional opportunity does not become active simply because it
expires.

An active email does NOT automatically mean action_required is true.

For example:
- an upcoming movie ticket is active but may require no action
- a package currently shipping is active but may require no action
- an upcoming reservation is active but may require no action

A completed email does NOT mean it should be deleted.

Financial records, receipts, confirmations, and other important
records may still need to be archived or retained.

Classify the state based on the underlying purpose and current status
of the email, not merely words such as "today", "now", "expires",
"deadline", or "limited time".


IMPORTANCE:

high:
The email is important or time-sensitive and the user would
reasonably want to notice it soon.

Examples:
- security warning
- failed payment
- required response
- imminent appointment
- important deadline
- urgent personal correspondence

medium:
The email contains useful personalized information worth keeping
or reviewing, but is not urgent.

low:
Promotional, informational, repetitive, or otherwise low-priority.


ACTION REQUIRED:

Set action_required to true ONLY when the email explicitly requires
or clearly expects the user to perform an action.

Examples:
- respond to someone
- make or resolve a payment
- submit documentation
- complete registration
- verify an account
- reset or change something
- approve or deny something
- attend an appointment or meeting
- complete a required task
- address a failed transaction
- take action by a genuine deadline

Do NOT mark action_required true merely because:
- an order shipped
- a package will arrive
- a receipt was issued
- an account setting changed successfully
- the user could optionally review something
- a promotional offer expires
- the email contains links
- the email contains useful information

Optional opportunities are NEVER considered required actions.

Set action_required to false for:
- coupons or discounts that expire
- game rewards that can optionally be claimed
- limited-time promotions
- sales ending soon
- optional event participation
- optional purchases
- optional reservations
- optional applications
- marketing calls-to-action such as "Shop Now", "Claim Now",
  "Buy Tickets", "Learn More", or "Register Now"

An expiration date or limited-time offer does NOT make something
action_required.

action_required means the user faces a meaningful consequence,
obligation, unresolved task, or expected response if they do nothing.


RECOMMENDED ACTION:

keep:
Important, active, personal, time-sensitive, or actionable messages
that should remain visible in the inbox.

archive:
Useful messages worth retaining but which do not need to remain
in the inbox.

trash_candidate:
Low-value promotional or repetitive content that is unlikely to
have future value.

review:
Use when the appropriate action is genuinely uncertain.


SAFETY RULES:

Never recommend trash_candidate for:
- personal correspondence
- school or university messages
- banking or financial transactions
- receipts
- bills
- account or security notifications
- government messages
- employment or recruiting messages
- travel reservations
- active orders
- appointments
- anything requiring action

For marketing and newsletters:

Use archive if the content has meaningful reference value beyond
the promotion itself.

Use trash_candidate for generic advertising, sales promotions,
product advertisements, repetitive promotional campaigns,
optional promotional offers, and similar low-value messages.

Do not recommend keep merely because a promotional offer is
time-limited.

Be conservative when genuinely uncertain.


CONSISTENCY GUIDANCE:

The fields should describe different aspects of the email and should
not be forced to agree artificially.

For example:

Upcoming movie ticket:
category = Events
email_state = active
action_required = false
recommended_action = keep

Payment confirmation:
category = Financial
email_state = completed
action_required = false
recommended_action = archive

Package currently shipping:
category = Shopping & Orders
email_state = active
action_required = false
recommended_action = keep

Delivered package:
category = Shopping & Orders
email_state = completed
action_required = false
recommended_action = archive

Generic clothing sale:
category = Marketing
email_state = promotional
action_required = false
recommended_action = trash_candidate

News digest:
category = Newsletters
email_state = informational
action_required = false
recommended_action = archive

Payment failure:
category = Financial
email_state = active
importance = high
action_required = true
recommended_action = keep

Use the actual contents of the email to make the final determination.

DATE AWARENESS:
The email date and current date are provided. Use them when deciding lifecycle
state. An old ticket, old event, old delivery, expired reservation, old deadline,
or other clearly past matter should not be treated as currently active merely
because the original email used future-tense language. Preserve records when
appropriate, but prefer completed/archive for clearly finished historical items.
"""

    email_text = f"""
CURRENT DATE (UTC):
{datetime.now(timezone.utc).date().isoformat()}

EMAIL DATE:
{email.get("date", "")}

FROM:
{email["sender_raw"]}

SUBJECT:
{email["subject"]}

BODY:
{body}
"""

    response = get_openai_client().responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        store=False,
        instructions=instructions,
        input=email_text,
        text_format=EmailClassification,
    )

    result = response.output_parsed

    if result is None:
        raise ValueError(
            "OpenAI did not return a valid email classification."
        )

    return result.model_dump()


def classify_email(email, max_retries=3):
    for attempt in range(max_retries):
        try:
            return _classify_email(email)

        except RateLimitError:
            if attempt == max_retries - 1:
                raise

            wait_time = 10 * (attempt + 1)

            print(
                f"Rate limit reached. "
                f"Waiting {wait_time} seconds..."
            )

            time.sleep(wait_time)
