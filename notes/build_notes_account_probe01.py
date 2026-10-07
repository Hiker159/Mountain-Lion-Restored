"""Build a load-only Mavericks Notes account probe; never execute legacy code here."""
from pathlib import Path
import subprocess,shutil,os,json,hashlib,plistlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/notes-account-probe-01/NotesAccounts'; A=R/'deliverables/Notes-Account-Probe-01.zip'; V=R/'work/notes-account-probe01-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*args):return subprocess.check_output([str(x) for x in args],text=True,stderr=subprocess.STDOUT)
F=D/'Contents/Frameworks'; F.parent.mkdir(parents=True)
shutil.copytree(R/'builds/contacts-background-01/ContactsAccounts/Mountain Lion Contacts.app/Contents/Frameworks',F,symlinks=True)
# Load-only probe uses explicit routing; no application bootstrap or alert helper.
for name in ['MLAccountBootstrap.dylib','MLAccountPluginRouting.dylib','MLCalendarWakeRecovery.dylib']:(F/name).unlink()
shutil.copytree(R/'builds/restored-apps-preview-05/Notes/Mountain Lion Notes.app/Contents/Frameworks/Notes.framework',F/'Notes.framework',symlinks=True)
P=D/'Contents/AccountPlugins';P.mkdir()
for name in ['Mail.iaplugin','Notes.iaplugin']:
 shutil.copytree(R/'work/notes-account-assets/System/Library/InternetAccounts'/name,P/name,symlinks=True)
shutil.copytree(R/'work/account-plugin-assets/System/Library/InternetAccounts/Google.iaplugin',P/'Google.iaplugin',symlinks=True)
routing=(R/'account_plugin_routing.m').read_text().replace('&&![name isEqualToString:@"Calendar.iaplugin"]','&&![name isEqualToString:@"Mail.iaplugin"]&&![name isEqualToString:@"Notes.iaplugin"]')
(R/'notes_account_plugin_routing.m').write_text(routing)
probe=(R/'account_plugin_probe.m').read_text().replace('if(argc!=4)','if(argc!=5)').replace('const char *ids[]={"com.apple.google.iaplugin","com.apple.calendar.iaplugin"};','void *notes=dlopen(argv[4],RTLD_NOW|RTLD_LOCAL);\n  if(!notes){printf("NOTES_LOAD_FAILED %s\\n",dlerror());return 5;}\n  puts("NOTES_FRAMEWORK_LOADED");\n  const char *ids[]={"com.apple.google.iaplugin","com.apple.mail.iaplugin","com.apple.Notes.iaplugin"};').replace('i<2','i<3')
(R/'notes_account_probe.m').write_text(probe)
mapping={}
for frame in F.glob('*.framework'):
 for v in (frame/'Versions').iterdir():
  if v.is_symlink() or not (v/frame.stem).is_file():continue
  for area in ['Frameworks','PrivateFrameworks']:mapping[f'/System/Library/{area}/{frame.name}/Versions/{v.name}/{frame.stem}']=v/frame.stem
