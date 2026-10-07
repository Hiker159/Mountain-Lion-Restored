"""Integrate user-tested native Google Calendar with existing restored suite."""
from pathlib import Path
import hashlib,json,subprocess,shutil,os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/restored-apps-preview-04';A=R/'deliverables/Mountain-Lion-Restored-Apps-Preview-04.zip';V=R/'work/preview-04-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved.')
def run(*args):return subprocess.check_output([str(a) for a in args],text=True)
def inventory(root):
 result={}
 for p in sorted(root.rglob('*')):
  key=str(p.relative_to(root))
  if p.is_symlink():result[key]={'link':str(p.readlink())}
  elif p.is_file():result[key]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}
 return result
S=R/'builds/restored-apps-preview-03'
D.mkdir()
for name in ('Notes','Contacts','Birthdays'):run('ditto',S/name,D/name)
run('ditto',R/'builds/calendar-private-accounts-10/CalendarAccounts',D/'Calendar')
C=D/'Calendar'
for name in ('Enable Calendar Alerts at Login.command','Disable Calendar Alerts at Login.command','Collect Calendar Startup Log.command','Diagnose Calendar.command'):
 shutil.copy2(S/'Calendar'/name,C/name)
# Controller derives its identity/data paths from the working Google controller.
shutil.copy2(S/'Calendar/calendar_login_control.py',C/'calendar_login_control.py')
# Retain the tested Google app launcher but add the managed login workflow.
s=(C/'Open Private Accounts Calendar.command').read_text().replace('"$HERE/calendar_agent_control.py" start','"$HERE/calendar_login_control.py" open')
(C/'Open Calendar.command').write_text(s);os.chmod(C/'Open Calendar.command',0o755)
(C/'Open Private Accounts Calendar.command').unlink()
# Inherited utility scripts must follow the current identity and datastore.
for p in C.glob('*.command'):
 if p.name=='Open Calendar.command':continue
 s=p.read_text()
 for old,new in [('org.local.CalendarAgent','org.authx.CalendarAgent'),('org.cloud.CalendarAgent','org.authx.CalendarAgent'),('org.local.iCal','org.authx.iCal'),('ML-Calendar','ML-CalAuthx'),('ML-CalCloud','ML-CalAuthx'),('MLCalData','MLCalAuth'),('MLCalNetx','MLCalAuth'),('Mountain Lion Restored Apps','ML Calendar Private Accounts')]:s=s.replace(old,new)
 p.write_text(s)
# Birthday scripting targets this app; preserve source IDs/markers and export semantics.
p=D/'Birthdays/birthday_bridge.py';s=p.read_text().replace("require_running('org.local.iCal',calendar)","require_running('org.authx.iCal',calendar)").replace('Support/ML-Calendar/BirthdayBridge','Support/ML-CalAuthx/BirthdayBridge');p.write_text(s)
p=D/'Birthdays/READ ME FIRST.txt';p.write_text(p.read_text()+'\nPreview 04 targets the integrated Google Calendar data store. Import your\nContacts vCard again to populate birthdays in this store. Old data is retained.\n')
# Accurate release documentation replaces experimental instructions.
readme='''MOUNTAIN LION RESTORED APPS — PREVIEW 04 (MAVERICKS)

Calendar now uses the user-tested private native Google account backend.
Notes and Contacts are unchanged. iCloud is not part of this validation.

SETUP
Stop the previous Calendar helper and Google mirror/background-sync helper,
then quit previous restored Calendar copies. If the old package has Calendar
alerts enabled at login, use its Disable Calendar Alerts at Login.command.
Keep the extracted new package in one permanent folder. Run Calendar/Open
Calendar.command. Do not launch the app directly during this validation.

This package retains the Google Test 10 app identity and stores:
~/Library/MLCalAuth
~/Library/Application Support/ML-CalAuthx
~/Library/ML Cloud Accounts/V1
Your Google test account/events should remain available. Credential access
may prompt after the app moves; enter passwords only into Calendar/macOS.
Private credentials remain namespaced in the login Keychain.
The stock Mavericks calendar/contact/account stores remain protected.

Older local calendars in ~/Library/MLCalData are not automatically migrated.
They remain intact. Export/import selected local calendars if needed; do not
copy database files. Birthday Bridge is retargeted to this Calendar; refresh
from your Contacts vCard export to populate birthdays in the new store.

Enable Calendar Alerts at Login.command is optional. It starts this helper
at login, allowing background syncing/alerts. Keep the package at its installed
path. Disable Calendar Alerts at Login.command reverses this setting.

VALIDATION ON MAVERICKS
1. Launch Calendar: Google events load; sidebar right-click menus work.
2. Set a disposable Google event a few minutes ahead with an alert; quit only
   Calendar and confirm the alert appears. Click it and check the restored app
   opens the event. Check a snoozed alert as well.
3. Refresh Birthdays from a small Contacts vCard export; check dates appear.
4. Enable alerts at login; log out/in or restart, then confirm background
   alerts and Google refresh. Disable this setting when you do not want it.
5. Collect Account Setup Log.command for account failures, and Collect Calendar
   Startup Log.command for login/alert issues. Send results after these checks.

Native Google download/upload, event moves/deletion, two-way alert edits and
sidebar menus were user-tested in Test 10. Integration into this combined
package and its login/birthday tools still needs the checks above. Older
account-service warnings remain in logs; they did not block the reported tests.
'''
(D/'READ ME FIRST.txt').write_text(readme)
(C/'READ ME FIRST.txt').write_text(readme)
for name in ('Notes','Contacts'):assert inventory(D/name)==inventory(S/name)
# Calendar app stays byte-identical to the tested build.
assert inventory(C/'Mountain Lion Calendar.app')==inventory(R/'builds/calendar-private-accounts-10/CalendarAccounts/Mountain Lion Calendar.app')
for p in D.rglob('*.command'):run('bash','-n',p)
for p in D.rglob('*.py'):compile(p.read_bytes(),str(p),'exec')
apps=[D/n/('Mountain Lion '+n+'.app') for n in ('Notes','Contacts','Calendar')]+[D/'Birthdays/Birthday Bridge.app']
for p in apps:run('codesign','--verify','--deep','--strict',p)
# Update metadata after adjusting scripts; omit the manifest's own hash.
for folder,filename in [(C,'manifest.json'),(D/'Birthdays','bridge-manifest.json')]:
 p=folder/filename;m=json.loads(p.read_text());m['integration']='Preview 04 native Google Calendar; integration runtime pending';m['files_sha256']={str(x.relative_to(folder)):hashlib.sha256(x.read_bytes()).hexdigest() for x in folder.rglob('*') if x.is_file() and not x.is_symlink() and x!=p};p.write_text(json.dumps(m,indent=2)+'\n')
manifest={'package':'Preview 04','components':['unchanged Notes/Contacts from Preview 03','Calendar Private Accounts Test 10 with integrated login tools','Birthday Bridge 06 retargeted to native Google Calendar'],'runtime':'component tests confirmed; integration pending','files':inventory(D)}
(D/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V)
assert inventory(D)==inventory(V/D.name)
for app in apps:run('codesign','--verify','--deep','--strict',V/D.name/app.relative_to(D))
(R/'reports/preview-04-validation.json').write_text(json.dumps({'archive':str(A),'sha256':hashlib.sha256(A.read_bytes()).hexdigest(),'archive_roundtrip':'hashes/symlinks/executable flags match','signatures':'all four apps pass after extraction','calendar_app':'byte-identical to user-tested Test 10','notes_contacts':'unchanged','integration_runtime':'pending'},indent=2)+'\n')
print(A)
