"""Enable CalendarStore's existing in-process alert monitor in the trial app.

The context initializer normally selects CalXPCAlertChangeMonitor outside
CalendarAgent. With the agent deliberately disconnected, alarm changes never
reach its scheduling helper. Removing only that conditional jump selects the
existing CalAlertChangeMonitor, which calls CalUserNotificationCenterHelper
locally on saves. It leaves __isCalendarAgent false and does not enable sync.

CalendarStore also explicitly supports its notification center running inside
Calendar: when the main bundle ID matches iCal it uses the caller's default
NSUserNotificationCenter, rather than registering on behalf of another app.
The isolation patch consistently renames both IDs to org.local.iCal.

This does not implement a background process, startup scan, or wake scheduler.
"""
import hashlib

SOURCE_SHA256 = '3b739cf48d096208a12dabe971d2a781763d8379e68b34fb4dfae322224891c8'
OFFSET = 0x49b8
CONTEXT = bytes.fromhex('803db8053000007410488b35c7e12c00488b3d10202d00eb0e488b35b7e12c00488b3d08202d00ff15')

def patch(binary):
    data = bytearray(binary.read_bytes())
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise RuntimeError('Unknown CalendarStore executable; refusing alarm patch.')
    if data[0x49b1:0x49da] != CONTEXT:
        raise RuntimeError('Unexpected alert-monitor selection instructions.')
    data[OFFSET:OFFSET+2] = b'\x90\x90'
    binary.write_bytes(data)
    return {'original_sha256':SOURCE_SHA256,'offset':hex(OFFSET),
            'before':'7410','after':'9090',
            'effect':'Use existing local CalAlertChangeMonitor instead of XPC monitor.',
            'limit':'Calendar must run for alarm creation/edit handling; background delivery unverified.'}
