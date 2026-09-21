import base64
import os
from email.utils import parseaddr

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]

_LABEL_CACHE = {}


def get_gmail_service():
    """Authenticate to Gmail, recovering cleanly from revoked/expired tokens."""
    creds = None

    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file(
                "token.json",
                SCOPES,
            )
        except (ValueError, OSError):
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            # The refresh token was revoked/expired. Fall through to a fresh
            # browser authorization instead of crashing the organizer.
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json",
            SCOPES,
        )
        creds = flow.run_local_server(port=0)

        with open("token.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build(
        "gmail",
        "v1",
        credentials=creds,
        cache_discovery=False,
    )


def list_inbox_messages(
    service,
    max_results=10,
):
    results = (
        service.users()
        .messages()
        .list(
            userId="me",
            labelIds=["INBOX"],
            maxResults=max_results,
        )
        .execute()
    )

    return results.get(
        "messages",
        [],
    )


def decode_data(data):
    if not data:
        return ""

    return base64.urlsafe_b64decode(
        data
    ).decode(
        "utf-8",
        errors="ignore",
    )


def extract_body(payload):
    mime_type = payload.get(
        "mimeType",
        "",
    )

    body = payload.get(
        "body",
        {},
    )

    if (
        mime_type == "text/plain"
        and body.get("data")
    ):
        return decode_data(
            body["data"]
        )

    text = ""

    for part in payload.get(
        "parts",
        [],
    ):
        part_type = part.get(
            "mimeType",
            "",
        )

        if part_type == "text/plain":
            text += decode_data(
                part
                .get("body", {})
                .get("data")
            )

        elif part_type.startswith(
            "multipart/"
        ):
            text += extract_body(part)

    return text


def get_message(
    service,
    message_id,
):
    message = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full",
        )
        .execute()
    )

    payload = message.get(
        "payload",
        {},
    )

    headers = payload.get(
        "headers",
        [],
    )

    header_dict = {
        header["name"].lower():
            header["value"]
        for header in headers
    }

    sender_raw = header_dict.get(
        "from",
        "",
    )

    return {
        "id": message_id,
        "thread_id": message.get(
            "threadId"
        ),
        "sender": parseaddr(
            sender_raw
        )[1],
        "sender_raw": sender_raw,
        "subject": header_dict.get(
            "subject",
            "",
        ),
        "date": header_dict.get(
            "date",
            "",
        ),
        "body": extract_body(
            payload
        ),
        "snippet": message.get(
            "snippet",
            "",
        ),
    }


def _load_label_cache(service):
    if _LABEL_CACHE:
        return

    labels = (
        service.users()
        .labels()
        .list(userId="me")
        .execute()
        .get("labels", [])
    )

    for label in labels:
        _LABEL_CACHE[label["name"]] = label["id"]


def get_or_create_label(service, label_name):
    """Resolve a Gmail label ID with an in-process cache."""
    _load_label_cache(service)

    if label_name in _LABEL_CACHE:
        return _LABEL_CACHE[label_name]

    label = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )

    _LABEL_CACHE[label_name] = label["id"]
    return label["id"]


def apply_label(
    service,
    message_id,
    label_name,
):
    label_id = get_or_create_label(
        service,
        label_name,
    )

    (
        service.users()
        .messages()
        .modify(
            userId="me",
            id=message_id,
            body={
                "addLabelIds": [
                    label_id
                ]
            },
        )
        .execute()
    )


def remove_label(
    service,
    message_id,
    label_name,
):
    """Remove one custom label from a Gmail message if the label exists."""
    label_id = get_label_id(service, label_name)
    if not label_id:
        return

    (
        service.users()
        .messages()
        .modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": [label_id]},
        )
        .execute()
    )


def archive_message(
    service,
    message_id,
):
    (
        service.users()
        .messages()
        .modify(
            userId="me",
            id=message_id,
            body={
                "removeLabelIds": [
                    "INBOX"
                ]
            },
        )
        .execute()
    )


def quarantine_message(
    service,
    message_id,
    label_id,
):
    """
    Quarantine a historical trash candidate.

    Adds the quarantine label and removes the
    message from the Inbox.

    Does NOT move the message to Gmail Trash.
    """

    (
        service.users()
        .messages()
        .modify(
            userId="me",
            id=message_id,
            body={
                "addLabelIds": [
                    label_id
                ],
                "removeLabelIds": [
                    "INBOX"
                ],
            },
        )
        .execute()
    )


def get_label_id(service, label_name):
    _load_label_cache(service)
    return _LABEL_CACHE.get(label_name)


def list_messages_with_label(
    service,
    label_name,
    max_results=None,
):
    """List messages carrying a label, paging through the full set by default."""
    label_id = get_label_id(service, label_name)

    if not label_id:
        return []

    messages = []
    page_token = None

    while True:
        if max_results is not None:
            remaining = max_results - len(messages)
            if remaining <= 0:
                break
            request_size = min(500, remaining)
        else:
            request_size = 500

        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=[label_id],
                maxResults=request_size,
                pageToken=page_token,
            )
            .execute()
        )

        messages.extend(response.get("messages", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return messages


def get_message_label_ids(
    service,
    message_id,
):
    message = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="minimal",
        )
        .execute()
    )

    return message.get(
        "labelIds",
        [],
    )


def trash_message(
    service,
    message_id,
):
    """
    Move a Gmail message to Trash.

    IMPORTANT:
    This should only be called after the
    quarantine/retention period has expired.
    """

    (
        service.users()
        .messages()
        .trash(
            userId="me",
            id=message_id,
        )
        .execute()
    )


def list_all_messages(
    service,
    query=None,
    max_messages=None,
    page_size=500,
):
    messages = []
    page_token = None

    while True:
        remaining = None

        if max_messages is not None:
            remaining = (
                max_messages
                - len(messages)
            )

            if remaining <= 0:
                break

        request_size = page_size

        if remaining is not None:
            request_size = min(
                page_size,
                remaining,
            )

        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=request_size,
                pageToken=page_token,
            )
            .execute()
        )

        batch = response.get(
            "messages",
            [],
        )

        messages.extend(batch)

        print(
            f"\rDiscovered "
            f"{len(messages):,} messages...",
            end="",
            flush=True,
        )

        page_token = response.get(
            "nextPageToken"
        )

        if not page_token:
            break

    print()

    return messages


def get_message_metadata(
    service,
    message_id,
):
    message = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=[
                "From",
                "Subject",
                "Date",
            ],
        )
        .execute()
    )

    headers = {
        header["name"].lower():
            header["value"]
        for header in (
            message
            .get("payload", {})
            .get("headers", [])
        )
    }

    return {
        "id": message_id,
        "thread_id": message.get(
            "threadId",
            "",
        ),
        "sender_raw": headers.get(
            "from",
            "",
        ),
        "subject": headers.get(
            "subject",
            "",
        ),
        "date_raw": headers.get(
            "date",
            "",
        ),
        "internal_date": message.get(
            "internalDate"
        ),
        "label_ids": message.get(
            "labelIds",
            [],
        ),
    }