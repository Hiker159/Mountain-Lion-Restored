"""Static import/export comparison; does not establish runtime compatibility."""
from pathlib import Path
import json
import re
import subprocess

import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
ROOT = project_root()
OLD = ROOT / 'originals'
NEW = ROOT / 'mavericks-originals'

def run(*args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout

def dependencies(binary):
    result = {}
    for line in run('otool', '-L', str(binary)).splitlines()[1:]:
        path = line.strip().split(' (compatibility')[0]
        result[Path(path).name] = path
    return result

def imports(binary):
    result = {}
    for line in run('xcrun', 'dyld_info', '-arch', 'x86_64', '-imports', str(binary)).splitlines():
        m = re.search(r'^\s+(\S+)\s+\(from ([^)]+)\)(.*)$', line)
        if m:
            result.setdefault(m[2], []).append({'symbol': m[1], 'flags': m[3].strip()})
    return result

def exports(binary):
    output = run('xcrun', 'dyld_info', '-arch', 'x86_64', '-exports', str(binary))
    return set(re.findall(r'^\s+0x[0-9A-Fa-f]+\s+(\S+)', output, re.M)), output

report = ['# Static dependency comparison', '',
          'Direct exported symbols only. Re-exports, Objective-C method changes, framework '
          'initialization, services, signing, and data compatibility require further checks.', '']
data = {}
for name in ('Notes', 'Contacts', 'Calendar'):
    binary = OLD / f'Applications/{name}.app/Contents/MacOS/{name}'
    deps = dependencies(binary)
    grouped = imports(binary)
    report += ['## ' + name, '']
    data[name] = {}
    for lib, symbols in sorted(grouped.items()):
        path = deps.get(lib)
        if not path or '/PrivateFrameworks/' not in path:
            continue
        target = NEW / path.lstrip('/')
        if not target.is_file():
            data[name][lib] = {'path': path, 'status': 'not extracted or absent'}
            report.append(f'- {lib}: not extracted or absent.')
            continue
        available, raw = exports(target)
        missing = [s for s in symbols if s['symbol'] not in available]
        data[name][lib] = {'path': path, 'imports': len(symbols), 'missing_direct_exports': missing}
        report.append(f'- {lib}: {len(symbols)} imports; {len(missing)} absent from direct exports.')
        report.extend('  - `' + s['symbol'] + '` ' + s['flags'] for s in missing)
        (ROOT / 'reports' / f'mavericks-{lib}-exports.txt').write_text(raw)
    report.append('')
(ROOT / 'reports/dependency-comparison.json').write_text(json.dumps(data, indent=2) + '\n')
(ROOT / 'reports/dependency-comparison.md').write_text('\n'.join(report) + '\n')
print('\n'.join(report))
