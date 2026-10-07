from pathlib import Path
import subprocess,shutil,json,hashlib,os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/notes-icloud-menu-06/NotesAccounts';A=R/'deliverables/Notes-iCloud-Menu-Test-06.zip';V=R/'work/notes-icloud-menu06-verification'
if any(p.exists() for p in (D,A,V)):raise RuntimeError('Existing artifacts preserved')
def run(*args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
shutil.copytree(R/'builds/notes-private-accounts-04/NotesAccounts',D,symlinks=True)
APP=D/'Mountain Lion Notes.app';lib=APP/'Contents/Frameworks/MLNotesAccountsUI.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Cocoa','-Wl,-install_name,@rpath/MLNotesAccountsUI.dylib','-o',lib,R/'notes_account_ui_icloud06.m')
for t in (lib,APP):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',t)
run('codesign','--verify','--deep','--strict',APP)
(D/'READ ME FIRST.txt').write_text("""RESTORED NOTES — ICLOUD MENU TEST 06

Quit the older restored Notes. Extract this package to a permanent folder and run Open Private Notes.command. Existing private Notes and Google accounts remain in the same storage. No account reset is needed.

Open Notes > Add iCloud Notes Account… and choose Continue. This opens the dedicated private Notes IMAP account wizard, avoiding the Mail app handoff that stalled Test 05. Use your iCloud Mail address and an app-specific password. Choose IMAP if offered account types. If server details are requested: IMAP imap.mail.me.com, SSL, port 993; SMTP smtp.mail.me.com, TLS, port 587. Start with your full iCloud Mail address as username.

Wait two minutes and check whether an iCloud Notes folder and existing legacy notes appear. If so, create a disposable note and check another legacy Mac. Test editing both ways and reopening. Use Collect Private Notes Log.command and send its archive, without passwords.

This tests the legacy IMAP Notes path. It does not implement the upgraded iCloud Notes format used by newer Apple Notes. Apple states upgraded notes require OS X 10.11 or later. A successful mail connection does not prove upgraded iCloud notes will appear. Google support and private storage protection are retained. Mavericks runtime testing is pending.

Apple settings: https://support.apple.com/102525
Compatibility: https://support.apple.com/guide/notes/apda3f8513ed/mac
""")
for p in D.glob('*.command'):run('bash','-n',p)
def inventory(root):
 return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
(D/'manifest.json').unlink()
(D/'manifest.json').write_text(json.dumps({'build':'Notes iCloud menu test 06','runtime':'pending','change':'Add iCloud Notes menu action opening private IMAP wizard with setup guidance; upgraded Notes not implemented','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V)
assert inventory(D)==inventory(V/D.name)
run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/notes-icloud-menu06-validation.json').write_text(json.dumps({'build':A.name,'signatures':'passed before and after extraction','archive_inventory':'identical','legacy_execution_on_host':False,'runtime':'pending'},indent=2)+'\n')
print(A)
