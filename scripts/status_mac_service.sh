#!/bin/sh
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.gmail-ai-organizer"
DOMAIN="gui/$(id -u)/$LABEL"
PYTHON="$ROOT/.venv/bin/python"

cd "$ROOT"

echo "===== GMAIL AI ORGANIZER STATUS ====="

if launchctl print "$DOMAIN" >/dev/null 2>&1; then
  launchctl print "$DOMAIN" 2>/dev/null | grep -E "state =|active count|runs =|last exit code" | head -n 20
else
  echo "Service is not installed or not loaded."
fi

echo
echo "===== SAFE CONFIG ====="

if [ -x "$PYTHON" ]; then
  "$PYTHON" - <<'PY'
try:
    import config
    print(f"Trash quarantine:          {config.TRASH_QUARANTINE_DAYS} days")
    print(f"Historical quarantine:     {config.HISTORICAL_QUARANTINE_DAYS} days")
    print(f"Inbox batch size:          {config.AUTO_INBOX_BATCH_SIZE}")
    print(f"Sender-policy batch size:  {config.AUTO_SENDER_POLICY_BATCH_SIZE}")
    print(f"Historical bulk batch:     {config.AUTO_HISTORICAL_BULK_BATCH_SIZE}")
    print(f"Phase 3 batch size:        {config.AUTO_PHASE3_BATCH_SIZE}")
    print(f"Active pause:              {config.AUTO_ACTIVE_PAUSE_SECONDS}s")
    print(f"Idle pause:                {config.AUTO_IDLE_SECONDS}s")
except Exception as exc:
    print(f"Configuration error: {exc}")
PY
else
  echo "Virtual environment Python not found at $PYTHON"
fi

echo
echo "===== DASHBOARD ====="

if [ -x "$PYTHON" ]; then
  "$PYTHON" main.py --phase3-dashboard 2>&1 || true
fi

echo
echo "===== NORMAL LOG (LAST 40 LINES) ====="
tail -n 40 "$ROOT/logs/launchd.log" 2>/dev/null || echo "No launchd.log yet."

echo
echo "===== ERROR LOG (LAST 40 LINES) ====="
tail -n 40 "$ROOT/logs/launchd-error.log" 2>/dev/null || echo "No launchd-error.log yet."
