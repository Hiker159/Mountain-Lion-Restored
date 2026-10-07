"""Suppress direct ABAddressBook class receivers in the copied legacy images.

The trial has no contact integration. Returning a nil class receiver prevents
these callers from constructing native AddressBook objects, whose failed reads
previously triggered repair attempts and distributed change notifications.
This is limited to observed RIP-relative class loads in copied code; the sandbox
remains the backstop for indirect/native framework accesses. Runtime validation
is necessary: no guarantee is made for untested contact-dependent UI features.
"""
import hashlib,re,struct,subprocess

def patch(binary):
    data=bytearray(binary.read_bytes())
    source_hash=hashlib.sha256(data).hexdigest()
    if data[:4]!=b'\xcf\xfa\xed\xfe':
        raise RuntimeError('Expected thin x86_64 image')
    segments=[];off=32
    for _ in range(struct.unpack_from('<I',data,16)[0]):
        cmd,size=struct.unpack_from('<II',data,off)
        if cmd==0x19:
            vm,vmsize,fileoff,filesize=struct.unpack_from('<QQQQ',data,off+24)
            segments.append((vm,filesize,fileoff))
        off+=size
    dis=subprocess.check_output(['xcrun','llvm-objdump','--macho','--disassemble','--arch=x86_64',str(binary)],universal_newlines=True, errors="replace")
    changes=[]
    for line in dis.splitlines():
        if not re.search(r'Objc class ref: _OBJC_CLASS_\$_ABAddressBook\s*$',line):continue
        m=re.match(r'\s*([0-9a-f]+):\s*((?:[0-9a-f]{2}\s+)+)movq\s+.*\(%rip\),\s*%(\w+)',line)
        if not m:raise RuntimeError('Unrecognized AddressBook class reference: '+line)
        address=int(m[1],16);raw=bytes.fromhex(m[2]);register=m[3]
        matches=[fo+address-vm for vm,sz,fo in segments if vm<=address<vm+sz]
        if len(matches)!=1:raise RuntimeError('Unmapped class reference')
        pos=matches[0]
        # REX.W MOV r64,[RIP+disp32] -> MOV r64,0, preserving seven bytes.
        if len(raw)!=7 or raw[0] not in (0x48,0x4c) or raw[1]!=0x8b or raw[2]&0xc7!=5:
            raise RuntimeError('Unexpected instruction encoding')
        reg=(raw[2]>>3)&7
        replacement=bytes([0x49 if raw[0]==0x4c else 0x48,0xc7,0xc0|reg,0,0,0,0])
        if data[pos:pos+7]!=raw:raise RuntimeError('Disassembly byte mismatch')
        data[pos:pos+7]=replacement
        changes.append({'address':hex(address),'offset':hex(pos),'register':register,'before':raw.hex(),'after':replacement.hex()})
    if changes:binary.write_bytes(data)
    return {'original_sha256':source_hash,'class_receiver_edits':changes}
