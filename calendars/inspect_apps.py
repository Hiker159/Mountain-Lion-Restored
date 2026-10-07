"""Read extracted app metadata and dependencies; never launch or alter the apps."""
from pathlib import Path
import plistlib
import subprocess

import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
ROOT = project_root()
lines = ['# Mountain Lion app inventory', '']
version = ROOT / 'originals/System/Library/CoreServices/SystemVersion.plist'
if version.exists():
    lines += ['System version: ' + repr(plistlib.loads(version.read_bytes())), '']
for name in ('Notes', 'Contacts', 'Calendar'):
    app = ROOT / 'originals/Applications' / (name + '.app')
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    lines += ['## ' + name, '']
    for key in ('CFBundleIdentifier', 'CFBundleShortVersionString', 'CFBundleVersion',
                'LSMinimumSystemVersion', 'LSMaximumSystemVersion'):
        if key in info:
            lines.append(f'- {key}: {info[key]}')
    binary = app / 'Contents/MacOS' / info['CFBundleExecutable']
    for args in (['file', str(binary)], ['otool', '-L', str(binary)],
                 ['codesign', '-d', '--entitlements', ':-', str(app)]):
        result = subprocess.run(args, capture_output=True, text=True)
        lines += ['', '```text', result.stdout.strip(), result.stderr.strip(), '```']
    textures = [str(p.relative_to(app)) for p in app.rglob('*')
                if p.is_file() and any(s in p.name.lower() for s in
                                      ('leather', 'linen', 'paper', 'stitch'))]
    lines += ['', 'Texture-related filenames:', ''] + ['- ' + p for p in textures]
    lines += ['']
(ROOT / 'reports/app-inventory.md').write_text('\n'.join(lines) + '\n')
print(ROOT / 'reports/app-inventory.md')
