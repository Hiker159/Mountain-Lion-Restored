from pathlib import Path
import subprocess,shutil,json,hashlib,os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/notes-icloud-menu-10/NotesAccounts';A=R/'deliverables/Notes-iCloud-Menu-Test-10.zip';V=R/'work/notes-icloud-menu10-verification'
if any(p.exists() for p in (D,A,V)):raise RuntimeError('Existing artifacts preserved')
def run(*args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
shutil.copytree(R/'builds/notes-private-accounts-04/NotesAccounts',D,symlinks=True)
APP=D/'Mountain Lion Notes.app';lib=APP/'Contents/Frameworks/MLNotesAccountsUI.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Cocoa','-Wl,-install_name,@rpath/MLNotesAccountsUI.dylib','-o',lib,R/'notes_account_ui_icloud10.m')
for t in (lib,APP):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',t)
run('codesign','--verify','--deep','--strict',APP)
(D/'READ ME FIRST.txt').write_text('RESTORED NOTES ICLOUD TEST 10\n\nQuit the old restored Notes. Extract this package and run Open Private Notes.command. Select Notes > Add iCloud Notes Account… . A separate form asks for your full iCloud Mail address and app-specific password. Click Add Account once. It creates an IMAP Notes account directly through the existing private Notes provider with SSL on port 993 and password authentication. It does not launch Mail or use the incomplete standalone Apple Notes wizard.\n\nWait two minutes and check the Notes sidebar for the account and any legacy notes. Send Collect Private Notes Log.command output and describe what appears. Account creation alone does not confirm server login or sync. Existing Google accounts are retained; do not reset any data. This does not support upgraded iCloud Notes.\n')
for p in D.glob('*.command'):run('bash','-n',p)
def inventory(root):
 return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
(D/'manifest.json').unlink()
(D/'manifest.json').write_text(json.dumps({'build':'Notes iCloud menu test 10','runtime':'pending','change':'Add iCloud Notes menu action opening private IMAP wizard with setup guidance; upgraded Notes not implemented','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V)
assert inventory(D)==inventory(V/D.name)
run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/notes-icloud-menu10-validation.json').write_text(json.dumps({'build':A.name,'signatures':'passed before and after extraction','archive_inventory':'identical','legacy_execution_on_host':False,'runtime':'pending'},indent=2)+'\n')
print(A)
