from backlog_cache import get_backlog_counts, get_cached_message_ids
from database import get_historical_action_ids, get_phase3_stats, get_processed_email_ids


def get_dashboard_data():
    backlog = get_backlog_counts()
    cached_ids = get_cached_message_ids()
    handled_ids = get_processed_email_ids() | get_historical_action_ids()
    handled_cached = len(cached_ids & handled_ids)
    remaining = max(backlog["total_messages"] - handled_cached, 0)

    stats = get_phase3_stats()
    return {
        **backlog,
        **stats,
        "handled_cached": handled_cached,
        "remaining": remaining,
    }


def run_phase3_dashboard():
    data = get_dashboard_data()
    cached = data["total_messages"]
    handled = data["handled_cached"]

    print("\n" + "=" * 78)
    print("GMAIL AI ORGANIZER — DASHBOARD")
    print("=" * 78)
    print(f"Cached mailbox messages:   {cached:,}")
    print(f"Historical handled:        {handled:,}")
    print(f"Historical remaining:      {data['remaining']:,}")
    if cached:
        print(f"Historical coverage:       {handled / cached:.1%}")
    print(f"Unique cached senders:     {data['unique_senders']:,}")
    print(f"Sender policies learned:   {data['sender_policies']:,}")
    print(f"Bulk-safe senders:         {data['bulk_safe_senders']:,}")
    print()
    print(f"Organizer records:         {(data.get('total') or 0):,}")
    print(f"OpenAI historical:         {(data.get('openai_historical') or 0):,}")
    print(f"Local/rule classifications:{(data.get('local_or_rule') or 0):>9,}")
    print(f"Learning observations:     {(data.get('learning_observations') or 0):,}")
    print()
    print(f"Keep:                      {(data.get('kept') or 0):,}")
    print(f"Archive:                   {(data.get('archived') or 0):,}")
    print(f"Trash quarantine:          {(data.get('trash_candidates') or 0):,}")
    print(f"Needs review:              {(data.get('review') or 0):,}")
    print("=" * 78)

    return data
