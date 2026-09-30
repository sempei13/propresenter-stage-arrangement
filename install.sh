#!/bin/bash
# Install the arrangement watcher as a macOS background service (LaunchAgent).
# It starts at login and restarts if it crashes.
#
#   bash install.sh [output_file]
#
# Default output file: ~/ProPresenter Stage Text/arrangement.txt
set -euo pipefail

LABEL="com.trinitydigitalmedia.arrangement-watch"
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HOME/ProPresenter Stage Text/arrangement.txt}"
LOG="$(dirname "$OUT")/arrangement-watch.log"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$(dirname "$OUT")" "$HOME/Library/LaunchAgents"
touch "$OUT"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$DIR/arrangement_watch.py</string>
    <string>$OUT</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Installed. Writing to: $OUT"
echo "Log: $LOG"
