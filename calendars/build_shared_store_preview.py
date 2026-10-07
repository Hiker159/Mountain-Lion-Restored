"""Experimental shared-store copy. Never launches apps or accesses host user stores."""
from pathlib import Path
import subprocess,json,hashlib,struct,plistlib,shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/restored-apps-shared-experimental-01';BASE=R/'builds/restored-apps-preview-03'
if D.exists():raise SystemExit('Preserving existing experimental build')
def run(*args):subprocess.run([str(a) for a in args],check=True,stdout=subprocess.DEVNULL)
D.mkdir();changes=[]
for name in ['Notes','Contacts','Calendar']:
 dst=D/name;dst.mkdir();app=dst/('Mountain Lion '+name+'.app');run('ditto',BASE/name/app.name,app)
 manifest=json.loads((BASE/name/'manifest.json').read_text())
 if name=='Notes':continue
 modified=set()
 for rel,entry in manifest['storage_patches'].items():
  p=app/rel;data=p.read_bytes();original=data
  edits=entry if isinstance(entry,list) else entry['literal_changes']
  for edit in edits:
   if 'default_directory' in edit:
    pointer,length=struct.unpack_from('<QQ',data,0x37f580+16)
    assert length==11 and data[pointer:pointer+11]==b'ML-Contacts'
    data=data[:pointer]+b'AddressBook'+data[pointer+11:];continue
   old,new=edit['old'],edit['new']
   if name=='Calendar' and old.startswith('com.apple.'):continue
   if name=='Calendar' and 'Preferences/' in old:continue
   before=b'\0'+new.encode()+b'\0';after=b'\0'+old.encode()+b'\0'
   assert data.count(before)==edit['count'],(rel,new)
   data=data.replace(before,after)
  if data!=original:p.write_bytes(data);modified.add(p);changes.append(str(p.relative_to(D)))
 # Keep the shared trial's app/service identities distinct from the working preview.
 if name=='Calendar':
  for p in app.rglob('*'):
   if not p.is_file() or p.is_symlink():continue
   data=p.read_bytes()
   if data[:4] in (b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe') and b'org.local' in data:
    p.write_bytes(data.replace(b'org.local',b'org.share'));modified.add(p)
   elif p.suffix=='.plist':
    try:obj=plistlib.loads(data)
    except Exception:continue
    if isinstance(obj,dict) and obj.get('CFBundleIdentifier','').startswith('org.local'):
     obj['CFBundleIdentifier']=obj['CFBundleIdentifier'].replace('org.local','org.share');p.write_bytes(plistlib.dumps(obj))
  # Compile a separate click extension with shared-store launch arguments.
  work=R/'work/shared-click-source';work.mkdir(parents=True,exist_ok=True)
  for filename in ['calendar_wake_recovery.m','calendar_notification_click.m']:
   text=(R/filename).read_text().replace('org.local.iCal','org.share.iCal').replace('MLCalDataDirectory','CalendarsDirectory').replace('Library/MLCalData','Library/Calendars').replace('Library/Application Support/ML-Calendar','Library/Application Support/iCal')
   (work/filename).write_text(text)
  lib=app/'Contents/Frameworks/MLCalendarWakeRecovery.dylib'
  run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-fblocks','-Werror','-Wno-deprecated-declarations','-framework','AppKit','-framework','Foundation','-framework','Carbon','-Wl,-no_fixup_chains,-no_implicit_dylibs','-Wl,-install_name,@rpath/MLCalendarWakeRecovery.dylib','-o',lib,work/'calendar_wake_recovery.m');modified.add(lib)
 # Re-sign changed executables first, then enclosing bundles inside-out.
 for p in sorted((p for p in modified if p.parent.name!='MacOS'),key=lambda p:len(p.parts),reverse=True):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',p)
 suffixes=('.app','.framework','.bundle','.sourcebundle','.xpc','.syncschema','.docktileplugin')
 bundles={q for p in modified for q in p.parents if q==app or (app in q.parents and q.suffix in suffixes)}
 for p in sorted(bundles,key=lambda p:len(p.parts),reverse=True):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',p)
 run('codesign','--verify','--deep','--strict',app)
# Session-only helper uses its own job/log identity. Never touches normal preview job.
c=(R/'calendar_agent_control.py').read_text().replace("LABEL='org.local.CalendarAgent'","LABEL='org.share.CalendarAgent'")
c=c.replace("'ML-Calendar','Agent'","'ML-Shared-Experiment','Agent'").replace("'Library','MLCalData'","'Library','Calendars'").replace("'Application Support','ML-Calendar'","'Application Support','iCal'").replace('-MLCalDataDirectory','-CalendarsDirectory')
(D/'Calendar/calendar_agent_control.py').write_text(c)
profile='''(version 1)
(allow default)
; This experiment intentionally allows stock store access.
; Legacy account traffic stays disabled; stock Mavericks retains its connection.
(deny network-outbound)
(deny mach-lookup (global-name "com.apple.CalendarAgent") (global-name "com.apple.CalendarAgent.proxy"))
(deny process-exec (subpath "/System/Library/Frameworks/CalendarStore.framework") (subpath "/System/Library/PrivateFrameworks/CalendarAgent.framework"))
'''
for name in ['calendar-trial.sb','calendar-agent-trial.sb']:(D/'Calendar'/name).write_text(profile)
header='''#!/bin/bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$(/usr/bin/sw_vers -productVersion)" in 10.9|10.9.*) ;; *) echo 'Mavericks only.'; exit 1 ;; esac
if [ "$(/usr/bin/id -u)" = 0 ]; then echo 'Run without sudo.'; exit 1; fi
LOG="$HOME/Library/Logs/ML Shared Experiment"
/bin/mkdir -p "$LOG"
'''
for name in ['Notes','Contacts','Calendar']:
 body=header+'APP="$HERE/Mountain Lion '+name+'.app"\n/usr/bin/codesign --verify --deep "$APP"\n'
 if name=='Notes':body+='''/usr/bin/nohup "$APP/Contents/MacOS/Notes" >> "$LOG/Notes.log" 2>&1 < /dev/null &
'''
 elif name=='Contacts':body+='''/usr/bin/nohup /usr/bin/env ML_CONTACTS_PLUGINS="$APP/Contents/PlugIns/ContactSources" "$APP/Contents/MacOS/Contacts" -ABAlternateDataStoreDirectory "$HOME/Library/Application Support/AddressBook" >> "$LOG/Contacts.log" 2>&1 < /dev/null &
'''
 else:body+='''/usr/bin/python "$HERE/calendar_agent_control.py" start
/usr/bin/nohup /usr/bin/sandbox-exec -f "$HERE/calendar-trial.sb" "$APP/Contents/MacOS/Calendar" -CalendarsDirectory "$HOME/Library/Calendars" -iCalApplicationSupportDirectory "$HOME/Library/Application Support/iCal" >> "$LOG/Calendar.log" 2>&1 < /dev/null &
'''
 body+="echo 'Shared-store experimental launch requested.'\n"
 p=D/name/('Open Shared '+name+'.command');p.write_text(body);p.chmod(0o755);run('bash','-n',p)
p=D/'Calendar/Stop Shared Calendar Helper.command';p.write_text(header+'/usr/bin/python "$HERE/calendar_agent_control.py" stop\n');p.chmod(0o755)
(D/'manifest.json').write_text(json.dumps({'build':'shared-experimental-01','status':'UNTESTED ON MAVERICKS; incompatible shared writes may rebuild stock stores','modified_storage_binaries':changes,'stock_paths':['~/Library/Application Support/AddressBook','~/Library/Calendars','~/Library/Application Support/iCal'],'notes':'unchanged; already stock Notes location','calendar_services':'org.share.CalendarAgent; session only','retained_limits':'native birthdays and legacy external sync disabled; no guarantee of stock account sync'},indent=2)+'\n')
print(D)
