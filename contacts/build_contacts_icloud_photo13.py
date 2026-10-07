from pathlib import Path
import shutil,subprocess,json,hashlib,os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/contacts-icloud-photo-13/ContactsAccounts';APP=D/'Mountain Lion Contacts.app'
A=R/'deliverables/Contacts-iCloud-Photo-Test-13.zip';V=R/'work/contacts-icloud-photo13-verification'
def run(*args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
if any(p.exists() for p in (D,A,V)):raise RuntimeError('Existing artifacts preserved')
shutil.copytree(R/'builds/contacts-background-01/ContactsAccounts',D,symlinks=True)
p=APP/'Contents/Frameworks/MLAccountBootstrap.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-Wl,-install_name,@rpath/MLAccountBootstrap.dylib','-o',p,R/'contacts_icloud_photo_auth.m')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',p)
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',APP)
run('codesign','--verify','--deep','--strict',APP)
(D/'READ ME FIRST.txt').write_text('CONTACTS ICLOUD PHOTO TEST 13 — MAVERICKS\n\nThis experimental build removes the legacy MobileMe token preauthentication request only for iCloud photo GETs made by the private CardDAV client. Normal DAV authentication remains in place. The authentication hook now waits for the private CoreDAV framework to load; Test 12 did not install the hook. It includes the working local/Google photo callback adapter, Export Test 11 fixes, and two-minute background sync. No contacts or accounts are reset.\n\nQuit restored Contacts. From the previous package run Disable Contacts Sync at Login.command. Extract this package to a permanent folder, run Open Contacts.command, then Enable Contacts Sync at Login.command. Keep your existing accounts. Do not run two copies at once.\n\nCheck the disposable iCloud contact that has a photo on your newer Mac. Refresh Contacts and wait 2–3 minutes. Check whether its photo appears and survives reopening. Then add or replace a photo on a disposable iCloud contact in restored Contacts, wait for sync, and check both Macs. Send the archive from Collect Contacts Account Log.command.\n\nMavericks photo runtime testing is pending. No credentials or photo contents are added to diagnostic logging.\n')
def inventory(root):
 return {str(p.relative_to(root)):(['link',os.readlink(p)] if p.is_symlink() else ['file',hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode&0o777]) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
for p in D.glob('*.command'):run('bash','-n',p)
for p in D.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
(D/'manifest.json').write_text(json.dumps({'build':'Contacts iCloud photo test 13','runtime':'pending','change':'Remove MobileMe token preauthentication from private iCloud contact photo GETs; retain Export Test 11 and background polling','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V)
assert inventory(D)==inventory(V/D.name)
run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/contacts-icloud-photo13-validation.json').write_text(json.dumps({'build':A.name,'signature':'passed before and after extraction','archive_inventory':'identical','runtime':'pending'},indent=2)+'\n')
print(A)
