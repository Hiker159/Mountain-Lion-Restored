"""Host the private InternetAccounts pane within the separately stored Notes app."""
from pathlib import Path
import subprocess,shutil,os,json,plistlib,hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/notes-private-accounts-01/NotesAccounts';A=R/'deliverables/Notes-Private-Accounts-Test-01.zip';V=R/'work/notes-private-accounts01-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*a):return subprocess.check_output([str(x) for x in a],text=True,stderr=subprocess.STDOUT)
shutil.copytree(R/'builds/notes-private-storage-01/NotesPrivate',D,symlinks=True)
APP=D/'Mountain Lion Notes.app';F=APP/'Contents/Frameworks'
P=APP/'Contents/PrivatePanes/InternetAccounts.prefPane';P.parent.mkdir()
shutil.copytree(R/'work/account-plugin-assets/System/Library/PreferencePanes/InternetAccounts.prefPane',P,symlinks=True)
mapping={}
for frame in F.glob('*.framework'):
 for v in (frame/'Versions').iterdir():
  if not v.is_symlink() and (v/frame.stem).is_file():
   for area in ['Frameworks','PrivateFrameworks']:mapping[f'/System/Library/{area}/{frame.name}/Versions/{v.name}/{frame.stem}']=v/frame.stem
mapping['/System/Library/Frameworks/Security.framework/Versions/A/Security']=F/'MLAccountSecurity.dylib'
edges=[]
for p in P.rglob('*'):
 if p.is_symlink() or not p.is_file():continue
 data=p.read_bytes()
 if data[:4] in [b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe']:
  if run('lipo','-archs',p).split()!=['x86_64']:
   tmp=p.with_name(p.name+'.thin');run('lipo',p,'-thin','x86_64','-output',tmp);os.replace(tmp,p)
  data=p.read_bytes().replace(b'com.apple.Notes',b'org.ntest.Notes').replace(b'com.apple.mail',b'org.ntest.mail');p.write_bytes(data)
  args=['install_name_tool']
  for l in run('otool','-L',p).splitlines()[1:]:
   dep=l.strip().split(' (')[0]
   if dep in mapping:
    new='@loader_path/'+os.path.relpath(mapping[dep],p.parent);args+=['-change',dep,new];edges.append([str(p.relative_to(APP)),dep,new])
  if len(args)>1:run(*args,p)
# Own pane identifier; executable filename retained.
p=P/'Contents/Info.plist';v=plistlib.loads(p.read_bytes());v['CFBundleIdentifier']='org.ntest.preferences.internetaccounts';p.write_bytes(plistlib.dumps(v))
lib=F/'MLNotesAccountsUI.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Cocoa','-Wl,-install_name,@rpath/MLNotesAccountsUI.dylib','-o',lib,R/'notes_account_ui.m')
for target in [P,lib,APP]:run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',target)
run('codesign','--verify','--deep','--strict',APP)
s=(D/'notes-private.sb').read_text().replace('(deny network*)\n','').replace('(subpath (param "KEYCHAINS")) ','');(D/'notes-private.sb').write_text(s)
p=D/'Open Private Notes.command';s=p.read_text().replace('MLNotesStorage.dylib"','MLNotesStorage.dylib:$APP/Contents/Frameworks/MLNotesAccountsUI.dylib"').replace('This first app test is local only.','Use Notes > Accounts to set up Google.');p.write_text(s)
(D/'READ ME FIRST.txt').write_text('''PRIVATE NOTES ACCOUNTS TEST 01 — MAVERICKS

Quit the restored Notes test, extract this package separately, and run
Open Private Notes.command. It uses the same private notes from Storage
Test 01. Open Notes > Accounts… to show the bundled account panel.

Try adding Google using your full email and existing app password. Select
only Notes if a service selection appears (leave Mail and other apps off).
Grant Keychain access to this test app if prompted. Passwords belong only in
the account panel; do not send them or include them in screenshots/logs.
If the panel fails to appear or crashes, collect the log without signing in.

Wait for Google notes to appear. This uses Gmail's Notes folder, not Keep.
Quit and reopen with the launcher to check account/password persistence.
If downloads work, create one disposable note in the Google account and
check your stock/other Mac Notes app. Leave existing real notes unchanged
for this first sync test. Run Collect Private Notes Log.command and send
its ZIP along with what worked or failed.

App: org.ntest.Notes. Notes stay in the private ML Private Notes folder;
accounts stay in ~/Library/ML Notes Accounts/V1. Credential operations use
org.ntest.RestoredApps/ namespacing via the tested Security wrapper. Stock
Notes/Mail/account/contact/calendar stores remain blocked. Network and
private credential access are enabled for this test. No login helper is
installed. Working Calendar/Contacts packages are unchanged. iCloud is not
part of this test. The account panel and Google Notes sync remain unverified
until tested on your Mavericks laptop.
''')
for p in D.glob('*.command'):run('bash','-n',p)
def inventory(root):return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_symlink() or p.is_file()}
(D/'manifest.json').unlink();(D/'manifest.json').write_text(json.dumps({'build':'Notes private accounts 01','runtime':'pending Mavericks test','account_panel':'Private InternetAccounts.prefPane hosted inside Notes','private_pane_redirects':edges,'files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name);run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/notes-accounts01-validation.json').write_text(json.dumps({'archive':str(A),'signatures':'passed after extraction','roundtrip':'hashes, links, modes match','shell_syntax':'passed','legacy_execution_on_host':False,'runtime':'pending'},indent=2)+'\n');print(A)
