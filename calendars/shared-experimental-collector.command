#!/bin/bash
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/Shared-store-diagnostics-$(/bin/date +%Y%m%d-%H%M%S)-$$"
/bin/mkdir "$OUT" || exit 1
/bin/date > "$OUT/system.txt"
/usr/bin/sw_vers >> "$OUT/system.txt"
/usr/bin/python "$HERE/Calendar/calendar_agent_control.py" status > "$OUT/helper-status.txt" 2>&1
for NAME in Notes Contacts Calendar; do
  LOG="$HOME/Library/Logs/ML Shared Experiment/$NAME.log"
  if [ -f "$LOG" ]; then /usr/bin/tail -n 3000 "$LOG" > "$OUT/$NAME.log"; fi
  /usr/bin/codesign --verify --deep "$HERE/$NAME/Mountain Lion $NAME.app" > "$OUT/$NAME-signature.txt" 2>&1
  echo "Signature exit status: $?" >> "$OUT/$NAME-signature.txt"
done
AGENT="$HOME/Library/Application Support/ML-Shared-Experiment/Agent/CalendarAgent.log"
if [ -f "$AGENT" ]; then /usr/bin/tail -n 5000 "$AGENT" > "$OUT/shared-agent.log"; fi
for STORE in "$HOME/Library/Calendars" "$HOME/Library/Application Support/iCal" "$HOME/Library/Application Support/AddressBook"; do
  /bin/ls -ld "$STORE" >> "$OUT/store-directories.txt" 2>&1
done
/bin/cp "$HERE/manifest.json" "$OUT/manifest.json"
/usr/bin/ditto -c -k --keepParent "$OUT" "$OUT.zip"
echo "Diagnostics: $OUT.zip"
echo 'Review before sharing; app logs may contain personal details. No databases copied.'
echo 'Press Return to close.'
read -r DONE
