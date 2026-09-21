#!/bin/sh
set -eu
PLIST="$HOME/Library/LaunchAgents/com.gmail-ai-organizer.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
rm -f "$PLIST"
echo "Gmail AI Organizer background service removed."
