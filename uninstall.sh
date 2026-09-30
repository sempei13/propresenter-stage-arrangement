#!/bin/bash
# Stop the arrangement watcher and remove its background service.
set -euo pipefail

LABEL="com.trinitydigitalmedia.arrangement-watch"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Uninstalled."
