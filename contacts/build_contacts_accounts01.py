from pathlib import Path
import subprocess,shutil,os,json,hashlib,plistlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/contacts-private-accounts-01/ContactsAccounts';A=R/'deliverables/Contacts-Private-Accounts-Test-01.zip';V=R/'work/contacts-accounts01-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*a):return subprocess.check_output([str(x) for x in a],text=True,stderr=subprocess.STDOUT)
S=R/'builds/restored-apps-preview-04/Contacts';shutil.copytree(S,D,symlinks=True)
APP=D/'Mountain Lion Contacts.app';F=APP/'Contents/Frameworks';CF=R/'builds/calendar-private-accounts-10/CalendarAccounts/Mountain Lion Calendar.app/Contents/Frameworks'
for p in CF.iterdir():
 if (F/p.name).exists():shutil.rmtree(F/p.name) if (F/p.name).is_dir() else (F/p.name).unlink()
 if p.is_dir():shutil.copytree(p,F/p.name,symlinks=True)
 else:shutil.copy2(p,F/p.name)
shutil.copytree(R/'originals/System/Library/PrivateFrameworks/ShareKit.framework',F/'ShareKit.framework',symlinks=True)
plugins=APP/'Contents/AccountPlugins';plugins.mkdir()
for name in ['Google.iaplugin','AddressBook.iaplugin']:
 source=R/('work/account-plugin-assets' if name.startswith('Google') else 'work/contacts-account-assets')/'System/Library/InternetAccounts'/name
 shutil.copytree(source,plugins/name,symlinks=True)
shutil.copytree(R/'work/contacts-account-assets/System/Library/Address Book Plug-Ins/CardDAVPlugin.sourcebundle',APP/'Contents/PlugIns/ContactSources/CardDAVPlugin.sourcebundle',symlinks=True)
# Contacts-specific bootstrap/routing sources leave the working Calendar untouched.
routing=(R/'account_plugin_routing.m').read_text().replace('Calendar.iaplugin','AddressBook.iaplugin');(R/'contacts_account_plugin_routing.m').write_text(routing)
bootstrap=(R/'account_app_bootstrap.m').read_text().replace('account_plugin_routing.m','contacts_account_plugin_routing.m').replace('ML Cloud Accounts','ML Contacts Accts');(R/'contacts_account_bootstrap.m').write_text(bootstrap)
security=(R/'account_security_compat.c').read_text().replace('org.local.RestoredApps/','org.ctest.RestoredApps/');(R/'contacts_account_security.c').write_text(security)
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fblocks','-Werror','-Wno-deprecated-declarations','-framework','CoreFoundation','-Wl,-no_fixup_chains,-reexport_framework,Security','-Wl,-install_name,@rpath/MLAccountSecurity.dylib','-Wl,-compatibility_version,55179.3.0','-Wl,-current_version,55179.13.0','-o',F/'MLAccountSecurity.dylib',R/'contacts_account_security.c')
replacements=[(b'com.apple.AddressBook',b'org.ctest.AddressBook'),(b'org.authx',b'org.ctest'),(b'ML Cloud Accounts',b'ML Contacts Accts'),(b'ML-AcctBook',b'ML-GContact')]
assert all(len(a)==len(b) for a,b in replacements)
mapping={}
for frame in F.glob('*.framework'):
 for v in (frame/'Versions').iterdir():
  if v.is_symlink() or not (v/frame.stem).is_file():continue
  for area in ['Frameworks','PrivateFrameworks']:mapping[f'/System/Library/{area}/{frame.name}/Versions/{v.name}/{frame.stem}']=v/frame.stem
