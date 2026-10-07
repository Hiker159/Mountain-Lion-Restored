#!/bin/bash
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$(/usr/bin/sw_vers -productVersion)" in
  10.9|10.9.*) ;;
  *) echo 'Run this on Mavericks.'; exit 1 ;;
esac
if [ ! -f "$HERE/calendar_agent_control.py" ]; then
  echo 'Place this command inside your existing Calendar folder and try again.'
  read -r DONE
  exit 1
fi
OUT="$HERE/Calendar-recurrence-$(/bin/date +%Y%m%d-%H%M%S)-$$"
/bin/mkdir "$OUT" || exit 1
START="$(/bin/date +%s)"
/usr/bin/sw_vers > "$OUT/system.txt"
/bin/date >> "$OUT/system.txt"
/usr/bin/python "$HERE/calendar_agent_control.py" status > "$OUT/helper-before.txt" 2>&1
echo "Helper status exit code: $?" >> "$OUT/helper-before.txt"
if [ -f "$HERE/manifest.json" ]; then /bin/cp "$HERE/manifest.json" "$OUT/build-manifest.json"; fi
/usr/bin/codesign --verify --deep "$HERE/Mountain Lion Calendar.app" > "$OUT/signature.txt" 2>&1
echo "Signature check exit code: $?" >> "$OUT/signature.txt"
echo 'This collector does not start or stop Calendar or its helper.'
echo 'Keep this window open. Follow the recurring-alert test guide.'
echo 'After the final alert time plus two minutes, press Return here.'
read -r READY
for QUESTION in 'Control: expected time, actual time and sound?' 'Moved: original time, new time, actual alert time and sound?' 'Deleted: expected time; did any alert appear?' 'After reopening: do later occurrences remain, and are exceptions correct?' 'Any sleep/wake, duplicate alerts or other problems?'; do
  echo "$QUESTION"
  read -r ANSWER
  printf '%s\n%s\n\n' "$QUESTION" "$ANSWER" >> "$OUT/observations.txt"
done
/bin/date > "$OUT/finished.txt"
/usr/bin/python "$HERE/calendar_agent_control.py" status > "$OUT/helper-after.txt" 2>&1
echo "Helper status exit code: $?" >> "$OUT/helper-after.txt"
STATE="$HOME/Library/Application Support/ML-Calendar/Agent"
for NAME in CalendarAgent.log CalendarAgent.log.previous; do
  if [ -f "$STATE/$NAME" ]; then /usr/bin/tail -n 5000 "$STATE/$NAME" > "$OUT/$NAME"; fi
done
/usr/bin/syslog -F bsd -k Time ge "$START" 2> "$OUT/system-query-errors.txt" |
  /usr/bin/awk '/Calendar|iCal|calendar|usernoted|NotificationCenter|sandbox|Sandbox|tccd/ {print}' > "$OUT/system-messages.txt"
/usr/bin/pmset -g log 2> "$OUT/power-log-errors.txt" | /usr/bin/tail -n 1500 |
  /usr/bin/awk '/[Ss]leep|[Ww]ake/ {print}' > "$OUT/recent-sleep-wake.txt"
/usr/bin/ditto -c -k --keepParent "$OUT" "$OUT.zip"
if [ "$?" != 0 ]; then echo "ZIP failed; the diagnostic folder remains at $OUT"; exit 1; fi
echo "Please send: $OUT.zip"
echo 'Review before sharing; logs can contain event details. No databases are copied.'
echo 'Press Return to close.'
read -r DONE
