"""Integrate tested Notes persistence routing into a separately identified app."""
from pathlib import Path
import subprocess,shutil,os,json,hashlib,plistlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/notes-private-storage-01/NotesPrivate';A=R/'deliverables/Notes-Private-Storage-Test-01.zip';V=R/'work/notes-private-storage01-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*a):return subprocess.check_output([str(x) for x in a],text=True,stderr=subprocess.STDOUT)
D.mkdir(parents=True);APP=D/'Mountain Lion Notes.app'
shutil.copytree(R/'builds/restored-apps-preview-05/Notes/Mountain Lion Notes.app',APP,symlinks=True)
F=APP/'Contents/Frameworks';shutil.rmtree(F)
shutil.copytree(R/'builds/notes-account-probe-02/NotesAccounts/Contents/Frameworks',F,symlinks=True)
shutil.copytree(R/'builds/notes-account-probe-02/NotesAccounts/Contents/AccountPlugins',APP/'Contents/AccountPlugins',symlinks=True)
routing=(R/'notes_account_plugin_routing.m').read_text();(R/'notes_account_plugin_routing.m').write_text(routing)
bootstrap=(R/'contacts_account_bootstrap.m').read_text().replace('contacts_account_plugin_routing.m','notes_account_plugin_routing.m').replace('ML Contacts Accts','ML Notes Accounts')
(R/'notes_account_bootstrap.m').write_text(bootstrap)
security=(R/'account_security_compat.c').read_text().replace('org.local.RestoredApps/','org.ntest.RestoredApps/');(R/'notes_account_security.c').write_text(security)
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fblocks','-Werror','-Wno-deprecated-declarations','-framework','CoreFoundation','-Wl,-no_fixup_chains,-reexport_framework,Security','-Wl,-install_name,@rpath/MLAccountSecurity.dylib','-Wl,-compatibility_version,55179.3.0','-Wl,-current_version,55179.13.0','-o',F/'MLAccountSecurity.dylib',R/'notes_account_security.c')
replacements=[(b'com.apple.Notes',b'org.ntest.Notes'),(b'com.apple.mail',b'org.ntest.mail'),(b'org.ctest',b'org.ntest')]
assert all(len(a)==len(b) for a,b in replacements)
mapping={}
for frame in F.glob('*.framework'):
 for v in (frame/'Versions').iterdir():
  if not v.is_symlink() and (v/frame.stem).is_file():
   for area in ['Frameworks','PrivateFrameworks']:mapping[f'/System/Library/{area}/{frame.name}/Versions/{v.name}/{frame.stem}']=v/frame.stem
