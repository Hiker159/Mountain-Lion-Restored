"""Version-guarded local-source search patch for AddressBook 1170, x86_64.

sourceBundlePaths first reads an environment path, then adds system-domain
Library/Address Book Plug-Ins directories. Change the environment key and skip
the latter block, keeping the existing .sourcebundle enumeration logic.
Offsets and instructions were verified against the saved original disassembly.
"""
import hashlib
import struct

EXPECTED_SHA256 = '7da3a14a938f8f6b293a08086eedf6e36f88acfab8fc6a7b6f4106228d6a6ecf'

def patch(binary):
    data = bytearray(binary.read_bytes())
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError('Unrecognized original AddressBook binary; refusing patch.')
    if data[:4] != b'\xcf\xfa\xed\xfe':
        raise RuntimeError('Expected thin x86_64 Mach-O.')
    def file_offset(address):
        off = 32
        for _ in range(struct.unpack_from('<I', data, 16)[0]):
            cmd, size = struct.unpack_from('<II', data, off)
            if cmd == 0x19:
                vmaddr, vmsize, fileoff, filesize = struct.unpack_from('<QQQQ', data, off+24)
                if vmaddr <= address < vmaddr + filesize:
                    return fileoff + address - vmaddr
            off += size
        raise RuntimeError('Address outside file-backed segment.')
    start = file_offset(0xb36f)
    target = file_offset(0xb49f)
    assert data[start:start+15] == bytes.fromhex('bf05000000be08000000ba01000000')
    assert data[target:target+7] == bytes.fromhex('488b35ea233500')
    # Replace the first instruction with a near jump over the system search.
    data[start:start+5] = b'\xe9' + struct.pack('<i', 0xb49f - (0xb36f+5))
    old = b'DYLD_FRAMEWORK_PATH\0'
    new = b'ML_CONTACTS_PLUGINS\0'
    assert len(new) <= len(old) and data.count(old) == 1
    data = data.replace(old, new.ljust(len(old), b'\0'))
    binary.write_bytes(data)
    return {'original_sha256': EXPECTED_SHA256,
            'method': '-[ABDataSourcePluginIndex sourceBundlePaths]',
            'jump_from': '0xb36f', 'jump_to': '0xb49f',
            'environment_key': 'ML_CONTACTS_PLUGINS',
            'effect': 'Only enumerate .sourcebundle files in the explicit test-app path.'}
