#!/bin/sh
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.gmail-ai-organizer.plist"
LOGDIR="$ROOT/logs"

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required."
    exit 1
  fi
  "$(command -v python3)" -m venv "$ROOT/.venv"
fi

PYTHON="$ROOT/.venv/bin/python"
"$PYTHON" -m pip install -r "$ROOT/requirements.txt"

# Preflight configuration before registering a KeepAlive LaunchAgent. This
# prevents a malformed .env from creating a crash/restart loop.
(
  cd "$ROOT"
  "$PYTHON" - <<'PY'
import config
from database import initialize_database, migrate_database
initialize_database()
migrate_database()
print("Configuration preflight passed.")
print(f"Trash quarantine: {config.TRASH_QUARANTINE_DAYS} days")
print(f"Historical quarantine: {config.HISTORICAL_QUARANTINE_DAYS} days")
PY
)

mkdir -p "$HOME/Library/LaunchAgents" "$LOGDIR"
: > "$LOGDIR/launchd.log"
: > "$LOGDIR/launchd-error.log"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.gmail-ai-organizer</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$ROOT/main.py</string>
    <string>--auto</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>$LOGDIR/launchd.log</string>
  <key>StandardErrorPath</key><string>$LOGDIR/launchd-error.log</string>
</dict>
</plist>
PLISTEOF

launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/com.gmail-ai-organizer"
launchctl kickstart -k "gui/$(id -u)/com.gmail-ai-organizer"
echo "Gmail AI Organizer background service installed and started."
