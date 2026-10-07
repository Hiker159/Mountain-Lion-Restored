#!/bin/bash
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
/usr/bin/python "$TEST_DIR/calendar_agent_control.py" stop
echo 'Press Return to close.'
read -r TEST_DONE