mapping['/System/Library/Frameworks/Security.framework/Versions/A/Security']=F/'MLAccountSecurity.dylib'
edges=[];machos=[]
for p in APP.rglob('*'):
 if p.is_symlink() or not p.is_file():continue
 data=p.read_bytes()
 if data[:4] in [b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe']:
  if run('lipo','-archs',p).split()!=['x86_64']:
   tmp=p.with_name(p.name+'.thin');run('lipo',p,'-thin','x86_64','-output',tmp);os.replace(tmp,p)
  data=p.read_bytes()
  for a,b in replacements:data=data.replace(a,b)
  p.write_bytes(data)
  args=['install_name_tool']
  if p.name!='MLAccountSecurity.dylib':
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
  updated=replace(value)
  if isinstance(value,dict) and 'CFBundleExecutable' in value:updated['CFBundleExecutable']=value['CFBundleExecutable']
  p.write_bytes(plistlib.dumps(updated))
for source,name in [('notes_account_bootstrap.m','MLAccountBootstrap.dylib'),('notes_storage_bootstrap.m','MLNotesStorage.dylib')]:
 run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-Wl,-install_name,@rpath/'+name,'-o',F/name,R/source);machos.append(F/name)
# Own seatbelt profile protects stock stores; remove app-container entitlement so
# our tested libraryURL override is free to use the separate local store.
ents=D/'test-entitlements.plist';ents.write_bytes(plistlib.dumps({}))
suffixes={'.framework','.app','.bundle','.xpc','.iaplugin','.sourcebundle','.syncschema','.sharingservice','.webplugin'}
for p in machos:
 if p.parent.name!='MacOS' and not any(a.suffix=='.framework' and p.name==a.stem for a in p.parents):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',p)
for b in sorted({p for p in APP.rglob('*') if p.is_dir() and p.suffix in suffixes}|{APP},key=lambda p:len(p.parts),reverse=True):
 run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--entitlements',ents,'--requirements','=library => true',b)
run('codesign','--verify','--deep','--strict',APP)
(D/'notes-private.sb').write_text('''(version 1)
(allow default)
(deny network*)
(deny file-read* file-write* (subpath (param "KEYCHAINS")) (subpath (param "ACCOUNTS")) (subpath (param "INET")) (subpath (param "MAIL")) (subpath (param "NOTES")) (subpath (param "CONTACTS")) (subpath (param "CALENDARS")))
(deny file-write* (literal (param "NOTES_PREFS")) (literal (param "MAIL_PREFS")))
''')
p=D/'Open Private Notes.command';p.write_text('''#!/bin/bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$(/usr/bin/sw_vers -productVersion)" in 10.9|10.9.*) ;; *) echo 'Use on Mavericks only.'; exit 1;; esac
if [ "$(/usr/bin/id -u)" = 0 ]; then echo 'Run without sudo.'; exit 1; fi
APP="$HERE/Mountain Lion Notes.app"
LOG="$HOME/Library/Logs/ML Private Notes"
/bin/mkdir -p "$LOG"
/usr/bin/codesign --verify --deep "$APP"
if [ -f "$LOG/Notes.log" ]; then /bin/mv -f "$LOG/Notes.log" "$LOG/Notes.log.previous"; fi
/usr/bin/nohup /usr/bin/sandbox-exec -D "KEYCHAINS=$HOME/Library/Keychains" -D "ACCOUNTS=$HOME/Library/Accounts" -D "INET=$HOME/Library/Internet Accounts" -D "MAIL=$HOME/Library/Mail" -D "NOTES=$HOME/Library/Containers/com.apple.Notes" -D "CONTACTS=$HOME/Library/Application Support/AddressBook" -D "CALENDARS=$HOME/Library/Calendars" -D "NOTES_PREFS=$HOME/Library/Preferences/com.apple.Notes.plist" -D "MAIL_PREFS=$HOME/Library/Preferences/com.apple.mail.plist" -f "$HERE/notes-private.sb" /usr/bin/env "DYLD_INSERT_LIBRARIES=$APP/Contents/Frameworks/MLAccountBootstrap.dylib:$APP/Contents/Frameworks/MLNotesStorage.dylib" "$APP/Contents/MacOS/Notes" > "$LOG/Notes.log" 2>&1 < /dev/null &
echo 'Private Notes launch requested. This first app test is local only.'
''');p.chmod(0o755)
(D/'collect_notes_private.py').write_text('''from __future__ import print_function
import os,re,sys,codecs
if sys.version_info[0]<3:sys.stdout=codecs.getwriter('utf-8')(sys.stdout)
root=os.path.expanduser('~/Library/Logs/ML Private Notes')
for name in ['Notes.log.previous','Notes.log']:
 p=os.path.join(root,name)
 if not os.path.isfile(p):continue
 print('LOG '+name)
 with open(p,'rb') as f:s=f.read().decode('utf8','replace')
 for line in s.splitlines()[-6000:]:
  if not re.search('PRIVATE_|error|fail|exception|crash',line,re.I):continue
  if re.search('password|passwd|credential|bearer|token|authorization|cookie',line,re.I):continue
  line=re.sub(r'[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}','[email]',line)
  print(line)
store=os.path.expanduser('~/Library/Application Support/ML Private Notes/Library')
count=0
if os.path.isdir(store):
 for base,dirs,files in os.walk(store):count+=sum(n.endswith('.storedata') for n in files)
print('PRIVATE_STORE_FILE_COUNT='+str(count))
''')
p=D/'Collect Private Notes Log.command';p.write_text('''#!/bin/bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/Notes-private-$(/bin/date +%Y%m%d-%H%M%S)-$$"
/bin/mkdir "$OUT"
/usr/bin/python "$HERE/collect_notes_private.py" > "$OUT/notes.log" 2>&1
/bin/cp "$HERE/manifest.json" "$OUT/manifest.json"
/usr/bin/ditto -c -k --keepParent "$OUT" "$OUT.zip"
echo "Send: $OUT.zip"
''');p.chmod(0o755)
(D/'READ ME FIRST.txt').write_text('''PRIVATE NOTES APP TEST 01 — MAVERICKS

Quit other restored Notes copies. Extract this folder separately and launch
with Open Private Notes.command (use the launcher for every test launch).
This is a fresh local-only store, so previous notes should not appear.
Do not add an account yet; sign-in UI is the next stage. Network and Keychain
file access are blocked in this first app test.

1. Create two disposable notes and edit one.
2. Quit Notes and reopen with the launcher. Check both notes and edits remain.
3. Delete one disposable note. Check fullscreen and normal window mode.
4. Run Collect Private Notes Log.command and send its ZIP with results.

Own identity: org.ntest.Notes. Own data:
~/Library/Application Support/ML Private Notes/Library
Own accounts: ~/Library/ML Notes Accounts/V1 (not configured yet).
Existing Notes containers, Mail, account/contact/calendar stores are blocked.
No old notes are copied or migrated and no background job is installed.
The log collector excludes note contents, databases, and Keychains.
Compatibility of the integrated app still requires this Mavericks test.
''')
for p in D.glob('*.command'):run('bash','-n',p)
compile((D/'collect_notes_private.py').read_bytes(),'collector','exec')
missing=[]
for p in machos:
 for l in run('otool','-L',p).splitlines()[1:]:
  dep=l.strip().split(' (')[0]
  if dep.startswith('@loader_path/') and not (p.parent/dep[13:]).exists():missing.append([str(p),dep])
assert not missing,missing
def inventory(root):return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_symlink() or p.is_file()}
(D/'manifest.json').write_text(json.dumps({'build':'Notes private storage app 01','runtime':'pending Mavericks app test','identity':'org.ntest.Notes','sync_enabled':False,'dependency_redirects':edges,'files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name);run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/notes-private-storage01-validation.json').write_text(json.dumps({'archive':str(A),'signatures':'passed after extraction','roundtrip':'hashes, links, modes match','local_dependencies':'all resolve','shell_and_collector_syntax':'passed','runtime':'pending','legacy_execution_on_host':False},indent=2)+'\n');print(A)
