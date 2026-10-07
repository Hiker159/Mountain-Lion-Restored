#!/bin/bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$(/usr/bin/sw_vers -productVersion)" in
  10.9|10.9.*) ;;
  *) echo 'Use this on Mavericks only.'; exit 1 ;;
esac
OUT="$HERE/Calendar-startup-$(/bin/date +%Y%m%d-%H%M%S)-$$"
/bin/mkdir "$OUT"
/usr/bin/sw_vers > "$OUT/system.txt"
/bin/date >> "$OUT/system.txt"
/usr/bin/python "$HERE/calendar_agent_control.py" status > "$OUT/helper-status.txt" 2>&1 || true
STATE="$HOME/Library/Application Support/ML-Calendar/Agent"
for ITEM in CalendarAgent.log CalendarAgent.log.previous org.local.CalendarAgent.plist; do
  if [ -f "$STATE/$ITEM" ]; then
    if [[ "$ITEM" == *.log* ]]; then /usr/bin/tail -n 5000 "$STATE/$ITEM" > "$OUT/$ITEM";
    else /bin/cp "$STATE/$ITEM" "$OUT/$ITEM"; fi
  fi
done
if [ -f "$HOME/Library/LaunchAgents/org.local.CalendarAgent.plist" ]; then
  /bin/cp "$HOME/Library/LaunchAgents/org.local.CalendarAgent.plist" "$OUT/login-setting.plist"
fi
if [ -f "$HERE/manifest.json" ]; then /bin/cp "$HERE/manifest.json" "$OUT/build-manifest.json"; fi
/usr/bin/codesign --verify --deep "$HERE/Mountain Lion Calendar.app" > "$OUT/signature.txt" 2>&1 || true
/usr/bin/ditto -c -k --keepParent "$OUT" "$OUT.zip"
echo "Log collected without restarting the helper: $OUT.zip"
echo 'Review before sharing; logs may contain personal information.'
echo 'Press Return to close.'
read -r DONE
