"""Check new extension imports against extracted Mavericks exports/re-exports."""
from pathlib import Path
from functools import lru_cache
import subprocess,re,json,sys
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
ROOT=project_root()
binary=Path(sys.argv[1])
def run(*args):return subprocess.check_output(args,text=True)
@lru_cache(None)
def exports(path):
 p=ROOT/'mavericks-originals'/path.lstrip('/')
 out=run('xcrun','dyld_info','-arch','x86_64','-exports',str(p))
 result=set(re.findall(r'^\s+(?:0x[0-9a-fA-F]+|\[re-export\])\s+(\S+)',out,re.M))
 deps=run('xcrun','dyld_info','-arch','x86_64','-dependents',str(p))
 for dep in re.findall(r'^\s+re-export\s+(/\S+)',deps,re.M):result.update(exports(dep))
 return result
paths={Path(line.strip().split(' (compatibility')[0]).name:line.strip().split(' (compatibility')[0] for line in run('otool','-L',str(binary)).splitlines()[2:]}
# dyld_info uses libSystem rather than libSystem.B.dylib in its display.
paths['libSystem']='/usr/lib/libSystem.B.dylib'
imports=re.findall(r'^\s+(\S+)\s+\(from (\S+)\)',run('xcrun','dyld_info','-arch','x86_64','-imports',str(binary)),re.M)
missing=[(sym,lib) for sym,lib in imports if lib not in paths or sym not in exports(paths[lib])]
commands=run('otool','-l',str(binary))
assert 'LC_DYLD_CHAINED_FIXUPS' not in commands
assert re.search(r'LC_VERSION_MIN_MACOSX\s+cmdsize \d+\s+version 10.9\b',commands)
report={'binary':str(binary),'imports':len(imports),'missing':missing,'minimum_os':'10.9','chained_fixups':False}
print(json.dumps(report,indent=2))
if missing:raise SystemExit(1)
