# Gmail AI Organizer

A production-oriented Python application that organizes Gmail with a hybrid of deterministic rules, learned sender/subject patterns, and OpenAI classification.

It is designed for both **continuous Inbox maintenance** and **large historical mailbox cleanup**. The system prefers local rules whenever possible, uses AI only when a message is genuinely ambiguous, records decisions in SQLite, and places low-value mail in a reversible quarantine before it reaches Gmail Trash.

## Highlights

- Gmail API integration with OAuth and automatic token refresh/re-authorization
- Structured AI classification with categories, lifecycle state, importance, confidence, and action requirements
- Current Inbox processing plus resumable historical cleanup
- Sender rules, sender-policy analysis, subject-pattern policies, and deterministic historical rules
- Local learning from repeated high-confidence historical classifications
- SQLite-backed processing ledger and backlog cache
- Safe `keep`, `archive`, `review`, and `trash_candidate` actions
- Configurable trash quarantine with rescue checks for starred/restored/protected mail
- Autonomous worker that drains the historical backlog, refreshes its mailbox cache daily, and then continues monitoring the Inbox
- macOS launchd service with configuration preflight and status diagnostics
- Dashboard and preview modes for visibility and auditing
- GitHub Actions CI for compilation and unit tests

## Architecture

```mermaid
flowchart TD
    A[Gmail] --> B{Current Inbox or Historical Backlog?}
    B -->|Current Inbox| C[Inbox Processor]
    B -->|Historical| D[Backlog Cache]

    C --> E[Local Sender / Domain Rules]
    D --> F[Sender Policy Analysis]
    F --> G[Bulk-safe Historical Processor]
    D --> H[Phase 3 Individual Classifier]

    H --> E
    E --> I[Sender + Subject Pattern Policy]
    I --> J[Learned Pattern]
    J --> K[Deterministic Historical Rule]
    K --> L[OpenAI Fallback]

    C --> M[Action Policy]
    H --> M
    G --> M

    M --> N[Keep]
    M --> O[Archive]
    M --> P[Needs Review]
    M --> Q[Trash Quarantine]

    Q --> R[Retention + Safety Recheck]
    R -->|Still eligible| S[Gmail Trash]
    R -->|Starred / Restored / Protected| T[Rescued]

    M --> U[(SQLite Ledger)]
    L --> V[(Pattern Learning)]
    V --> J
```

## Classification model

Each message is assigned:

- `category`
- `subcategory`
- `email_state` (`active`, `completed`, `informational`, `promotional`, `unknown`)
- `importance`
- `action_required`
- `confidence`
- `recommended_action`
- `classification_source`

The final action policy is intentionally more conservative than the raw model recommendation. Financial, security, school, career, shopping/order, receipt, travel, event, and personal categories are protected from automatic trashing.

## Safety model

`trash_candidate` does **not** immediately delete mail. The organizer applies `AI/Trash Candidates`, removes the message from the Inbox, and records the quarantine in SQLite. After the configured retention period, cleanup re-checks Gmail before moving the message to Trash.

A message is rescued or protected if, among other safeguards, it is starred, restored to the Inbox, carries an important/action/review label, belongs to a protected category, or no longer carries the quarantine label.

The default quarantine is 14 days. It can be shortened locally, for example:

```env
TRASH_QUARANTINE_DAYS=7
HISTORICAL_QUARANTINE_DAYS=7
```

## Modes

```bash
python main.py                         # Process current Inbox mail
python main.py --once                  # One complete production cycle
python main.py --auto                  # Continuous production worker
python main.py --cleanup               # Process expired quarantine
python main.py --phase3-dashboard      # Backlog/progress dashboard
python main.py --backlog-scan          # Refresh historical metadata cache
python main.py --sender-policy-preview # Learn safe sender policies (no Gmail changes)
python main.py --historical-preview    # Preview approved bulk historical work
python main.py --historical-live       # Run approved bulk historical batch
python main.py --historical-classify-run-preview
python main.py --historical-classify-live
```

## Quick start

```bash
git clone https://github.com/ethancalebfrancis/Gmail-AI-Organizer.git
cd Gmail-AI-Organizer

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

Add `OPENAI_API_KEY` to `.env`, then place a Google OAuth desktop client file at `credentials.json`. The first Gmail connection opens a browser authorization flow and writes `token.json` locally.

Run one foreground cycle first:

```bash
python main.py --once
```

Then install the background worker on macOS:

```bash
chmod +x scripts/*.sh
./scripts/install_mac_service.sh
```

The installer validates the Python configuration before registering the KeepAlive LaunchAgent. A malformed `.env` therefore fails before launchd enters a restart loop.

Check status at any time with:

```bash
./scripts/status_mac_service.sh
```

Remove the service with:

```bash
./scripts/uninstall_mac_service.sh
```

## Faster historical cleanup

For a very large mailbox, the worker can be made more aggressive through local `.env` settings without changing source code:

```env
AUTO_INBOX_BATCH_SIZE=250
AUTO_SENDER_POLICY_BATCH_SIZE=100
AUTO_HISTORICAL_BULK_BATCH_SIZE=5000
AUTO_PHASE3_BATCH_SIZE=500
AUTO_ACTIVE_PAUSE_SECONDS=1
AUTO_IDLE_SECONDS=60
```

These values increase throughput; the classification and protected-category safety rules remain unchanged.

## Local state and secrets

Sensitive/runtime files are intentionally excluded from Git:

- `.env`
- `credentials.json`
- `token.json`
- SQLite databases
- logs
- virtual environments

Keep API keys in `.env`. Do not store an OpenAI key in launchd's global environment or paste it into logs, screenshots, issues, or commits.

## Autonomous operation

`python main.py --auto` runs the production pipeline continuously:

1. process new Inbox messages;
2. learn policies for promotion-heavy historical senders;
3. drain bulk-safe historical messages;
4. classify remaining historical messages through the Phase 3 hierarchy;
5. run quarantine cleanup periodically;
6. continue polling the Inbox after the historical backlog reaches zero.

Processing is resumable because successful Gmail actions are recorded immediately. If the process stops, previously completed message IDs are skipped on restart.

## Testing

```bash
python -m py_compile *.py
python -m unittest discover -s tests -v
```

## Tech stack

Python, Gmail API, OpenAI API, Pydantic, SQLite, OAuth 2.0.
