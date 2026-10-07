"""Consolidate tested Contacts background sync with stable Calendar and Notes."""
from pathlib import Path
import hashlib,json,subprocess,shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/restored-apps-preview-05';A=R/'deliverables/Mountain-Lion-Restored-Apps-Preview-05.zip';V=R/'work/preview-05-verification';S=R/'builds/restored-apps-preview-04'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*a):return subprocess.check_output([str(x) for x in a],text=True,stderr=subprocess.STDOUT)
def inventory(root):
 out={}
 for p in root.rglob('*'):
  if p.is_symlink():out[str(p.relative_to(root))]={'link':str(p.readlink())}
  elif p.is_file():out[str(p.relative_to(root))]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}
 return out
D.mkdir()
for name in ('Notes','Calendar','Birthdays'):shutil.copytree(S/name,D/name,symlinks=True)
T=R/'builds/contacts-background-01/ContactsAccounts';shutil.copytree(T,D/'Contacts',symlinks=True)
p=D/'Birthdays/birthday_bridge.py';p.write_text(p.read_text().replace("SOURCES={'restored':('com.apple.AddressBook'", "SOURCES={'restored':('org.ctest.AddressBook'"))
p=D/'Birthdays/READ ME FIRST.txt';p.write_text(p.read_text()+'\nPreview 05 contains the Google-enabled restored Contacts. Its exported vCards\nuse the same birthday import workflow. Background Contacts sync does not\nautomatically refresh the exported birthday snapshot.\n')
p=D/'Birthdays/bridge-manifest.json';m=json.loads(p.read_text());m['integration']='Preview 05 Google Contacts identity; export workflow unchanged';m['files_sha256']={str(x.relative_to(p.parent)):hashlib.sha256(x.read_bytes()).hexdigest() for x in p.parent.rglob('*') if x.is_file() and not x.is_symlink() and x!=p};p.write_text(json.dumps(m,indent=2)+'\n')
(D/'READ ME FIRST.txt').write_text('''RESTORED APPS — PREVIEW 05 (MAVERICKS)

Contains stable Calendar from Preview 04, Google-enabled Contacts Test 02 with
the user-tested background helper, unchanged Notes, and the export birthday
bridge. Experimental Google sound preservation is NOT included. Use Message
alerts for Google events to also receive reminders on Android. Local Calendar
sound alerts remain available. Google/iCloud Notes investigation is next.

MOVING TO THIS PACKAGE
1. Before moving/replacing folders, use the previous Contacts test package's
   Disable Contacts Sync at Login.command. Quit restored Contacts.
2. Disable Calendar alerts at login in the old suite and stop its helper; quit
   restored Calendar. This prevents jobs retaining the old package paths.
3. Extract Preview 05 to a permanent folder. Run Calendar/Open Calendar.command
   and Contacts/Open Contacts.command. Enable each app's login helper from its
   own folder if desired. Keep this package at that path while jobs are enabled.
4. Your existing native Google test accounts/data remain in the same folders.
   A moved signed app/helper may ask for Keychain permission again.

CONTACTS
Contacts uses org.ctest.AddressBook, ~/Library/Application Support/ML-GContact,
and ~/Library/ML Contacts Accts/V1. Old local restored Contacts data in
ML-Contacts is retained separately; it is not automatically imported.
Google CardDAV creation/editing/deletion, remote updates, group syncing to
another Mac, app reopen and background syncing before/after logout were
reported successful. Native account-service/source warnings remain in logs;
they did not block the reported tests. Background sync is approximately every
2 minutes; it is enabled with Enable Contacts Sync at Login.command and removed
with Disable Contacts Sync at Login.command. Collect Contacts Account Log
captures app/helper diagnostics without databases or Keychains.

CALENDAR/NOTES/BIRTHDAYS
Calendar is byte-identical to Preview 04 (native Google backend and working
alerts/clicks/login tools). Notes is unchanged. Calendar remains in MLCalAuth
and ML-CalAuthx. Use Message for Google reminders requiring phone alerts.
The birthday bridge continues to import a Contacts vCard export. A contact
change alone does not refresh the saved export. Re-export then refresh as before.
No stock apps, account stores or contact/calendar databases are replaced.

PACKAGE CHECK
After switching, confirm Google contacts/events load, a remote contact update
arrives with Contacts closed, and a Calendar alert fires with Calendar closed.
If using birthdays, export one disposable birthday contact and refresh it.
Send diagnostics only if a check fails. Component tests passed; integration
into this combined package still needs that final path-change validation.
''')
for name in ('Notes','Calendar'):assert inventory(D/name)==inventory(S/name)
assert inventory(D/'Contacts')==inventory(T)
for p in D.rglob('*.command'):run('bash','-n',p)
for p in D.rglob('*.py'):compile(p.read_bytes(),str(p),'exec')
apps=[D/n/('Mountain Lion '+n+'.app') for n in ('Notes','Contacts','Calendar')]+[D/'Birthdays/Birthday Bridge.app']
for app in apps:run('codesign','--verify','--deep','--strict',app)
(D/'package-manifest.json').write_text(json.dumps({'package':'Preview 05','components':['unchanged Notes','Contacts Accounts 02 + Background 01','unchanged Calendar Preview 04','Birthday Bridge 06 with Contacts identity update'],'runtime':'components user-tested; combined path validation pending','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name)
for app in apps:run('codesign','--verify','--deep','--strict',V/D.name/app.relative_to(D))
(R/'reports/preview-05-validation.json').write_text(json.dumps({'archive':str(A),'sha256':hashlib.sha256(A.read_bytes()).hexdigest(),'roundtrip':'all file hashes/symlink targets/executable modes match','signatures':'all four apps passed after extraction','unchanged_components':'Notes/Calendar match Preview 04; Contacts matches background test 01','runtime':'combined path check pending'},indent=2)+'\n');print(A)
