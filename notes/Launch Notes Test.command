#!/bin/bash
set -u
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_APP="$TEST_DIR/Mountain Lion Notes.app"
TEST_VERSION="$(/usr/bin/sw_vers -productVersion)"
case "$TEST_VERSION" in
  10.9|10.9.*) ;;
  *) echo "This test is for Mavericks (10.9) only. Current version: $TEST_VERSION"; exit 1 ;;
esac
if [ ! -x "$TEST_APP/Contents/MacOS/Notes" ]; then
  echo "Keep this launcher beside Mountain Lion Notes.app in the extracted folder."
  exit 1
fi
TEST_LOG="$TEST_DIR/Notes-test-$(/bin/date +%Y%m%d-%H%M%S)-$$.log"
{
  /bin/date
  /usr/bin/sw_vers
  /usr/bin/uname -m
  /usr/bin/codesign --verify --deep --verbose=2 "$TEST_APP"
} > "$TEST_LOG" 2>&1
echo "Use a temporary user account with no Internet Accounts for this first test."
echo "Launching experimental Notes. Log: $TEST_LOG"
DYLD_PRINT_LIBRARIES=1 "$TEST_APP/Contents/MacOS/Notes" >> "$TEST_LOG" 2>&1
TEST_RESULT=$?
echo "Notes exit status: $TEST_RESULT" >> "$TEST_LOG"
echo "Notes exited ($TEST_RESULT). Please return the log with your test results."
echo "Press Return to close this window."
read -r TEST_DONE
exit "$TEST_RESULT"
