"""Build an experimental x86_64 Contacts copy; originals and system files are untouched."""
from pathlib import Path
import hashlib
import json
import os
import plistlib
import shutil
import struct
import subprocess
import sys
from patch_contacts_sources import patch as patch_sources
from patch_contacts_isolation import patch_layout, patch_storage

import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
ROOT = project_root()
OLD = ROOT / 'originals'
DEST = ROOT / 'builds' / (sys.argv[1] if len(sys.argv) > 1 else 'contacts-trial-01')
PERMISSION_MODE = sys.argv[2] if len(sys.argv) > 2 else 'public-only'
if PERMISSION_MODE not in ('original', 'public-only'):
    raise SystemExit('Permission mode must be original or public-only.')
if DEST.exists():
    raise SystemExit('Choose a new build name; existing builds are never overwritten.')
if DEST.parent != ROOT / 'builds':
    raise SystemExit('Build name must be a single directory name.')
APP = DEST / 'Mountain Lion Contacts.app'
LOG = []

def run(*args):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    LOG.append({'args': [str(a) for a in args], 'returncode': p.returncode,
                'stdout': p.stdout, 'stderr': p.stderr})
    (DEST / 'build-log.json').write_text(json.dumps(LOG, indent=2))
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout

def machos(root):
    for p in root.rglob('*'):
        if not p.is_file() or p.is_symlink():
            continue
        with p.open('rb') as f:
            magic = f.read(4)
        if magic in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xce\xfa\xed\xfe'):
            yield p

def entitlements(binary):
    b = binary.read_bytes()
    if b[:4] == b'\xca\xfe\xba\xbe':
        count = struct.unpack_from('>I', b, 4)[0]
        for i in range(count):
            cpu, subtype, offset, size, align = struct.unpack_from('>IIIII', b, 8 + 20*i)
            if cpu == 0x01000007:
                b = b[offset:offset+size]
                break
    if b[:4] != b'\xcf\xfa\xed\xfe':
        raise RuntimeError('Expected x86_64 Mach-O: ' + str(binary))
    count = struct.unpack_from('<I', b, 16)[0]
    off = 32
    for _ in range(count):
        cmd, size = struct.unpack_from('<II', b, off)
        if cmd == 0x1d:
            start, length = struct.unpack_from('<II', b, off+8)
            magic, total, slots = struct.unpack_from('>III', b, start)
            if magic != 0xfade0cc0:
                continue
            for i in range(slots):
                slot, rel = struct.unpack_from('>II', b, start+12+i*8)
                if slot == 5:
                    magic, length = struct.unpack_from('>II', b, start+rel)
                    return plistlib.loads(b[start+rel+8:start+rel+length])
        off += size
    return None

DEST.mkdir(parents=True)
run('ditto', OLD / 'Applications/Contacts.app', APP)
frameworks = APP / 'Contents/Frameworks'
frameworks.mkdir()
mapping = {}
for name in ('InternetAccounts', 'AddressBook', 'ServerNotification', 'AOSNotification'):
    area = 'Frameworks' if name in ('AddressBook', 'ServerNotification') else 'PrivateFrameworks'
    version = 'A'
    original = f'/System/Library/{area}/{name}.framework/Versions/{version}/{name}'
    source = OLD / f'System/Library/{area}/{name}.framework'
    run('ditto', source, frameworks / source.name)
    mapping[original] = frameworks / source.name / f'Versions/{version}/{name}'

local_source = OLD / 'System/Library/Address Book Plug-Ins/LocalSource.sourcebundle'
source_dir = APP / 'Contents/PlugIns/ContactSources'
source_dir.mkdir(parents=True, exist_ok=True)
run('ditto', local_source, source_dir / local_source.name)
source_patch = None

# Older AOSNotification stores loose resources at its framework root. Modern
# signing requires sealed resources inside the versioned Resources directory.
relocated_resources = []
aos = frameworks / 'AOSNotification.framework'
for resource in aos.iterdir():
    if resource.is_file() and not resource.is_symlink():
        destination = aos / 'Versions/A/Resources' / resource.name
        resource.rename(destination)
        relocated_resources.append(resource.name)

