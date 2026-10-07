from pathlib import Path
import subprocess,shutil,json,hashlib,os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/notes-icloud-menu-14/NotesAccounts';A=R/'deliverables/Notes-iCloud-Menu-Test-14.zip';V=R/'work/notes-icloud-menu14-verification'
if any(p.exists() for p in (D,A,V)):raise RuntimeError('Existing artifacts preserved')
def run(*args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
shutil.copytree(R/'builds/notes-private-accounts-04/NotesAccounts',D,symlinks=True)
APP=D/'Mountain Lion Notes.app';lib=APP/'Contents/Frameworks/MLNotesAccountsUI.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Cocoa','-Wl,-install_name,@rpath/MLNotesAccountsUI.dylib','-o',lib,R/'notes_account_ui_icloud14.m')
for t in (lib,APP):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',t)
run('codesign','--verify','--deep','--strict',APP)
(D/'READ ME FIRST.txt').write_text('RESTORED NOTES ICLOUD SYNC TRACE TEST 14\n\nQuit the previous restored Notes and open this build. Use your existing iCloud account; do not add another account or reset data. Create one disposable note in an iCloud folder, wait two minutes, and check the other Mac. Edit a different disposable note on the other Mac and wait two minutes with Restored Notes left open. Collect the log before quitting, then reopen and collect again if the change only appears after relaunch. Logs record login, folder refresh and native upload results without note contents, titles or credentials. This is a diagnostic build, not a confirmed live-sync fix.\n')
for p in D.glob('*.command'):run('bash','-n',p)
def inventory(root):
 return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o141)}) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
(D/'manifest.json').unlink()
(D/'manifest.json').write_text(json.dumps({'build':'Notes iCloud menu test 14','runtime':'pending','change':'Trace private iCloud native authentication, refresh and add/update/delete upload results; existing account retained; runtime pending','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V)
assert inventory(D)==inventory(V/D.name)
run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/notes-icloud-menu14-validation.json').write_text(json.dumps({'build':A.name,'signatures':'passed before and after extraction','archive_inventory':'identical','legacy_execution_on_host':False,'runtime':'pending'},indent=2)+'\n')
print(A)
