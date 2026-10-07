"""Keep standard message UTIs distinct from private app/account identifiers."""
from pathlib import Path
import subprocess,shutil,os,json,hashlib,plistlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/notes-private-accounts-04/NotesAccounts';A=R/'deliverables/Notes-Private-Accounts-Test-04.zip';V=R/'work/notes-private-accounts04-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*a):return subprocess.check_output([str(x) for x in a],text=True,stderr=subprocess.STDOUT)
shutil.copytree(R/'builds/notes-private-accounts-03/NotesAccounts',D,symlinks=True)
APP=D/'Mountain Lion Notes.app'
replacements=[(b'org.ntest.mail-',b'com.apple.mail-'),(b'org.ntest.mail.emlx',b'com.apple.mail.emlx')]
assert all(len(a)==len(b) for a,b in replacements)
changes=[];dirty=[]
for p in APP.rglob('*'):
 if p.is_symlink() or not p.is_file():continue
 data=p.read_bytes()
 if data[:4] in [b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe']:
  before=data
  for a,b in replacements:data=data.replace(a,b)
  if data!=before:p.write_bytes(data);dirty.append(p);changes.append(str(p.relative_to(APP)))
 elif p.suffix=='.plist':
  try:value=plistlib.loads(data)
  except Exception:continue
  def replace(v):
   if isinstance(v,str):
    for a,b in replacements:v=v.replace(a.decode(),b.decode())
   elif isinstance(v,list):v=[replace(x) for x in v]
   elif isinstance(v,dict):v={replace(k):replace(x) for k,x in v.items()}
   return v
  new=replace(value)
  if new!=value:p.write_bytes(plistlib.dumps(new));changes.append(str(p.relative_to(APP)))
assert dirty, 'Expected altered message UTIs'
suffixes={'.framework','.app','.bundle','.xpc','.iaplugin','.sourcebundle','.syncschema','.sharingservice','.webplugin','.prefPane'}
for p in dirty:
 if p.parent.name!='MacOS' and not any(a.suffix=='.framework' and p.name==a.stem for a in p.parents):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',p)
for b in sorted({p for p in APP.rglob('*') if p.is_dir() and p.suffix in suffixes}|{APP},key=lambda p:len(p.parts),reverse=True):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',b)
run('codesign','--verify','--deep','--strict',APP)
core=APP/'Contents/Frameworks/CoreMessage.framework/Versions/A/CoreMessage'
data=core.read_bytes();assert b'com.apple.mail-note\0' in data and b'org.ntest.mail-note' not in data
message=APP/'Contents/Frameworks/Message.framework/Versions/B/Message'
assert b'org.ntest.mail.plist' in message.read_bytes(), 'Private preference namespace must remain'
p=D/'READ ME FIRST.txt';s=p.read_text().replace('ACCOUNTS TEST 03','ACCOUNTS TEST 04');s+='\nTEST 04 — NOTE CONTENT TYPES\nSeparating Mail preference IDs had also changed standard mail-note/message\ncontent types. Those standard identifiers are restored; private identities,\naccounts, credentials, and storage remain separate.\n\nQuit the older restored Notes, launch this copy using the launcher, and keep\nyour existing private Google account (no reset or sign-in setup needed).\nAllow two minutes, then select the Google Notes folder. Check existing notes\nappear. If they do, create one disposable note in the Google account and\ncheck another Mac. Quit and reopen to check persistence. If a note was created\nby an earlier test with the incorrect type, leave it alone for now.\nCollect the log and describe the outcome even if existing notes remain absent.\n';p.write_text(s)
for p in D.glob('*.command'):run('bash','-n',p)
def inventory(root):return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_symlink() or p.is_file()}
(D/'manifest.json').unlink();(D/'manifest.json').write_text(json.dumps({'build':'Notes private accounts 04','runtime':'pending Mavericks test','change':'Restore standard mail content UTIs, retain private app/account/defaults identities','changed_files':changes,'files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name);run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/notes-accounts04-validation.json').write_text(json.dumps({'archive':str(A),'signatures':'passed after extraction','roundtrip':'hashes, links, modes match','content_types':'standard mail-note restored','private_mail_preferences':'retained','changed_files':changes,'legacy_execution_on_host':False,'runtime':'pending'},indent=2)+'\n');print(A)
