"""Guarded local-only CalendarStore edits, applied after the background patch.

Mavericks ABPerson searchElementForProperty creates ABSearchElementMatch;
its initWithProperty:... resolves sharedAddressBook at 0x633bd in the supplied
Mavericks AddressBook image. The birthday reset still constructs this query
when its direct ABAddressBook receiver has been suppressed. Nil just that
ABPerson receiver; keep the reset method's cleanup and return conventions.

launchSyncWithArgs:shouldDelay: only enqueues the excluded iCalExternalSync
launch. Return before suspending/queuing work. Do not disable change tracking,
touch the enclosing XPC operation, or skip its finishOperation callback.
"""
import hashlib
from patch_calendar_alarms import SOURCE_SHA256

EDITS = (
    (0x643f5, '488b3d7c192700', '48c7c700000000',
     'Nil ABPerson receiver for the birthday search query'),
    (0x15d40d, '554889e5', 'c3909090',
     'Return from legacy external-sync launch before queue operations'),
)

def patch(binary):
    data = bytearray(binary.read_bytes())
    # The only preceding edit must be the Test 07 notification identity branch.
    original = bytearray(data)
    if original[0x2fb53:0x2fb55] != b'\x90\x90':
        raise RuntimeError('Expected background notification patch')
    original[0x2fb53:0x2fb55] = bytes.fromhex('746c')
    if hashlib.sha256(original).hexdigest() != SOURCE_SHA256:
        raise RuntimeError('Unknown CalendarStore; refusing local-only edits')
    changes = []
    for offset, before, after, effect in EDITS:
        before, after = bytes.fromhex(before), bytes.fromhex(after)
        if len(before) != len(after) or data[offset:offset+len(before)] != before:
            raise RuntimeError('Unexpected instruction at ' + hex(offset))
        data[offset:offset+len(after)] = after
        changes.append(dict(offset=hex(offset), before=before.hex(),
                            after=after.hex(), effect=effect))
    binary.write_bytes(data)
    return dict(original_sha256=SOURCE_SHA256, edits=changes)
