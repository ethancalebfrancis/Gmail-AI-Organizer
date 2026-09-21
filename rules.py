import json
import os


RULES_FILE = "rules.json"


def load_rules():
    """
    Load local classification rules from rules.json.
    """

    if not os.path.exists(RULES_FILE):
        return {
            "sender_rules": {},
            "domain_rules": {},
            "protected_senders": [],
            "protected_domains": [],
        }

    with open(RULES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_sender_domain(sender):
    """
    Extract the domain from a sender email address.
    """

    if not sender or "@" not in sender:
        return ""

    return sender.rsplit("@", 1)[-1].lower().strip()


def build_rule_result(rule, classification_source):
    """
    Convert a saved local rule into the same result structure
    returned by the OpenAI classifier.
    """

    return {
        "category": rule["category"],
        "subcategory": rule["subcategory"],
        "email_state": rule.get(
            "email_state",
            "promotional"
        ),
        "importance": rule["importance"],
        "action_required": rule["action_required"],
        "confidence": 1.0,
        "recommended_action": rule[
            "recommended_action"
        ],
        "reason": (
            "Matched a saved sender rule."
            if classification_source == "sender_rule"
            else "Matched a saved domain rule."
        ),
        "classification_source": classification_source,
    }


def check_local_rule(email):
    """
    Check whether an email matches a saved sender or domain rule.

    Exact sender rules take priority over domain rules.
    """

    rules = load_rules()

    sender = email.get(
        "sender",
        ""
    ).lower().strip()

    domain = get_sender_domain(sender)

    sender_rules = rules.get(
        "sender_rules",
        {}
    )

    domain_rules = rules.get(
        "domain_rules",
        {}
    )

    # Normalize rule keys so matching is case-insensitive.
    sender_rules = {
        key.lower().strip(): value
        for key, value in sender_rules.items()
    }

    domain_rules = {
        key.lower().strip(): value
        for key, value in domain_rules.items()
    }

    # Exact sender rule takes priority.
    if sender in sender_rules:
        return build_rule_result(
            sender_rules[sender],
            "sender_rule"
        )

    # If no sender rule exists, check the sender's domain.
    if domain in domain_rules:
        return build_rule_result(
            domain_rules[domain],
            "domain_rule"
        )

    return None