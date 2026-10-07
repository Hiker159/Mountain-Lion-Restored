from pathlib import Path
import shutil,subprocess,os,plistlib,json,hashlib,zipfile,stat,re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/calendar-private-accounts-02/CalendarAccounts'
APP=D/'Mountain Lion Calendar.app';F=APP/'Contents/Frameworks'
def run(*a):
 p=subprocess.run([str(x) for x in a],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
if D.exists():raise RuntimeError('Build destination exists')
shutil.copytree(R/'builds/calendar-network-test-01/CalendarNetwork',D,symlinks=True)
shutil.rmtree(F)
S=R/'builds/account-security-probe-01/AccountBackend'
shutil.copytree(S/'Frameworks',F,symlinks=True)
shutil.copytree(R/'originals/System/Library/PrivateFrameworks/Suggestions.framework',F/'Suggestions.framework',symlinks=True)
shutil.copytree(S/'AccountPlugins',APP/'Contents/AccountPlugins',symlinks=True)
shutil.copy2(R/'builds/account-credential-persistence-02/AccountCredentials/MLAccountSecurity.dylib',F/'MLAccountSecurity.dylib')
replacements=[(b'org.cloud',b'org.authx'),(b'org.local.InternetAccounts',b'org.authx.InternetAccounts'),(b'MLCalNetx',b'MLCalAuth'),(b'ML-CalCloud',b'ML-CalAuthx'),(b'com.apple.iCal',b'org.authx.iCal')]
assert all(len(a)==len(b) for a,b in replacements)
mapping={}
for frame in F.glob('*.framework'):
 for v in (frame/'Versions').iterdir():
  if v.is_symlink() or not (v/frame.stem).is_file():continue
  for area in ['Frameworks','PrivateFrameworks']:mapping[f'/System/Library/{area}/{frame.name}/Versions/{v.name}/{frame.stem}']=v/frame.stem
mapping['/System/Library/Frameworks/Security.framework/Versions/A/Security']=F/'MLAccountSecurity.dylib'
modified=[];edges=[]
for p in APP.rglob('*'):
 if not p.is_file() or p.is_symlink():continue
 data=p.read_bytes()
 if data[:4] in [b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe']:
  if run('lipo','-archs',p).split()!=['x86_64']:
   temp=p.with_name(p.name+'.thin');run('lipo',p,'-thin','x86_64','-output',temp);os.replace(temp,p)
  data=p.read_bytes()
  for old,new in replacements:data=data.replace(old,new)
  p.write_bytes(data)
  if p.name=='Suggestions':run('install_name_tool','-id','@rpath/Suggestions.framework/Versions/A/Suggestions',p)
  if p.name!='MLAccountSecurity.dylib':
   deps=[l.strip().split(' (')[0] for l in run('otool','-L',p).splitlines()[1:]];args=['install_name_tool']
   for dep in deps:
    if dep in mapping:
     new='@loader_path/'+os.path.relpath(mapping[dep],p.parent);args+=['-change',dep,new];edges.append({'binary':str(p.relative_to(APP)),'original':dep,'private':new})
   if len(args)>1:run(*args,p)
  modified.append(p)
 elif p.suffix=='.plist':
  try:i=plistlib.loads(data)
  except Exception:continue
  def change(v):
   if isinstance(v,str):
    for old,new in replacements:v=v.replace(old.decode(),new.decode())
   elif isinstance(v,list):v=[change(x) for x in v]
   elif isinstance(v,dict):v={change(k):change(x) for k,x in v.items()}
   return v
  p.write_bytes(plistlib.dumps(change(i)))
bootstrap=F/'MLAccountBootstrap.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-Wl,-install_name,@rpath/MLAccountBootstrap.dylib','-o',bootstrap,R/'account_app_bootstrap.m');modified.append(bootstrap)
# Sign executable leaves then every enclosing bundle from inner to outer.
suffixes={'.framework','.app','.xpc','.bundle','.iaplugin','.sourcebundle','.syncschema','.docktileplugin'}
bundles=set()
for p in modified:
 owners=[a for a in p.parents if a==APP or (APP in a.parents and a.suffix in suffixes)];bundles.update(owners)
 main=False
 if p.parent.name=='MacOS':main=True
 if any(a.suffix=='.framework' and p.name==a.stem for a in owners):main=True
 if not main:run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',p)
for b in sorted(bundles,key=lambda p:len(p.parts),reverse=True):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',b)
run('codesign','--verify','--deep','--strict',APP)
# Fresh app/helper/data namespaces; bootstrap precedes any account setup.
for name in ['calendar_agent_control.py','collect_network.py','Open Network Calendar.command']:
 p=D/name;s=p.read_text()
 for old,new in replacements[:4]:s=s.replace(old.decode(),new.decode())
 s=s.replace('ML Calendar Network Test','ML Calendar Private Accounts')
 if name=='calendar_agent_control.py':
  s=s.replace("'DYLD_INSERT_LIBRARIES='+wake_library", "'DYLD_INSERT_LIBRARIES='+wake_library+':'+os.path.join(p['app'],'Contents','Frameworks','MLAccountBootstrap.dylib')")
 if name=='Open Network Calendar.command':
  s=s.replace('"${SANDBOX[@]}" "$APP/Contents/MacOS/Calendar"','"${SANDBOX[@]}" /usr/bin/env "DYLD_INSERT_LIBRARIES=$APP/Contents/Frameworks/MLAccountBootstrap.dylib" "$APP/Contents/MacOS/Calendar"')
 p.write_text(s)
# Preserve parameters protecting the real stock Calendar; no replacement above on sandbox definitions.
for name in ['calendar-trial.sb','calendar-agent-trial.sb']:
 p=D/name;s=p.read_text();s+='\n(deny file-read* file-write* (subpath (param "STOCK_ACCOUNTS")) (subpath (param "STOCK_INET")))\n';p.write_text(s)
p=D/'Open Network Calendar.command';s=p.read_text().replace('  -f "$HERE/calendar-trial.sb")','  -D "STOCK_ACCOUNTS=$HOME/Library/Accounts"\n  -D "STOCK_INET=$HOME/Library/Internet Accounts"\n  -f "$HERE/calendar-trial.sb")');p.write_text(s);p.rename(D/'Open Private Accounts Calendar.command')
p=D/'calendar_agent_control.py';s=p.read_text().replace("      '-f',os.path.join(package,'calendar-agent-trial.sb')]", "      '-D','STOCK_ACCOUNTS='+os.path.join(home,'Library','Accounts'),\n      '-D','STOCK_INET='+os.path.join(home,'Library','Internet Accounts'),\n      '-f',os.path.join(package,'calendar-agent-trial.sb')]");p.write_text(s)
# Collector accepts bootstrap records and image-loading records; omit secret-bearing log lines.
p=D/'collect_network.py';s=p.read_text().replace('error|fail|CalDAV|account|sync|network|auth|denied|exception|crash','error|fail|CalDAV|account|sync|network|auth|denied|exception|crash|dyld: loaded')
s=s.replace('password|passwd|access', 'password|passwd|credential|bearer|access')
p.write_text(s)
p=D/'Collect Network Log.command';s=p.read_text().replace('Calendar-network-','Calendar-accounts-');p.write_text(s);p.rename(D/'Collect Account Setup Log.command')
for p in D.glob('*.command'):run('bash','-n',p)
for p in D.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
(D/'READ ME FIRST.txt').write_text('''PRIVATE CALENDAR ACCOUNTS TEST 02

Build 02 supplies private Mountain Lion Suggestions, which otherwise loaded
stock InternetAccounts and AddressBook when Calendar started.

Use on Mavericks. Extract separately. Stop CalendarNetwork and GoogleSync,
and quit the usual restored Calendar. Run Open Private Accounts Calendar.command.
This app uses org.authx.iCal/org.authx.CalendarAgent, ~/Library/MLCalAuth and
~/Library/Application Support/ML-CalAuthx, separate from previous experiments.
Account storage is ~/Library/ML Cloud Accounts/V1. No login item is installed.

FIRST TEST: open the app and Preferences > Accounts, then collect the log.
Do not sign in yet. We need to verify that app/helper startup and the account
setup UI remain isolated before entering your Google app password. Send the
ZIP from Collect Account Setup Log.command, and report whether Accounts opens
and whether the account list is empty. Do not open macOS Internet Accounts.

The tested private frameworks and Google/Calendar plugins are integrated.
Bootstrap installs process-local plugin routing before account setup and
checks the private account-storage URL. Loading a stock account/calendar
framework or system account plugin stops the test process and logs its path.
Only Google and Calendar plugins are allowed. Security imports use the fixed
credential wrapper that passed the disposable Keychain persistence test.
Stock Calendar/contact/account stores remain protected by sandbox profiles.
Outbound networking is permitted for subsequent authentication tests.

This is experimental and not yet a functioning sync release. No account or
credential is needed for this first app integration check. Stop Calendar
Helper.command stops only this test helper; quit the test Calendar too.
Working restored apps and the stock Calendar remain separate.

Diagnostics filter credential-related lines and email addresses, exclude
account preferences/databases/Keychains, and include only selected own logs
and manifest. Review before sharing; never send an app password. Framework
signatures, redirects, Python/shell syntax and archive hashes/modes/symlinks
checked locally; actual app/helper initialization requires Mavericks.
''')
(R/'reports/calendar-private-accounts02-dependencies.json').write_text(json.dumps({'redirected_edges':edges,'credential_wrapper':'fixed ownership attribute query; dummy persistence test02 passed','phase':'UI/bootstrap verification before Google sign-in'},indent=2)+'\n')
manifest={'build':'calendar-private-accounts-02','runtime':'pending Mavericks UI/bootstrap test','files_sha256':{str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in D.rglob('*') if p.is_file() and not p.is_symlink() and p.name!='manifest.json'}}
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
zpath=R/'deliverables/Calendar-Private-Accounts-Test-02.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  n='CalendarAccounts/'+str(p.relative_to(D))
  if p.is_symlink():
   info=zipfile.ZipInfo(n);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,os.readlink(p))
  elif p.is_file():z.write(p,n)
with zipfile.ZipFile(zpath) as z:
 for rel,h in manifest['files_sha256'].items():assert hashlib.sha256(z.read('CalendarAccounts/'+rel)).hexdigest()==h
 for p in D.rglob('*'):
  n='CalendarAccounts/'+str(p.relative_to(D))
  if p.is_symlink():assert z.read(n).decode()==os.readlink(p)
  elif p.is_file():assert ((z.getinfo(n).external_attr>>16)&0o111)==(p.stat().st_mode&0o111)
print(zpath)
