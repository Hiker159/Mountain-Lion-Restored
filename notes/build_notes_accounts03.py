"""Route private Message framework account storage away from stock Mail."""
from pathlib import Path
import subprocess,shutil,os,json,hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/notes-private-accounts-03/NotesAccounts';A=R/'deliverables/Notes-Private-Accounts-Test-03.zip';V=R/'work/notes-private-accounts03-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*a):return subprocess.check_output([str(x) for x in a],text=True,stderr=subprocess.STDOUT)
shutil.copytree(R/'builds/notes-private-accounts-02/NotesAccounts',D,symlinks=True)
APP=D/'Mountain Lion Notes.app';F=APP/'Contents/Frameworks';lib=F/'MLNotesStorage.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-Wl,-install_name,@rpath/MLNotesStorage.dylib','-o',lib,R/'notes_storage_bootstrap03.m')
for t in [lib,APP]:run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',t)
run('codesign','--verify','--deep','--strict',APP)
p=D/'READ ME FIRST.txt';s=p.read_text().replace('ACCOUNTS TEST 02','ACCOUNTS TEST 03');s+='\nTEST 03 — PRIVATE MAIL ACCOUNT STORAGE\nThe previous panel initialized Mail account storage under stock Library/Mail\nand aborted because that path was blocked. Four Message Defaults root-path\nmethods now return ~/Library/Application Support/ML Private Notes/Mail.\nStock Mail remains blocked. Repeat the account-panel and Google test above.\nYour private notes from earlier tests stay in the same location.\n';p.write_text(s)
for p in D.glob('*.command'):run('bash','-n',p)
def inventory(root):return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_symlink() or p.is_file()}
(D/'manifest.json').unlink();(D/'manifest.json').write_text(json.dumps({'build':'Notes private accounts 03','runtime':'pending Mavericks test','change':'Own Mail root for private Message account storage; stock Mail sandbox deny retained','private_mail_root':'Library/Application Support/ML Private Notes/Mail','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name);run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/notes-accounts03-validation.json').write_text(json.dumps({'archive':str(A),'signatures':'passed after extraction','roundtrip':'hashes, links, modes match','shell_syntax':'passed','legacy_execution_on_host':False,'runtime':'pending'},indent=2)+'\n');print(A)
