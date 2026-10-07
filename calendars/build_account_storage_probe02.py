from pathlib import Path
import shutil,subprocess,json,hashlib,zipfile,stat,os
from patch_account_storage import patch_internet_accounts
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/account-storage-probe-02/AccountBackend'
def run(*a):
 p=subprocess.run([str(v) for v in a],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
if D.exists():raise RuntimeError('Build destination already exists')
shutil.copytree(R/'builds/account-backend-probe-04/AccountBackend',D,symlinks=True)
frame=D/'Frameworks/InternetAccounts.framework';binary=frame/'Versions/A/InternetAccounts'
report=patch_internet_accounts(binary)
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',frame)
run('codesign','--verify','--strict','--deep',frame)
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-Werror','-Wl,-no_fixup_chains','-framework','CoreFoundation','-o',D/'AccountStorageProbe',R/'account_storage_probe.c')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1',D/'AccountStorageProbe')
run('codesign','--verify','--strict',D/'AccountStorageProbe')
launcher=D/'Check Account Backend.command'
s=launcher.read_text()
s=s.replace('echo "Exit status: $RESULT" >> "$OUT/backend.log"','''echo "Library load exit status: $RESULT" >> "$OUT/backend.log"
/usr/bin/sandbox-exec \\
 -D "HOME_ACCOUNTS=$HOME/Library/Accounts" \\
 -D "HOME_INET_ACCOUNTS=$HOME/Library/Internet Accounts" \\
 -D "HOME_KEYCHAINS=$HOME/Library/Keychains" \\
 -D "HOME_CALENDARS=$HOME/Library/Calendars" \\
 -D "HOME_ADDRESSBOOK=$HOME/Library/Application Support/AddressBook" \\
 -f "$HERE/backend-probe.sb" "$HERE/AccountStorageProbe" \\
 "$F/InternetAccounts.framework/Versions/A/InternetAccounts" \\
 "$HOME/Library/ML Cloud Accounts/V1" >> "$OUT/backend.log" 2>&1
STORAGE_RESULT=$?
echo "Storage path exit status: $STORAGE_RESULT" >> "$OUT/backend.log"
if [ "$STORAGE_RESULT" != 0 ]; then RESULT=$STORAGE_RESULT; fi''')
launcher.write_text(s);run('bash','-n',launcher)
(D/'READ ME FIRST.txt').write_text('''PRIVATE ACCOUNT STORAGE PROBE 02

Extract AccountBackend separately on Mavericks. Keep CalendarNetwork and
background GoogleSync stopped. Run Check Account Backend.command and send
the resulting Account-backend ZIP.

The path check now resolves the library URL against its home-directory base
before comparing it. Probe 01 incorrectly compared the relative path.

The first probe repeats library loading. The second asks the private library
for its computed account-storage URL. Expected: ~/Library/ML Cloud Accounts/V1.
It does not enumerate, create, change, or remove accounts; it does not call
password APIs or start a preference pane. It requests no networking. The
existing sandbox still blocks stock account, Keychain, calendar/contact paths.

Account cache paths and InternetAccounts preference/notification names are
redirected. Credential handling and plug-in routing are NOT yet isolated.
Do not use these frameworks for sign-in or copy them into restored apps.
This package is a path-verification probe, not a functioning account backend.
No password is needed. A pass validates the computed path, not persistence.

Built for x86_64 Mavericks 10.9; signatures, literal redirects, launcher syntax,
and archive hashes/modes/symlinks verified locally. Runtime requires Mavericks.
''')
(R/'reports/account-storage-probe02-patches.json').write_text(json.dumps(report,indent=2)+'\n')
manifest={'build':'account-storage-probe-02','runtime':'pending Mavericks path verification','files_sha256':{str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in D.rglob('*') if p.is_file() and not p.is_symlink() and p.name!='manifest.json'}}
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
zpath=R/'deliverables/Private-Account-Storage-Probe-02.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  n='AccountBackend/'+str(p.relative_to(D))
  if p.is_symlink():
   info=zipfile.ZipInfo(n);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,os.readlink(p))
  elif p.is_file():z.write(p,n)
with zipfile.ZipFile(zpath) as z:
 for rel,h in manifest['files_sha256'].items():assert hashlib.sha256(z.read('AccountBackend/'+rel)).hexdigest()==h
 for p in D.rglob('*'):
  n='AccountBackend/'+str(p.relative_to(D))
  if p.is_symlink():assert z.read(n).decode()==os.readlink(p)
  elif p.is_file():assert ((z.getinfo(n).external_attr>>16)&0o111)==(p.stat().st_mode&0o111)
print(str(zpath));print(json.dumps(report['changes']))
