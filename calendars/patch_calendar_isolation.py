"""Same-length literal edits for the local-only Calendar trial.

CalendarStore's directory initializer honors CalendarsDirectory and falls back to
%@/Library/Calendars or the Calendars path component. Rename all three. Literal
matches never rewrite symbol names; equal lengths preserve CFString metadata.
The launcher supplies the renamed key and a separate application-support path.
"""
import hashlib
import re

def patch_storage(binary):
    data = binary.read_bytes()
    original_hash = hashlib.sha256(data).hexdigest()
    replacements = {
        b'CalendarsDirectory': b'MLCalDataDirectory',
        b'CalCalendarsDirectoryKey': b'CalMLCalDataDirectoryKey',
    }
    # Restrict this scan to complete, printable, NUL-delimited string literals.
    for match in re.finditer(rb'(?<=\x00)[\x20-\x7e]{3,}(?=\x00)', data):
        old = match.group()
        new = old
        if b'/Library/Calendars' in new:
            new = new.replace(b'/Library/Calendars', b'/Library/MLCalData')
        # Keep resource-bundle lookup identifiers aligned with their Info.plists.
        bundle_ids = (b'com.apple.CalendarStore', b'com.apple.CalendarAgentLink',
                      b'com.apple.iCal.CalendarDraw', b'com.apple.iCal.DockTilePlugIn')
        if new not in bundle_ids and new.startswith((b'com.apple.CalendarStore.', b'com.apple.CalendarAgent', b'com.apple.iCal')):
            new = b'org.local' + new[9:]
        if new == b'~/Library/Preferences/com.apple.iCal.sources.plist':
            new = b'~/Library/Preferences/org.local.iCal.sources.plist'
        if binary.name == 'CalendarStore' and new == b'Calendars':
            new = b'MLCalData'
        if new != old:
            replacements[old] = new
    changes=[]
    for old,new in replacements.items():
        if len(old) != len(new):
            raise RuntimeError('Unequal literal lengths')
        pattern=b'\0'+old+b'\0'
        count=data.count(pattern)
        if count:
            data=data.replace(pattern,b'\0'+new+b'\0')
            changes.append({'old':old.decode(),'new':new.decode(),'count':count})
    if binary.name == 'CalendarStore':
        for expected in [b'MLCalDataDirectory', b'%@/Library/MLCalData', b'MLCalData']:
            if b'\0'+expected+b'\0' not in data:
                raise RuntimeError('CalendarStore directory patch incomplete')
    binary.write_bytes(data)
    return {'original_sha256':original_hash,'literal_changes':changes}
