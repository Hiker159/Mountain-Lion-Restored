"""Audit a proposed app-local framework set against extracted Mavericks binaries."""
from pathlib import Path
from functools import lru_cache
import json
import re
import subprocess
import sys

import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
ROOT = project_root()
OLD = ROOT / 'originals'
NEW = ROOT / 'mavericks-originals'
from calendar_config import FRAMEWORKS, EXCLUDED
NAMES = sys.argv[1:] or FRAMEWORKS
def framework_path(name):
    matches = [p for area in ('Frameworks', 'PrivateFrameworks')
               for p in (OLD / f'System/Library/{area}/{name}.framework/Versions').glob(f'*/{name}')
               if p.parent.name != 'Current' and p.is_file()]
    if len(matches) != 1:
        raise RuntimeError(f'Ambiguous or absent framework: {name}: {matches}')
    return '/' + str(matches[0].relative_to(OLD))
BUNDLED = {framework_path(n) for n in NAMES}

def run(*args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout

def target(path):
    return (OLD if path in BUNDLED else NEW) / path.lstrip('/')

@lru_cache(None)
def exports(path, ancestors=()):
    if path in ancestors:
        return frozenset(), frozenset()
    p = target(path)
    if not p.is_file():
        return frozenset(), frozenset([path])
    output = run('xcrun', 'dyld_info', '-arch', 'x86_64', '-exports', str(p))
    found = set()
    for line in output.splitlines():
        m = re.match(r'^\s+(?:0x[0-9A-Fa-f]+|\[re-export\])\s+(\S+)', line)
        if m:
            found.add(m[1])
    missing_files = set()
    links = run('xcrun', 'dyld_info', '-arch', 'x86_64', '-dependents', str(p))
    for dep in re.findall(r'^\s+re-export\s+(/\S+)', links, re.M):
        symbols, absent = exports(dep, ancestors + (path,))
        found.update(symbols)
        missing_files.update(absent)
    return frozenset(found), frozenset(missing_files)

inputs = []
bundles = [OLD / 'Applications/Calendar.app'] + [(OLD / framework_path(name).lstrip('/')).parents[2] for name in NAMES]

for bundle in bundles:
    for p in bundle.rglob('*'):
        if any('/' + item in str(p) for item in EXCLUDED):
            continue
        if p.is_symlink() or not p.is_file():
            continue
        with p.open('rb') as f:
            magic = f.read(4)
        if magic in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xce\xfa\xed\xfe'):
            inputs.append(p)
data = []
for binary in inputs:
    links = run('xcrun', 'dyld_info', '-arch', 'x86_64', '-dependents', str(binary))
    deps = {}
    for line in links.splitlines():
        m = re.search(r'(/\S+)\s*$', line)
        if m:
            path = m[1]
            name = Path(path).name
            if name.endswith('.dylib'):
                name = name[:-6]
                deps[name] = path
                name = name.rsplit('.', 1)[0]
            deps[name] = path
    issues = []
    imported = run('xcrun', 'dyld_info', '-arch', 'x86_64', '-imports', str(binary))
    count = 0
    for line in imported.splitlines():
        m = re.search(r'^\s+(\S+)\s+\(from ([^)]+)\)(.*)$', line)
        if not m:
            continue
        symbol, lib, flags = m.groups()
        count += 1
        path = '/' + str(binary.relative_to(OLD)) if lib == '<this-image>' else deps.get(lib)
        if not path:
            issues.append({'symbol': symbol, 'library': lib, 'status': 'unmapped', 'flags': flags})
            continue
        available, missing_files = exports(path)
        if symbol not in available:
            issues.append({'symbol': symbol, 'library': path, 'flags': flags.strip(),
                           'missing_files': sorted(missing_files)})
    data.append({'binary': str(binary.relative_to(OLD)), 'imports': count, 'issues': issues})
report = {'bundled_frameworks': sorted(NAMES), 'excluded_helpers': EXCLUDED, 'binaries': data,
          'limitations': 'Static exported-symbol check only. No Objective-C method, data, signing, service, or runtime validation.'}
(ROOT / 'reports/calendar-audit.json').write_text(json.dumps(report, indent=2) + '\n')
for row in data:
    print(row['binary'], row['imports'], 'imports;', len(row['issues']), 'unresolved')
    for issue in row['issues']:
        print(' ', issue)