mapping['/System/Library/Frameworks/Security.framework/Versions/A/Security']=F/'MLAccountSecurity.dylib'
edges=[];machos=[]
for p in APP.rglob('*'):
 if not p.is_file() or p.is_symlink():continue
 data=p.read_bytes()
 if data[:4] in [b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe']:
  if run('lipo','-archs',p).split()!=['x86_64']:
   temp=p.with_name(p.name+'.thin');run('lipo',p,'-thin','x86_64','-output',temp);os.replace(temp,p)
  data=p.read_bytes()
  for a,b in replacements:data=data.replace(a,b)
  p.write_bytes(data)
  if p.name!='MLAccountSecurity.dylib':
   args=['install_name_tool']
   for line in run('otool','-L',p).splitlines()[1:]:
    dep=line.strip().split(' (')[0]
    if dep in mapping and not (p.name=='DataDetectors' and '/Security.framework/' in dep):
     target='@loader_path/'+os.path.relpath(mapping[dep],p.parent);args+=['-change',dep,target];edges.append([str(p.relative_to(APP)),dep,target])
   if len(args)>1:run(*args,p)
  machos.append(p)
 elif p.suffix=='.plist':
  try:value=plistlib.loads(data)
  except Exception:continue
  def replace(v):
   if isinstance(v,str):
    for a,b in replacements:v=v.replace(a.decode(),b.decode())
   elif isinstance(v,list):v=[replace(x) for x in v]
   elif isinstance(v,dict):v={replace(k):replace(x) for k,x in v.items()}
   return v
  p.write_bytes(plistlib.dumps(replace(value)))
lib=F/'MLAccountBootstrap.dylib';run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-Wl,-install_name,@rpath/MLAccountBootstrap.dylib','-o',lib,R/'contacts_account_bootstrap.m')
if lib not in machos:machos.append(lib)
suffixes={'.framework','.app','.bundle','.xpc','.iaplugin','.sourcebundle','.syncschema','.docktileplugin','.sharingservice'}
bundles={p for p in APP.rglob('*') if p.is_dir() and p.suffix in suffixes};bundles.add(APP)
for p in machos:
 main=p.parent.name=='MacOS' or any(a.suffix=='.framework' and p.name==a.stem for a in p.parents)
 if not main:run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',p)
for b in sorted(bundles,key=lambda p:len(p.parts),reverse=True):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',b)
run('codesign','--verify','--deep','--strict',APP)
(D/'contacts-accounts.sb').write_text('''(version 1)
(allow default)
(deny file-read* file-write* (subpath (param "STOCK_CONTACTS")) (subpath (param "STOCK_ACCOUNTS")) (subpath (param "STOCK_INET")) (subpath (param "STOCK_CALENDARS")))
(deny file-write* (literal (param "STOCK_CONTACT_PREFS")))
''')
p=D/'Open Contacts.command';p.write_text('''#!/bin/bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$(/usr/bin/sw_vers -productVersion)" in 10.9|10.9.*) ;; *) echo 'Use on Mavericks only.'; exit 1;; esac
if [ "$(/usr/bin/id -u)" = 0 ]; then echo 'Run without sudo.'; exit 1; fi
APP="$HERE/Mountain Lion Contacts.app"
LOG_DIR="$HOME/Library/Logs/ML Contacts Accounts"
/bin/mkdir -p "$LOG_DIR" "$HOME/Library/Application Support/ML-GContact"
/usr/bin/codesign --verify --deep "$APP"
if [ -f "$LOG_DIR/Contacts.log" ]; then /bin/mv -f "$LOG_DIR/Contacts.log" "$LOG_DIR/Contacts.log.previous"; fi
/usr/bin/nohup /usr/bin/sandbox-exec -D "STOCK_CONTACTS=$HOME/Library/Application Support/AddressBook" -D "STOCK_ACCOUNTS=$HOME/Library/Accounts" -D "STOCK_INET=$HOME/Library/Internet Accounts" -D "STOCK_CALENDARS=$HOME/Library/Calendars" -D "STOCK_CONTACT_PREFS=$HOME/Library/Preferences/com.apple.AddressBook.plist" -f "$HERE/contacts-accounts.sb" /usr/bin/env "DYLD_INSERT_LIBRARIES=$APP/Contents/Frameworks/MLAccountBootstrap.dylib" "$APP/Contents/MacOS/Contacts" -MLAlternateDataStoreDirectory "$HOME/Library/Application Support/ML-GContact" >> "$LOG_DIR/Contacts.log" 2>&1 < /dev/null &
echo 'Contacts launch requested. Use its Preferences > Accounts to add Google.'
''');p.chmod(0o755)
# Collector prints only filtered own log lines; excludes credential values and data stores.
(D/'collect_contacts_accounts.py').write_text('''from __future__ import print_function
import os,re
p=os.path.expanduser('~/Library/Logs/ML Contacts Accounts/Contacts.log')
if os.path.isfile(p):
 with open(p,'rb') as f:s=f.read().decode('utf8','replace')
 for line in s.splitlines()[-6000:]:
  if not re.search('private_|error|fail|exception|crash|CardDAV|account|sync',line,re.I):continue
  if re.search('password|passwd|credential|bearer|token|authorization:|cookie:',line,re.I):continue
  line=re.sub(r'[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}','[email]',line)
  line=re.sub(r'(https?://[^\\s?]+)\\?[^\\s]+',r'\\1?[query omitted]',line)
  print(line)
''')
p=D/'Collect Contacts Account Log.command';p.write_text('''#!/bin/bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/Contacts-accounts-$(/bin/date +%Y%m%d-%H%M%S)-$$"
/bin/mkdir "$OUT"
/usr/bin/python "$HERE/collect_contacts_accounts.py" > "$OUT/accounts.log" 2>&1
/usr/bin/codesign --verify --deep "$HERE/Mountain Lion Contacts.app" > "$OUT/signature.txt" 2>&1 || true
/bin/cp "$HERE/manifest.json" "$OUT/manifest.json"
/usr/bin/ditto -c -k --keepParent "$OUT" "$OUT.zip"
echo "$OUT.zip"
''');p.chmod(0o755)
# Omit old diagnostics aimed at the working Contacts store.
(D/'Diagnose Contacts.command').unlink()
(D/'READ ME FIRST.txt').write_text('''PRIVATE GOOGLE CONTACTS TEST 01 — MAVERICKS

Quit other restored Contacts copies; stock Contacts may remain closed for this
first test. Extract separately and run Open Contacts.command. This test has a
fresh identity org.ctest.AddressBook and separate contact data in
~/Library/Application Support/ML-GContact. Private accounts use
~/Library/ML Contacts Accts/V1. The working Calendar and Contacts stores are
not migrated or edited. No background login helper is installed.

Open Preferences > Accounts and add Google with your email/app password.
Select only Contacts. Grant access only to the test app if macOS asks.
Wait two minutes for Google contacts. Quit and reopen with the launcher and
check that they remain without repeated password prompts.
For this first round, do not edit/delete existing real contacts. If download
works, create one disposable contact in the Google account and check Android
or Google Contacts web. We will test edits/deletion in a subsequent round.
Run Collect Contacts Account Log.command and send the ZIP with your results.
If startup/account setup fails, collect the log anyway. Passwords are entered
only in the app; diagnostics exclude contact databases and Keychains.
Runtime compatibility and native Google Contacts syncing remain unverified.
''')
for p in D.glob('*.command'):run('bash','-n',p)
for p in D.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
def inventory(root):
 return {str(p.relative_to(root)):({'link':str(p.readlink())} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_symlink() or p.is_file()}
(D/'manifest.json').write_text(json.dumps({'build':'Contacts private accounts 01','runtime':'pending Mavericks test','dependency_redirects':edges,'files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name);run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/contacts-accounts01-validation.json').write_text(json.dumps({'archive':str(A),'roundtrip':'hashes/symlinks/executable flags match','signatures':'passed after extraction','runtime':'pending'},indent=2)+'\n')
print(A)
