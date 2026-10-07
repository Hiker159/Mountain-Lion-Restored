"""Check static native loads that could introduce duplicate bundled frameworks."""
from pathlib import Path
import subprocess,json,sys
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
ROOT=project_root()
from calendar_config import FRAMEWORKS
names=sys.argv[1:] or FRAMEWORKS
bundled={}
for name in names:
 for area in ('Frameworks','PrivateFrameworks'):
  for p in (ROOT/'originals/System/Library'/area/(name+'.framework')/'Versions').glob('*/'+name):
   if p.parent.name!='Current':bundled['/'+str(p.relative_to(ROOT/'originals'))]=p
queue=[ROOT/'originals/Applications/Calendar.app/Contents/MacOS/Calendar',*bundled.values()]
seen=set();collisions=[];absent=[];edges=[]
while queue:
 p=queue.pop()
 if p in seen:continue
 seen.add(p)
 if not p.is_file():absent.append(str(p));continue
 for line in subprocess.check_output(['otool','-L',str(p)],text=True).splitlines()[1:]:
  dep=line.strip().split(' (compatibility')[0]
  if not dep.startswith('/'):continue
  if p.name==Path(dep).name and str(p).endswith(dep):continue
  if dep in bundled:
   if 'mavericks-originals' in p.parts:collisions.append([str(p.relative_to(ROOT)),dep])
   target=bundled[dep]
  else:target=ROOT/'mavericks-originals'/dep.lstrip('/')
  edges.append([str(p.relative_to(ROOT)),str(target.relative_to(ROOT))])
  queue.append(target)
report={'bundled_frameworks':names,'visited':len(seen),'collisions':collisions,'absent':absent,'edges':edges,'limitation':'Static main executable closure only; dynamic plug-ins not covered.'}
(ROOT/'reports/calendar-transitive-loads.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='edges'},indent=2))
