from pathlib import Path
import shutil,subprocess,json,hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/contacts-background-01/ContactsAccounts';A=R/'deliverables/Contacts-Background-Sync-Test-01.zip';V=R/'work/contacts-background01-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*a):return subprocess.check_output([str(x) for x in a],text=True,stderr=subprocess.STDOUT)
shutil.copytree(R/'builds/contacts-private-accounts-02/ContactsAccounts',D,symlinks=True)
shutil.copy2(R/'contacts_background_control.py',D/'contacts_background_control.py')
for name,mode in [('Enable Contacts Sync at Login.command','enable'),('Disable Contacts Sync at Login.command','disable'),('Contacts Sync Status.command','status')]:
 p=D/name;p.write_text('#!/bin/bash\nset -eu\nHERE="$(cd "$(dirname "$0")" && pwd)"\n/usr/bin/python "$HERE/contacts_background_control.py" '+mode+'\n');p.chmod(0o755)
p=D/'collect_contacts_accounts.py';s=p.read_text();start=s.index("p=os.path.expanduser");s=s[:start]+'''for filename in ('Contacts.log','BackgroundSync.log'):
 p=os.path.expanduser('~/Library/Logs/ML Contacts Accounts/'+filename)
 print('LOG '+filename)
 if os.path.isfile(p):
  with open(p,'rb') as f:s=f.read().decode('utf8','replace')
  for line in s.splitlines()[-6000:]:
   if not re.search('private_|error|fail|exception|crash|CardDAV|account|sync',line,re.I):continue
   if re.search('password|passwd|credential|bearer|token|authorization:|cookie:',line,re.I):continue
   line=re.sub(r'[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}','[email]',line)
   line=re.sub(r'(https?://[^\\s?]+)\\?[^\\s]+',r'\\1?[query omitted]',line)
   print(line)
''';p.write_text(s)
p=D/'Collect Contacts Account Log.command';s=p.read_text().replace('/bin/cp "$HERE/manifest.json"', '/usr/bin/python "$HERE/contacts_background_control.py" status > "$OUT/helper-status.txt" 2>&1 || true\n/bin/cp "$HERE/manifest.json"');p.write_text(s)
(D/'READ ME FIRST.txt').write_text('''RESTORED CONTACTS BACKGROUND SYNC TEST 01 — MAVERICKS

The Contacts app is unchanged from successful account Test 02. Google account
and contact data remain in the same private folders. This adds an optional
private Mountain Lion AddressBookSourceSync login job and two-minute schedule.
No stock job is modified. Enabling/disabling is explicitly done with commands.
Do not run two test copies at once. No Calendar or Notes changes.

Quit the previous restored Contacts, extract to a permanent folder, and run
Enable Contacts Sync at Login.command. Keep Contacts closed. Create or rename
one disposable Google contact on Android/web and wait 2–3 minutes. Collect
Contacts Account Log before opening Contacts, then open it to check the change.
Repeat after logout/login with Contacts closed. Send the log and results.
Initial helper execution/background downloading remain unverified on Mavericks.
Contacts Sync Status.command shows the job. The helper may exit between runs;
this is normal for a periodic sync job. Collect logs even when enabling fails.
Disable Contacts Sync at Login.command unloads/removes only our marked job and
retains contact/account data. Disable it before moving/removing this package.
''')
for p in D.glob('*.command'):run('bash','-n',p)
for p in D.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
run('codesign','--verify','--deep','--strict',D/'Mountain Lion Contacts.app')
def inventory(root):
 return {str(p.relative_to(root)):({'link':str(p.readlink())} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_symlink() or p.is_file()}
assert inventory(D/'Mountain Lion Contacts.app')==inventory(R/'builds/contacts-private-accounts-02/ContactsAccounts/Mountain Lion Contacts.app')
(D/'manifest.json').write_text(json.dumps({'build':'Contacts background test 01','runtime':'interactive sync confirmed; background helper pending','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name);run('codesign','--verify','--deep','--strict',V/D.name/'Mountain Lion Contacts.app')
(R/'reports/contacts-background01-validation.json').write_text(json.dumps({'archive':str(A),'app':'unchanged from user-tested Contacts 02','signatures':'pass after extraction','archive':'hashes/symlinks/modes match','background_runtime':'pending'},indent=2)+'\n');print(A)
