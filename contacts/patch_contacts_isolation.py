"""Guarded Contacts 1170 layout patch and same-length local-store substitutions."""
import hashlib
import re
import struct

APP_SHA256 = '8b1e26ae47c36c8f080795e4b27152eb36ab72526afcf3f87493e33690d9e905'

def patch_layout(binary):
    data = bytearray(binary.read_bytes())
    if hashlib.sha256(data).hexdigest() != APP_SHA256:
        raise RuntimeError('Unknown Contacts executable; refusing layout patch.')
    # Redirect only the four transitions crossing the single-card boundary.
    # Both ends have identical Objective-C calling conventions. The two
    # multi-pane animation implementations and Option-key behavior stay intact.
    redirects = [(0x64601, 0x6468b), (0x66511, 0x6659b),
                 (0x67018, 0x670c0), (0x67055, 0x670fd)]
    changes = []
    for start, target in redirects:
        assert data[start:start+4] == bytes.fromhex('554889e5')
        assert data[target:target+4] == bytes.fromhex('554889e5')
        before = data[start:start+5].hex()
        data[start:start+5] = b'\xe9' + struct.pack('<i', target - start - 5)
        changes.append({'from': hex(start), 'to': hex(target), 'before': before,
                        'after': data[start:start+5].hex()})
    assert data[0x70fcf:0x70fd1] == bytes.fromhex('7420')
    binary.write_bytes(data)
    return {'original_sha256': APP_SHA256, 'redirects': changes,
            'effect': 'Instant transitions to/from single-card; multi-pane animations retained.'}

def patch_storage(binary):
    data = bytearray(binary.read_bytes())
    changes = []
    # Restrict replacements to literal strings, never symbol table names.
    replacements = {
        b'ABDatabaseDirectory': b'MLDatabaseDirectory',
        b'ABAlternateDataStoreDirectory': b'MLAlternateDataStoreDirectory',
        b'Library/Application Support/AddressBook/Sources': b'Library/Application Support/ML-Contacts/Sources',
        b'~/Library/Application Support/AddressBook/': b'~/Library/Application Support/ML-Contacts/',
        b'~/Library/Preferences/AddressBookMe.plist': b'~/Library/Preferences/ML-ContactsMe.plist',
    }
    for old in set(re.findall(rb'(?<=\x00)ABDistributed[A-Za-z]+(?=\x00)', data)):
        replacements[old] = b'ML' + old[2:]
    for old, new in replacements.items():
        assert len(old) == len(new)
        pattern = b'\0' + old + b'\0'
        count = data.count(pattern)
        if count:
            data = data.replace(pattern, b'\0' + new + b'\0')
            changes.append({'old': old.decode(), 'new': new.decode(), 'count': count})
    if binary.name == 'AddressBook' and binary.parent.name == 'A':
        # Only the directory-name CFString is redirected. Its payload is a
        # standalone C string, not a suffix of an install-name or another path.
        record = 0x37f580
        pointer, length = struct.unpack_from('<QQ', data, record+16)
        assert length == 11 and data[pointer-1:pointer+12] == b'\0AddressBook\0'
        data[pointer:pointer+11] = b'ML-Contacts'
        changes.append({'default_directory': '~/Library/Application Support/ML-Contacts'})
    binary.write_bytes(data)
    return changes
