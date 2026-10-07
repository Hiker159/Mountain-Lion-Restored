#!/bin/bash
set -u
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_APP="$TEST_DIR/Mountain Lion Calendar.app"
TEST_PROFILE="$TEST_DIR/calendar-trial.sb"
case "$(/usr/bin/sw_vers -productVersion)" in
  10.9|10.9.*) ;;
  *) echo 'Run this on the Mavericks laptop only.'; exit 1 ;;
esac
if [ ! -x "$TEST_APP/Contents/MacOS/Calendar" ] || [ ! -f "$TEST_PROFILE" ]; then
  echo 'Keep this command, the app, and calendar-trial.sb together in the extracted folder.'
  exit 1
fi
TEST_OUT="$TEST_DIR/Calendar-diagnostics-$(/bin/date +%Y%m%d-%H%M%S)-$$"
/bin/mkdir "$TEST_OUT" || exit 1
/usr/bin/touch "$TEST_OUT/start-marker"
if [ -f "$TEST_DIR/manifest.json" ]; then /bin/cp "$TEST_DIR/manifest.json" "$TEST_OUT/build-manifest.json"; fi
TEST_START_EPOCH="$(/bin/date +%s)"
TEST_DATA="$HOME/Library/MLCalData"
TEST_SUPPORT="$HOME/Library/Application Support/ML-Calendar"
/bin/mkdir -p "$TEST_DATA" "$TEST_SUPPORT" || exit 1
SANDBOX=(/usr/bin/sandbox-exec
  -D "STOCK_CALENDARS=$HOME/Library/Calendars"
  -D "STOCK_ICAL_SUPPORT=$HOME/Library/Application Support/iCal"
  -D "STOCK_CONTACTS=$HOME/Library/Application Support/AddressBook"
  -D "STOCK_ICAL_PREFS=$HOME/Library/Preferences/com.apple.iCal.plist"
  -f "$TEST_PROFILE")
snapshot_native_store() {
  /bin/date
  for TEST_FILE in "$HOME/Library/Calendars/Calendar Cache" "$HOME/Library/Calendars/Calendar Cache-wal" "$HOME/Library/Application Support/AddressBook/AddressBook-v22.abcddb" "$HOME/Library/Application Support/AddressBook/AddressBook-v22.abcddb-wal"; do
    if [ -f "$TEST_FILE" ]; then /usr/bin/shasum -a 256 "$TEST_FILE"; else echo "Absent: $TEST_FILE"; fi
  done
}
{
  /bin/date
  /usr/bin/sw_vers
  /usr/bin/uname -m
  echo "Local test data: $TEST_DATA"
  /usr/bin/codesign --verify --deep --verbose=2 "$TEST_APP"
} > "$TEST_OUT/launch.log" 2>&1
snapshot_native_store > "$TEST_OUT/native-store-before.txt"
if "${SANDBOX[@]}" /usr/bin/true >> "$TEST_OUT/launch.log" 2>&1 &&    /usr/bin/python "$TEST_DIR/calendar_agent_control.py" start >> "$TEST_OUT/agent-control.log" 2>&1; then
  echo 'Launching Calendar local-only test. Use a temporary account with no important data or Internet Accounts.'
  "${SANDBOX[@]}" /usr/bin/env DYLD_PRINT_LIBRARIES=1 "$TEST_APP/Contents/MacOS/Calendar" \
    -MLCalDataDirectory "$TEST_DATA" -iCalApplicationSupportDirectory "$TEST_SUPPORT" >> "$TEST_OUT/launch.log" 2>&1
  TEST_RESULT=$?
  echo "Calendar exit status: $TEST_RESULT" >> "$TEST_OUT/launch.log"
  echo 'Calendar is closed, but its test alert helper is still running.'
  echo 'Wait for your scheduled alert, then press Return to collect diagnostics.'
  read -r TEST_ALERT_DONE
else
  echo 'The protective profile or alert helper could not start. Calendar was not launched; see agent-control.log.' | /usr/bin/tee -a "$TEST_OUT/launch.log"
fi
/usr/bin/python "$TEST_DIR/calendar_agent_control.py" status > "$TEST_OUT/agent-status.txt" 2>&1
TEST_AGENT_LOG="$TEST_SUPPORT/Agent/CalendarAgent.log"
if [ -f "$TEST_AGENT_LOG" ]; then
  /usr/bin/tail -n 5000 "$TEST_AGENT_LOG" > "$TEST_OUT/agent.log"
fi
snapshot_native_store > "$TEST_OUT/native-store-after.txt"
/usr/bin/pmset -g log 2> "$TEST_OUT/power-log-errors.txt" | /usr/bin/tail -n 1500 | /usr/bin/awk '/[Ss]leep|[Ww]ake/ {print}' > "$TEST_OUT/recent-sleep-wake.txt"
/bin/ls -la "$TEST_DATA" > "$TEST_OUT/restored-store-status.txt" 2>&1
/bin/sleep 5
if [ -r /var/log/system.log ]; then
  /usr/bin/tail -n 3000 /var/log/system.log | /usr/bin/awk '/Calendar|iCal|calendar|usernoted|NotificationCenter|sandbox|Sandbox/ {print}' > "$TEST_OUT/calendar-system-messages.txt"
fi
/usr/bin/syslog -F bsd -k Time ge "$TEST_START_EPOCH" 2> "$TEST_OUT/asl-query-errors.txt" |
  /usr/bin/awk '/Calendar|iCal|calendar|usernoted|NotificationCenter|sandbox|Sandbox|amfid|taskgated|[Cc]ode.?[Ss]ign|killed/ {print}' > "$TEST_OUT/asl-messages.txt"
for TEST_REPORT_DIR in "$HOME/Library/Logs/DiagnosticReports" /Library/Logs/DiagnosticReports; do
  [ -d "$TEST_REPORT_DIR" ] || continue
  for TEST_REPORT in "$TEST_REPORT_DIR"/Calendar*.crash "$TEST_REPORT_DIR"/Calendar*.ips; do
    [ -f "$TEST_REPORT" ] || continue
    if [ "$TEST_REPORT" -nt "$TEST_OUT/start-marker" ]; then /bin/cp "$TEST_REPORT" "$TEST_OUT/"; fi
  done
done
/usr/bin/ditto -c -k --keepParent "$TEST_OUT" "$TEST_OUT.zip"
echo "Please return this ZIP: $TEST_OUT.zip"
echo 'It contains launch and system messages, file status/hashes, and any new Calendar crash reports.'
echo 'The test helper stays active until Stop Calendar Helper.command or logout.'
echo 'Press Return to close.'
read -r TEST_DONE
