"""Build an experimental x86_64 Calendar copy; originals and system files are untouched."""
from pathlib import Path
import hashlib
import json
import os
import plistlib
import shutil
import struct
import subprocess
import sys
from patch_calendar_isolation import patch_storage
from patch_calendar_background import patch as patch_background
from patch_calendar_local_only import patch as patch_local_only
from patch_calendar_contact_access import patch as patch_contact_access
from calendar_config import FRAMEWORKS, EXCLUDED

import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
ROOT = project_root()
OLD = ROOT / 'originals'
DEST = ROOT / 'builds' / (sys.argv[1] if len(sys.argv) > 1 else 'calendar-trial-01')
PERMISSION_MODE = sys.argv[2] if len(sys.argv) > 2 else 'public-only'
if PERMISSION_MODE not in ('original', 'public-only'):
    raise SystemExit('Permission mode must be original or public-only.')
if DEST.exists():
    raise SystemExit('Choose a new build name; existing builds are never overwritten.')
if DEST.parent != ROOT / 'builds':
    raise SystemExit('Build name must be a single directory name.')
APP = DEST / 'Mountain Lion Calendar.app'
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
run('ditto', OLD / 'Applications/Calendar.app', APP)
frameworks = APP / 'Contents/Frameworks'
frameworks.mkdir()
mapping = {}
for name in FRAMEWORKS:
    sources = [OLD / f'System/Library/{area}/{name}.framework'
               for area in ('Frameworks', 'PrivateFrameworks')]
    sources = [p for p in sources if p.exists()]
    if len(sources) != 1:
        raise RuntimeError('Ambiguous framework: ' + name)
    source = sources[0]
    versions = [p for p in (source / 'Versions').iterdir() if not p.is_symlink() and (p/name).is_file()]
    if len(versions) != 1:
        raise RuntimeError('Ambiguous framework version: ' + name)
    version = versions[0].name
    original = '/' + str((versions[0]/name).relative_to(OLD))
    run('ditto', source, frameworks / source.name)
    mapping[original] = frameworks / source.name / f'Versions/{version}/{name}'
for item in EXCLUDED:
    excluded = frameworks / item
    if excluded.is_dir():
        shutil.rmtree(excluded)
    elif excluded.is_file():
        excluded.unlink()
    else:
        raise RuntimeError('Missing expected excluded helper: ' + item)
info_path = APP / 'Contents/Info.plist'
info = plistlib.loads(info_path.read_bytes())
info['CFBundleIdentifier'] = 'org.local.iCal'
info_path.write_bytes(plistlib.dumps(info))

# Put the original agent executable in a conventional helper app for signing
# and its own Notification Center identity; it shares only our bundled libraries.
helper = APP / 'Contents/Helpers/Mountain Lion Calendar Alerts.app'
(helper/'Contents/MacOS').mkdir(parents=True)
(helper/'Contents/Resources').mkdir()
agent_source = frameworks / 'CalendarAgent.framework/Executables/CalendarAgent'
agent_source.rename(helper/'Contents/MacOS/CalendarAgent')
agent_source.parent.rmdir()
helper_info = {'CFBundleIdentifier':'org.local.CalendarAgent',
    'CFBundleExecutable':'CalendarAgent', 'CFBundleName':'Mountain Lion Calendar Alerts',
    'CFBundleDisplayName':'Mountain Lion Calendar Alerts', 'CFBundlePackageType':'APPL',
    'CFBundleVersion':'10', 'CFBundleShortVersionString':'0.10', 'LSUIElement':True,
    'CFBundleIconFile':'AlarmClock.icns',
    'LSMinimumSystemVersion':'10.9'}
