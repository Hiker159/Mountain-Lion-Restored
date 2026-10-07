"""Consolidate Google-enabled Notes with the tested Preview05 components."""
from pathlib import Path
import subprocess,shutil,os,json,hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/restored-apps-preview-06';A=R/'deliverables/Mountain-Lion-Restored-Apps-Preview-06.zip';V=R/'work/preview-06-verification';S=R/'builds/restored-apps-preview-05';N=R/'builds/notes-private-accounts-04/NotesAccounts'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*a):return subprocess.check_output([str(x) for x in a],text=True,stderr=subprocess.STDOUT)
def inventory(root):return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_symlink() or p.is_file()}
D.mkdir()
for name in ['Contacts','Calendar','Birthdays']:shutil.copytree(S/name,D/name,symlinks=True)
shutil.copytree(N,D/'Notes',symlinks=True)
(D/'READ ME FIRST.txt').write_text('''RESTORED APPS — PREVIEW 06 (MAVERICKS)

Notes now has native Google account setup and IMAP syncing through its own
Accounts menu. The user confirmed note download and edits syncing back to
stock Notes. Calendar, Contacts, and Birthday Bridge are unchanged from the
working Preview 05. Experimental Calendar Google sound patches are excluded.

NOTES
Quit other restored Notes copies and use Notes/Open Private Notes.command.
Notes > Accounts opens the private account panel. For Google choose only Notes,
using your email and app password. Existing Notes Accounts Test04 sign-in and
private notes remain in the same location; no reset is required.
Identity: org.ntest.Notes. Notes and Mail account support files live under
~/Library/Application Support/ML Private Notes. Account settings are in
~/Library/ML Notes Accounts/V1. Credentials use org.ntest.RestoredApps/.
Stock Notes/Mail/account/contact/calendar stores stay protected by the launcher.
Use the launcher on each run so the private frameworks/storage routing apply.
Old notes from the original restored Notes container are not automatically
migrated. Google notes synchronize via Gmail's Notes folder, not Google Keep.
Sync while Notes is running is tested; no Notes background login job is included.
iCloud testing is deferred.

SWITCHING THE COMBINED PACKAGE
Before relocating Contacts/Calendar with their login helpers enabled, disable
those helpers using their old folders' Disable commands, stop Calendar's test
helper, and quit the restored apps. Extract Preview06 to a permanent folder.
Launch Calendar/Open Calendar.command and Contacts/Open Contacts.command;
re-enable their login helpers from the new folders if desired. Keep the folder
at that location while those jobs are enabled. Private Google data/accounts are
retained. A relocated app/helper may ask for Keychain access again.
You can also test only this package's Notes folder while keeping your current
Calendar and Contacts packages in place.

REMAINING NOTES CHECKS
1. Create a disposable Google note in restored Notes; check it on another Mac.
2. Edit it on the other Mac; check the change in restored Notes.
3. Delete that disposable note and confirm deletion reaches the other Mac.
4. Quit/reopen using the launcher, then log out/in and launch again. Check notes
   and sign-in persist. Collect Private Notes Log.command produces diagnostics.
Do not delete existing real notes for this check. Send results and the ZIP.

CALENDAR / CONTACTS / BIRTHDAYS
Calendar uses MLCalAuth and ML-CalAuthx. Use Message for Google reminders that
must reach Android; local Calendar sound alerts remain available. Its user-tested
login alert helper handles alerts while Calendar is closed.
Contacts uses ML-GContact and ML Contacts Accts; its optional login helper syncs
approximately every two minutes. Google setup uses CardDAV server google.com,
full email, app password, SSL port443. Background logout/login sync was tested.
Birthdays still use exported Contacts vCards. Re-export and refresh after contact
birthday changes; the background contact sync does not refresh an export.

VALIDATION
App signatures, launcher/collector syntax, archive hashes, symlink targets,
and executable modes are checked on the build host. Legacy apps are not run
there. Notes creation/deletion/relogin and combined path-change checks still
need Mavericks verification. Stock apps and their data are not replaced.
''')
assert inventory(D/'Notes')==inventory(N)
for name in ['Contacts','Calendar','Birthdays']:assert inventory(D/name)==inventory(S/name)
for p in D.rglob('*.command'):run('bash','-n',p)
for p in D.rglob('*.py'):compile(p.read_bytes(),str(p),'exec')
apps=[D/n/('Mountain Lion '+n+'.app') for n in ['Notes','Contacts','Calendar']]+[D/'Birthdays/Birthday Bridge.app']
for app in apps:run('codesign','--verify','--deep','--strict',app)
(D/'package-manifest.json').write_text(json.dumps({'package':'Preview06','components':['Notes Accounts04','Contacts/Calendar/Birthdays byte-identical to Preview05'],'runtime':'Google Notes downloads and edit upload user-confirmed; remaining lifecycle checks pending','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name)
for app in apps:run('codesign','--verify','--deep','--strict',V/D.name/app.relative_to(D))
(R/'reports/preview-06-validation.json').write_text(json.dumps({'archive':str(A),'sha256':hashlib.sha256(A.read_bytes()).hexdigest(),'roundtrip':'all hashes, links, modes match','signatures':'all four apps passed after extraction','unchanged_components':'Contacts/Calendar/Birthdays match Preview05','notes':'matches Accounts04','runtime':'remaining Notes checks and path-change check pending'},indent=2)+'\n');print(A)
