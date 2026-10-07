"""Package tested restored apps without running legacy apps or changing account data."""
from pathlib import Path
import subprocess,shutil,os,json,hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/restored-apps-icloud-bundle-01'
A=R/'deliverables/Mountain-Lion-Restored-Apps-iCloud-Bundle-01.zip'
V=R/'work/icloud-bundle01-verification'
S={'Notes':R/'builds/notes-icloud-menu-14/NotesAccounts','Contacts':R/'builds/contacts-icloud-photo-16/ContactsAccounts','Calendar':R/'builds/calendar-provider-options-04/CalendarAccounts','Birthdays':R/'builds/restored-apps-preview-06/Birthdays'}
if any(p.exists() for p in (D,A,V)):raise RuntimeError('Existing artifacts preserved')
def run(*args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout

def inventory(root):
 return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':p.stat().st_mode&0o777}) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
D.mkdir()
for name,source in S.items():
 shutil.copytree(source,D/name,symlinks=True)
 assert inventory(source)==inventory(D/name)
(D/'READ ME FIRST.txt').write_text('''MOUNTAIN LION RESTORED APPS - ICLOUD BUNDLE 01
For OS X Mavericks. Includes the user-tested iCloud builds, with their Google
support, launchers, account isolation, alerts and diagnostics retained.

INCLUDED
Notes: iCloud Menu Test14. iCloud folders and notes download; creation, editing
and deletion sync both ways. Sign-in survives reopening. Incoming deletions
have sometimes appeared only after reopening; startup refresh is sufficient
for the user's chosen workflow. No Notes login/background helper is included.
Contacts: iCloud Photo Test16. iCloud contacts and photos sync both ways and
photos persist after reopening. Includes the export crash fix and the optional
background/login sync helper. Google CardDAV support is retained.
Calendar: iCloud Background Test04. Native Google and manual iCloud CalDAV,
60-second helper account refresh, alerts while the app is closed, notification
click handling and wake/login recovery. iCloud alerts after logout/login were
user-confirmed. Use Message for portable account alerts; reliable local sound
for cloud Message alerts is not confirmed.
Birthdays: existing Preview06 export-based bridge, unchanged. Re-export Contacts
vCards and refresh after birthday changes; it does not read live cloud contacts.

MOVING FROM YOUR EXISTING TEST PACKAGES
1. In your OLD Contacts folder, run Disable Contacts Sync at Login.command if
   enabled. In your OLD Calendar folder, run Disable Calendar Alerts at Login.command
   if enabled, then Stop Calendar Helper.command. Quit all restored app copies.
2. Extract this bundle to a permanent location. Keep all folders together.
3. Open each app with its launcher:
   Notes/Open Private Notes.command
   Contacts/Open Contacts.command
   Calendar/Open Calendar.command
   Use these launchers each time so private storage/framework routing applies.
4. Your existing private account settings and data are retained. Do not reset data
   or add duplicate accounts. Relocation may cause Keychain access prompts again.
5. If desired, enable Contacts sync and Calendar alerts at login using the Enable
   commands in this NEW bundle. Keep it in that location while helpers are enabled.

ACCOUNT SETUP FOR A NEW INSTALLATION
Use an app-specific password for iCloud. Calendar uses manual CalDAV with the
account-specific server settings established by the prior connection test;
Contacts uses manual CardDAV. Notes offers Add iCloud Notes Account in its menu.
The full system iCloud setup provider is not required. This package supports
legacy iCloud Notes accessible to Mavericks, not upgraded modern Notes features.
Google Notes use Gmail's Notes folder, not Google Keep.

DIAGNOSTICS
Each app folder retains its Collect command. No personal account data, notes,
contacts, passwords or user diagnostic archives are included in this bundle.
The stock applications and system databases are not replaced. The restored apps
continue using their established private data and account locations.

VALIDATION
Components are copied byte-for-byte from the tested builds. App signatures,
command syntax and archive hashes, symlinks and permissions are checked before
and after packaging. Legacy apps are not executed on the build host. The new
combined folder location still needs a quick Mavericks launch/helper check.
''')
for p in D.rglob('*.command'):run('bash','-n',p)
for p in D.rglob('*.py'):compile(p.read_bytes(),str(p),'exec')
apps=[D/n/('Mountain Lion '+n+'.app') for n in ('Notes','Contacts','Calendar')]+[D/'Birthdays/Birthday Bridge.app']
for app in apps:run('codesign','--verify','--deep','--strict',app)
(D/'package-manifest.json').write_text(json.dumps({'package':'iCloud Bundle01','components':{'Notes':'iCloud Menu Test14','Contacts':'iCloud Photo Test16','Calendar':'iCloud Background Test04','Birthdays':'Preview06 unchanged'},'runtime':'Components user-tested on Mavericks; combined relocation check pending','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A)
run('ditto','-x','-k',A,V)
assert inventory(D)==inventory(V/D.name)
for app in apps:run('codesign','--verify','--deep','--strict',V/D.name/app.relative_to(D))
report={'archive':str(A),'sha256':hashlib.sha256(A.read_bytes()).hexdigest(),'size_bytes':A.stat().st_size,'component_inventories':'all four match source builds','archive_roundtrip':'hashes, symlinks and permissions identical','signatures':'all four apps verified before and after extraction','legacy_execution_on_host':False,'runtime':'Mavericks combined relocation check pending'}
(R/'reports/icloud-bundle01-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
