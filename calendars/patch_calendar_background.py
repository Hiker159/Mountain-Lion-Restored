"""Version-guarded own-process notification-center registration for the agent.

Keep the original local-vs-XPC alert monitor selection: the UI sends changes to
the private test service, while the actual agent uses its local monitor. Both
processes use their own default notification center, without Apple-only proxy
registration on behalf of Calendar or Reminders.
"""
import hashlib
from patch_calendar_alarms import SOURCE_SHA256

def patch(binary):
    data=bytearray(binary.read_bytes())
    if hashlib.sha256(data).hexdigest()!=SOURCE_SHA256:
        raise RuntimeError('Unknown CalendarStore; refusing notification-center patch')
    if data[0x2fb51:0x2fb55] != bytes.fromhex('84c0746c'):
        raise RuntimeError('Notification-center branch changed')
    if data[0x49b8:0x49ba] != bytes.fromhex('7410'):
        raise RuntimeError('Expected original monitor selection')
    data[0x2fb53:0x2fb55]=b'\x90\x90'
    binary.write_bytes(data)
    return {'original_sha256':SOURCE_SHA256,'offset':'0x2fb53','before':'746c','after':'9090',
            'effect':'Use own default NSUserNotificationCenter; retain original UI-to-agent monitor routing.'}