mapping['/System/Library/Frameworks/Security.framework/Versions/A/Security']=F/'MLAccountSecurity.dylib'
edges=[];machos=[]
for p in D.rglob('*'):
 if p.is_symlink() or not p.is_file():continue
 if p.read_bytes()[:4] not in [b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe']:continue
 if run('lipo','-archs',p).split()!=['x86_64']:
  temp=p.with_name(p.name+'.thin');run('lipo',p,'-thin','x86_64','-output',temp);os.replace(temp,p)
 # Separate InternetAccounts path for this probe, even if a constructor asks for it.
 data=p.read_bytes().replace(b'ML Contacts Accts',b'ML Notes Accounts');p.write_bytes(data)
 args=['install_name_tool']
 if p.name!='MLAccountSecurity.dylib':
  for line in run('otool','-L',p).splitlines()[1:]:
   dep=line.strip().split(' (')[0]
   if dep in mapping and not (p.name=='DataDetectors' and '/Security.framework/' in dep):
    target='@loader_path/'+os.path.relpath(mapping[dep],p.parent);args+=['-change',dep,target];edges.append([str(p.relative_to(D)),dep,target])
 if len(args)>1:run(*args,p)
 machos.append(p)
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-Wl,-install_name,@rpath/MLNotesPluginRouting.dylib','-o',F/'MLNotesPluginRouting.dylib',R/'notes_account_plugin_routing.m')
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-o',D/'NotesAccountProbe',R/'notes_account_probe.m')
machos += [F/'MLNotesPluginRouting.dylib',D/'NotesAccountProbe']
suffixes={'.framework','.app','.bundle','.xpc','.iaplugin','.sourcebundle','.syncschema','.sharingservice'}
for p in machos:
 if p.parent.name!='MacOS' and not any(a.suffix=='.framework' and p.name==a.stem for a in p.parents):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',p)
for b in sorted({p for p in D.rglob('*') if p.is_dir() and p.suffix in suffixes},key=lambda p:len(p.parts),reverse=True):
 run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',b)
for b in F.glob('*.framework'):run('codesign','--verify','--deep','--strict',b)
for b in P.glob('*.iaplugin'):run('codesign','--verify','--deep','--strict',b)
(D/'notes-probe.sb').write_text('''(version 1)
(allow default)
(deny network*)
(deny file-read* file-write* (subpath (param "KEYCHAINS")) (subpath (param "ACCOUNTS")) (subpath (param "INET")) (subpath (param "MAIL")) (subpath (param "NOTES")) (subpath (param "CONTACTS")) (subpath (param "CALENDARS")))
(deny file-write* (subpath (param "PREFERENCES")) (subpath (param "PRIVATE_NOTES_ACCOUNTS")))
''')
launcher=D/'Check Notes Accounts.command'
launcher.write_text('''#!/bin/bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$(/usr/bin/sw_vers -productVersion)" in 10.9|10.9.*) ;; *) echo 'Use on Mavericks only.'; exit 1;; esac
if [ "$(/usr/bin/id -u)" = 0 ]; then echo 'Run without sudo.'; exit 1; fi
OUT="$HERE/Notes-accounts-$(/bin/date +%Y%m%d-%H%M%S)-$$"
/bin/mkdir "$OUT"
F="$HERE/Contents/Frameworks"
set +e
/usr/bin/sandbox-exec -D "KEYCHAINS=$HOME/Library/Keychains" -D "ACCOUNTS=$HOME/Library/Accounts" -D "INET=$HOME/Library/Internet Accounts" -D "MAIL=$HOME/Library/Mail" -D "NOTES=$HOME/Library/Containers/com.apple.Notes" -D "CONTACTS=$HOME/Library/Application Support/AddressBook" -D "CALENDARS=$HOME/Library/Calendars" -D "PREFERENCES=$HOME/Library/Preferences" -D "PRIVATE_NOTES_ACCOUNTS=$HOME/Library/ML Notes Accounts" -f "$HERE/notes-probe.sb" "$HERE/NotesAccountProbe" "$F/InternetAccounts.framework/Versions/A/InternetAccounts" "$F/MLNotesPluginRouting.dylib" "$HERE/Contents/AccountPlugins" "$F/Notes.framework/Versions/A/Notes" > "$OUT/probe.log" 2>&1
RESULT=$?
set -e
echo "Probe exit status: $RESULT" >> "$OUT/probe.log"
/bin/cp "$HERE/manifest.json" "$OUT/manifest.json"
/usr/bin/ditto -c -k --keepParent "$OUT" "$OUT.zip"
echo "Send this diagnostic ZIP: $OUT.zip"
echo 'This is a load test; no sign-in or note synchronization was requested.'
''');launcher.chmod(0o755);run('bash','-n',launcher)
(D/'READ ME FIRST.txt').write_text('''NOTES ACCOUNT LOAD TEST 01 — MAVERICKS

Extract NotesAccounts separately, then run Check Notes Accounts.command.
Send the diagnostic ZIP it creates and any visible error. You do not need to
quit your working Contacts or Calendar. No Notes app window should open.
Do not enter a password; this test has no sign-in interface.

This checks that the restored Notes framework and Google, Mail, and Notes
account plugins can load together on Mavericks before account setup is built.
It requests no account creation, note import, sync, or password operation.
The sandbox blocks network access, stock Notes/Mail/account/contact/calendar
stores, Keychain files, and preference writes. Private account writes are also
blocked for this load-only test. No helper or login job is installed.

A passing result should include NOTES_FRAMEWORK_LOADED, all three plugins
FOUND, SYSTEM_ACCOUNT_OR_PLUGIN_IMAGES=0, and Probe exit status: 0.
A failure is useful too: send its ZIP so the dependency can be fixed.
The diagnostic contains loaded library paths and errors, not note databases
or Keychains. The existing restored apps are unchanged.
''')
# Verify every local loader path resolves before distributing.
missing=[]
for p in machos:
 for line in run('otool','-L',p).splitlines()[1:]:
  dep=line.strip().split(' (')[0]
  if dep.startswith('@loader_path/') and not (p.parent/dep[len('@loader_path/'):]).exists():missing.append([str(p),dep])
assert not missing,missing
def inventory(root):
 return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_symlink() or p.is_file()}
(D/'manifest.json').write_text(json.dumps({'build':'Notes account load probe 01','runtime':'pending Mavericks laptop test','account_operations_requested':False,'network':'denied','dependency_redirects':edges,'files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name)
for b in (V/D.name/'Contents/Frameworks').glob('*.framework'):run('codesign','--verify','--deep','--strict',b)
(R/'reports/notes-account-probe01-validation.json').write_text(json.dumps({'archive':str(A),'roundtrip':'hashes, links, executable flags match','framework_and_plugin_signatures':'passed','local_dependencies':'all resolve','legacy_execution_on_host':False,'runtime':'pending Mavericks laptop test'},indent=2)+'\n')
print(A)
