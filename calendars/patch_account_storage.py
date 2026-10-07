"""Same-length literal redirects for a private backend; not credential isolation."""
import hashlib
import re
import struct

def patch_internet_accounts(binary):
    data=bytearray(binary.read_bytes());before=hashlib.sha256(data).hexdigest()
    assert data[:4]==b'\xcf\xfa\xed\xfe', 'Expected thin x86_64 Mach-O'
    offset=32; cstrings=None
    for _ in range(struct.unpack_from('<I',data,16)[0]):
        cmd,size=struct.unpack_from('<II',data,offset)
        if cmd==0x19:
            for i in range(struct.unpack_from('<I',data,offset+64)[0]):
                section=offset+72+i*80
                if data[section:section+16].rstrip(b'\0')==b'__cstring':
                    length=struct.unpack_from('<Q',data,section+40)[0]
                    start=struct.unpack_from('<I',data,section+48)[0]
                    cstrings=(start,start+length)
        offset+=size
    assert cstrings, 'Missing literal section'
    start,end=cstrings; literals=bytes(data[start:end])
    replacements={
        b'Library/Internet Accounts/V1':b'Library/ML Cloud Accounts/V1',
        b'~/Library/Internet Accounts/V1/%@':b'~/Library/ML Cloud Accounts/V1/%@',
    }
    # Preferences and distributed notifications must share the private namespace.
    for value in set(re.findall(rb'(?:^|(?<=\0))com\.apple\.InternetAccounts(?:\.[A-Za-z]+)?(?=\0)',literals)):
        replacements[value]=b'org.local'+value[len(b'com.apple'):]
    changes=[]
    for old,new in replacements.items():
        assert len(old)==len(new)
        positions=[m.start() for m in re.finditer(rb'(?:^|(?<=\0))'+re.escape(old)+rb'(?=\0)',literals)]
        count=len(positions)
        if count:
            for pos in positions:data[start+pos:start+pos+len(old)]=new
            changes.append({'old':old.decode(),'new':new.decode(),'count':count})
    assert any(c['old']=='Library/Internet Accounts/V1' for c in changes)
    assert any(c['old']=='com.apple.InternetAccounts' for c in changes)
    assert len(data)==binary.stat().st_size
    binary.write_bytes(data)
    return {'before_sha256':before,'changes':changes,'credentials':'Unchanged; no account creation or password API permitted in this stage'}
