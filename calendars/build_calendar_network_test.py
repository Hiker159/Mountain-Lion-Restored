from pathlib import Path
import shutil,plistlib,subprocess,json,hashlib,zipfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/calendar-network-test-01/CalendarNetwork'
S=R/'builds/restored-apps-preview-03/Calendar'
shutil.copytree(S,D,symlinks=True,dirs_exist_ok=True)
APP=D/'Mountain Lion Calendar.app';modified=set()
replacements=[(b'org.local.iCal',b'org.cloud.iCal'),(b'org.local.CalendarAgent',b'org.cloud.CalendarAgent'),(b'MLCalData',b'MLCalNetx'),(b'ML-Calendar',b'ML-CalCloud')]
assert all(len(a)==len(b) for a,b in replacements)
for p in APP.rglob('*'):
 if not p.is_file() or p.is_symlink():continue
 data=p.read_bytes()
 if data[:4] in (b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca'):
  new=data
  for a,b in replacements:new=new.replace(a,b)
  if new!=data:p.write_bytes(new);modified.add(p)
 elif p.suffix=='.plist':
  try:value=plistlib.loads(data)
  except Exception:continue
  def change(v):
   if isinstance(v,str):
    for a,b in replacements:v=v.replace(a.decode(),b.decode())
    return v
   if isinstance(v,dict):return {change(k):change(x) for k,x in v.items()}
   if isinstance(v,list):return [change(x) for x in v]
   return v
  new=change(value)
  if new!=value:
   p.write_bytes(plistlib.dumps(new));modified.add(p)
# Network-only experiment: retain external-sync and birthday guards.
profile=(D/'calendar-agent-trial.sb').read_text().replace('; This first background build is for local alarms, with no account syncing.\n(deny network-outbound)','; Native CalDAV test: outbound networking permitted; stock stores remain protected.')
(D/'calendar-agent-trial.sb').write_text(profile)
c=(D/'calendar_agent_control.py').read_text().replace('org.local.CalendarAgent','org.cloud.CalendarAgent').replace('MLCalData','MLCalNetx').replace('ML-Calendar','ML-CalCloud')
(D/'calendar_agent_control.py').write_text(c)
launcher=(D/'Open Calendar.command').read_text().replace('/usr/bin/python "$HERE/calendar_login_control.py" open','/usr/bin/python "$HERE/calendar_agent_control.py" start').replace('MLCalData','MLCalNetx').replace('ML-Calendar','ML-CalCloud').replace('Mountain Lion Restored Apps','ML Calendar Network Test')
(D/'Open Network Calendar.command').write_text(launcher);(D/'Open Network Calendar.command').chmod(0o755)
for name in ['Open Calendar.command','Enable Calendar Alerts at Login.command','Disable Calendar Alerts at Login.command','Collect Calendar Startup Log.command','Diagnose Calendar.command','calendar_login_control.py','manifest.json']:
 p=D/name
 if p.exists():p.unlink()
# Sign changed leaf images, followed by enclosing bundles from inner to outer.
def run(*args):subprocess.run([str(a) for a in args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
for p in sorted((p for p in modified if p.parent.name!='MacOS' and p.suffix!='.plist'),key=lambda p:len(p.parts),reverse=True):
 run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',p)
suffixes=('.app','.framework','.bundle','.sourcebundle','.xpc','.syncschema','.docktileplugin')
bundles={q for p in modified for q in p.parents if q==APP or (APP in q.parents and q.suffix in suffixes)}
for p in sorted(bundles,key=lambda p:len(p.parts),reverse=True):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',p)
run('codesign','--verify','--deep','--strict',APP)
print('Network experiment built and signature verified:',D)