(helper/'Contents/Info.plist').write_bytes(plistlib.dumps(helper_info))
# Original Mountain Lion Notification Center artwork, repackaged as an app icon.
icon_source = OLD/'System/Library/CoreServices/NotificationCenter.app/Contents/Resources/icon_alarm.tiff'
run('sips', '-s', 'format', 'icns', icon_source, '--out', helper/'Contents/Resources/AlarmClock.icns')
framework_info = frameworks/'CalendarAgent.framework/Versions/A/Resources/Info.plist'
agent_info=plistlib.loads(framework_info.read_bytes())
agent_info['CFBundleIdentifier']='org.local.CalendarAgent'
framework_info.write_bytes(plistlib.dumps(agent_info))
binaries = list(machos(APP))
permissions = {}
source_hashes = {}
storage_patches = {}
alarm_patch = None
local_only_patch = None
contact_access_patches = {}
for binary in binaries:
    relative = str(binary.relative_to(APP))
    source_hashes[relative] = hashlib.sha256(binary.read_bytes()).hexdigest()
    permissions[relative] = entitlements(binary)
    if PERMISSION_MODE == 'public-only' and permissions[relative]:
        permissions[relative] = {k: v for k, v in permissions[relative].items()
                                 if not k.startswith(('com.apple.private.', 'com.apple.developer.', 'com.apple.locationd.'))}
    arches = run('lipo', '-archs', binary).split()
    if arches != ['x86_64']:
        temp = binary.with_name(binary.name + '.x86_64-tmp')
        run('lipo', binary, '-thin', 'x86_64', '-output', temp)
        os.replace(temp, binary)
    if binary.name == 'CalendarStore' and binary.parent.name == 'A':
        alarm_patch = patch_background(binary)
        local_only_patch = patch_local_only(binary)
    contact_access_patches[relative] = patch_contact_access(binary)
    storage_patches[relative] = patch_storage(binary)
    if binary == helper/'Contents/MacOS/CalendarAgent':
        # Its original executable contains an embedded XML Info.plist as well.
        data=binary.read_bytes()
        old=b'<string>com.apple.CalendarAgent</string>'
        new=b'<string>org.local.CalendarAgent</string>'
        if data.count(old)!=1:raise RuntimeError('Unknown embedded agent identity')
        binary.write_bytes(data.replace(old,new))
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

# New source-built extension loads only into the alert helper via its launcher.
wake_library = frameworks / 'MLCalendarWakeRecovery.dylib'
run('xcrun', 'clang', '-arch', 'x86_64', '-mmacosx-version-min=10.9',
    '-dynamiclib', '-fno-objc-arc', '-fblocks', '-Wno-deprecated-declarations',
    '-framework', 'AppKit', '-framework', 'Foundation', '-framework', 'Carbon',
    '-Wl,-no_fixup_chains,-no_implicit_dylibs',
    '-Wl,-install_name,@rpath/MLCalendarWakeRecovery.dylib',
    '-o', wake_library, ROOT/'calendar_wake_recovery.m')
binaries.append(wake_library)
permissions[str(wake_library.relative_to(APP))] = None

# Sign each executable and then each enclosing code bundle from the inside out.
# Framework Resources also contain standalone helpers, so a single framework
# signature is insufficient to identify entitlement ownership correctly.
sign_targets = set()
for binary in binaries:
    for parent in binary.parents:
        if parent == APP or parent.suffix in ('.app', '.xpc', '.bundle', '.webplugin', '.framework', '.syncschema', '.sourcebundle', '.docktileplugin'):
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
    'storage_patches': storage_patches,
    'helper_icon_source_sha256': hashlib.sha256(icon_source.read_bytes()).hexdigest(),
    'wake_extension_source_sha256': hashlib.sha256((ROOT/'calendar_wake_recovery.m').read_bytes()).hexdigest(),
    'alarm_patch': alarm_patch,
    'local_only_patch': local_only_patch,
    'contact_access_patches': contact_access_patches,
    'excluded_helpers': EXCLUDED,
    'original_bundle_identifier_retained': False,
    'original_entitlements_retained': PERMISSION_MODE == 'original',
    'permission_mode': PERMISSION_MODE,
    'architecture': 'x86_64', 'signature': 'ad hoc SHA-1',
    'version_metadata': 'Unchanged from Mountain Lion',
    'validation': 'Local signature and bundled dependency-path checks passed; runtime untested.'
}, indent=2) + '\n')
print(APP)