binaries = list(machos(APP))
permissions = {}
source_hashes = {}
storage_patches = {}
layout_patch = None
for binary in binaries:
    relative = str(binary.relative_to(APP))
    source_hashes[relative] = hashlib.sha256(binary.read_bytes()).hexdigest()
    permissions[relative] = entitlements(binary)
    if PERMISSION_MODE == 'public-only' and permissions[relative]:
        permissions[relative] = {k: v for k, v in permissions[relative].items()
                                 if not k.startswith(('com.apple.private.', 'com.apple.developer.'))}
    arches = run('lipo', '-archs', binary).split()
    if arches != ['x86_64']:
        temp = binary.with_name(binary.name + '.x86_64-tmp')
        run('lipo', binary, '-thin', 'x86_64', '-output', temp)
        os.replace(temp, binary)
    if binary == mapping['/System/Library/Frameworks/AddressBook.framework/Versions/A/AddressBook']:
        source_patch = patch_sources(binary)
    if binary == APP / 'Contents/MacOS/Contacts':
        layout_patch = patch_layout(binary)
    storage_patches[relative] = patch_storage(binary)
    output = run('otool', '-L', binary)
    args = ['install_name_tool']
    for old, new in mapping.items():
        if old in output:
            relative_path = os.path.relpath(new, binary.parent)
            args += ['-change', old, '@loader_path/' + relative_path]
    if binary in mapping.values():
        args += ['-id', '@rpath/' + str(binary.relative_to(frameworks))]
    if len(args) > 1:
        run(*args, binary)
    # Remove only after install_name_tool: stripping first leaves legacy
    # __LINKEDIT padding that modern install_name_tool cannot process.
    # This also avoids inheriting Apple's original library requirements.
    run('codesign', '--remove-signature', binary)

# Sign each executable and then each enclosing code bundle from the inside out.
# Framework Resources also contain standalone helpers, so a single framework
# signature is insufficient to identify entitlement ownership correctly.
sign_targets = set()
for binary in binaries:
    for parent in binary.parents:
        if parent == APP or parent.suffix in ('.app', '.xpc', '.bundle', '.webplugin', '.framework', '.syncschema', '.sourcebundle'):
            sign_targets.add(parent)
        if parent == APP:
            break

def sign(target, ents):
    args = ['codesign', '--force', '--sign', '-', '--timestamp=none', '--digest-algorithm=sha1',
            '--requirements', '=library => true']
    if ents:
        path = DEST / ('entitlements-' + str(len(LOG)) + '.plist')
        path.write_bytes(plistlib.dumps(ents))
        args += ['--entitlements', path]
    run(*args, target)

bundle_executables = {}
for target in sign_targets:
    if target.suffix == '.framework':
        binary = (target / target.stem).resolve()
    else:
        info = plistlib.loads((target / 'Contents/Info.plist').read_bytes())
        binary = target / 'Contents/MacOS' / info['CFBundleExecutable']
    if binary not in binaries:
        raise RuntimeError('Unrecognized bundle executable: ' + str(binary))
    bundle_executables[target] = binary
for binary in binaries:
    if binary not in bundle_executables.values():
        sign(binary, permissions[str(binary.relative_to(APP))])
for target in sorted(sign_targets, key=lambda p: (len(p.parts), str(p)), reverse=True):
    binary = bundle_executables[target]
    sign(target, permissions[str(binary.relative_to(APP))])

run('codesign', '--verify', '--deep', '--verbose=2', APP)
for binary in binaries:
    output = run('otool', '-L', binary)
    for old in mapping:
        if old in output:
            raise RuntimeError('Unpatched dependency in ' + str(binary))
    for line in output.splitlines()[1:]:
        dep = line.strip().split(' (compatibility')[0]
        if dep.startswith('@loader_path/'):
            resolved = (binary.parent / dep[len('@loader_path/'):]).resolve()
            if not resolved.is_file() or APP.resolve() not in resolved.parents:
                raise RuntimeError('Invalid bundled dependency: ' + dep)

(DEST / 'manifest.json').write_text(json.dumps({
    'status': 'Experimental; not run on Mavericks',
    'source_binary_sha256': source_hashes,
    'frameworks': list(mapping),
    'local_source_lookup_patch': source_patch,
    'layout_patch': layout_patch,
    'storage_patches': storage_patches,
    'aos_resources_relocated_into_versioned_resources': relocated_resources,
    'original_bundle_identifier_retained': True,
    'original_entitlements_retained': PERMISSION_MODE == 'original',
    'permission_mode': PERMISSION_MODE,
    'architecture': 'x86_64', 'signature': 'ad hoc SHA-1',
    'version_metadata': 'Unchanged from Mountain Lion',
    'validation': 'Local signature and bundled dependency-path checks passed; runtime untested.'
}, indent=2) + '\n')
print(APP)
