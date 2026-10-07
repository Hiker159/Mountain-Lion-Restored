from pathlib import Path
import shutil,subprocess,json,hashlib,os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/contacts-photo-08/ContactsAccounts';APP=D/'Mountain Lion Contacts.app'
A=R/'deliverables/Contacts-Photo-Test-08.zip';V=R/'work/contacts-photo08-verification'
def run(*args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
if any(p.exists() for p in (D,A,V)):raise RuntimeError('Existing artifacts preserved')
shutil.copytree(R/'builds/contacts-background-01/ContactsAccounts',D,symlinks=True)
p=APP/'Contents/Frameworks/MLAccountBootstrap.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-Wl,-install_name,@rpath/MLAccountBootstrap.dylib','-o',p,R/'contacts_photo_callback_compat.m')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',p)
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',APP)
run('codesign','--verify','--deep','--strict',APP)
(D/'READ ME FIRST.txt').write_text('''CONTACTS ICLOUD TEST 04 — MAVERICKS

The crash report showed legacy iCloud push setup crashing in a Security query. This build bypasses the private AddressBook push center; the existing two-minute AddressBookSourceSync helper provides background polling. This applies to restored Contacts accounts only. No account, contact database or Keychain items are removed.

Quit restored Contacts and run Disable Contacts Sync at Login.command from the previous package. Extract this package to a permanent folder. Run its Open Contacts.command, then Enable Contacts Sync at Login.command. Keep the existing iCloud account; do not reset its data. Do not run two copies at once.

Check that the app reopens and iCloud contacts download. Test creating/editing a disposable contact in both directions. With the app closed, change a contact on another device and wait 2–3 minutes, then reopen Contacts to inspect it. Send Collect Contacts Account Log.command's archive, including any failure.

Push is bypassed in favor of polling; immediate remote updates are not promised. Mavericks runtime testing is pending.
''')
def inventory(root):
 return {str(p.relative_to(root)):(['link',os.readlink(p)] if p.is_symlink() else ['file',hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode&0o777]) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
for p in D.glob('*.command'):run('bash','-n',p)
for p in D.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
(D/'manifest.json').write_text(json.dumps({'build':'Contacts photo callback test 08','runtime':'pending','change':'Private legacy push bypass; original background polling retained','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V)
assert inventory(D)==inventory(V/D.name)
run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/contacts-photo08-validation.json').write_text(json.dumps({'build':A.name,'signature':'passed before and after extraction','archive_inventory':'identical','runtime':'pending'},indent=2)+'\n')
print(A)
