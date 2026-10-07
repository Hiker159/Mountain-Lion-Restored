from pathlib import Path
import subprocess,shutil,os,json,hashlib,zipfile,stat,plistlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/account-plugin-probe-01/AccountBackend';F=D/'Frameworks'
def run(*a):
 p=subprocess.run([str(x) for x in a],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
if D.exists():raise RuntimeError('Build destination exists')
shutil.copytree(R/'builds/account-storage-probe-02/AccountBackend',D,symlinks=True)
P=D/'AccountPlugins';P.mkdir()
mapping={}
for frame in F.glob('*.framework'):
 for v in (frame/'Versions').iterdir():
  if v.is_symlink() or not (v/frame.stem).is_file():continue
  for area in ['Frameworks','PrivateFrameworks']:
   mapping[f'/System/Library/{area}/{frame.name}/Versions/{v.name}/{frame.stem}']=v/frame.stem
edges=[]
for name in ['Google','Calendar']:
 bundle=P/(name+'.iaplugin')
 shutil.copytree(R/'work/account-plugin-assets/System/Library/InternetAccounts'/bundle.name,bundle,symlinks=True)
 i=plistlib.loads((bundle/'Contents/Info.plist').read_bytes());b=bundle/'Contents/MacOS'/i['CFBundleExecutable']
 if run('lipo','-archs',b).split()!=['x86_64']:
  temp=b.with_name(b.name+'.thin');run('lipo',b,'-thin','x86_64','-output',temp);os.replace(temp,b)
 deps=[l.strip().split(' (')[0] for l in run('otool','-L',b).splitlines()[1:]]
 args=['install_name_tool']
 for dep in deps:
  if dep in mapping:
   new='@loader_path/'+os.path.relpath(mapping[dep],b.parent);args+=['-change',dep,new];edges.append({'plugin':name,'old':dep,'new':new})
 run(*args,b)
 run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',bundle)
 run('codesign','--verify','--deep','--strict',bundle)
 assert not any(x in run('otool','-L',b) for x in mapping),name
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-Wl,-install_name,@rpath/MLAccountPluginRouting.dylib','-o',F/'MLAccountPluginRouting.dylib',R/'account_plugin_routing.m')
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-o',D/'AccountPluginProbe',R/'account_plugin_probe.m')
for p in [F/'MLAccountPluginRouting.dylib',D/'AccountPluginProbe']:
 run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1',p);run('codesign','--verify','--strict',p)
launcher=D/'Check Account Backend.command';s=launcher.read_text()
start=s.index('/bin/cat "$OUT/backend.log"')
addition='''/usr/bin/sandbox-exec \\
 -D "HOME_ACCOUNTS=$HOME/Library/Accounts" \\
 -D "HOME_INET_ACCOUNTS=$HOME/Library/Internet Accounts" \\
 -D "HOME_KEYCHAINS=$HOME/Library/Keychains" \\
 -D "HOME_CALENDARS=$HOME/Library/Calendars" \\
 -D "HOME_ADDRESSBOOK=$HOME/Library/Application Support/AddressBook" \\
 -f "$HERE/backend-probe.sb" "$HERE/AccountPluginProbe" \\
 "$F/InternetAccounts.framework/Versions/A/InternetAccounts" \\
 "$F/MLAccountPluginRouting.dylib" "$HERE/AccountPlugins" >> "$OUT/backend.log" 2>&1
PLUGIN_RESULT=$?
echo "Plugin probe exit status: $PLUGIN_RESULT" >> "$OUT/backend.log"
if [ "$PLUGIN_RESULT" != 0 ]; then RESULT=$PLUGIN_RESULT; fi
'''
launcher.write_text(s[:start]+addition+s[start:]);run('bash','-n',launcher)
(D/'READ ME FIRST.txt').write_text('''PRIVATE ACCOUNT PLUGIN PROBE 01

Extract AccountBackend separately on Mavericks. Keep CalendarNetwork and
background GoogleSync stopped. Run Check Account Backend.command and send
the resulting Account-backend ZIP. No password or sign-in is needed.

Repeats the passing library and private storage-path checks, then installs
routing for this process and asks IAPluginManager for the Google and Calendar
plugins. All other plugin paths are excluded. Both plugins use private bundled
account/calendar/contact dependencies. Expected: both PLUGIN lines FOUND,
SYSTEM_ACCOUNT_OR_PLUGIN_IMAGES=0, plugin probe exit status 0.

The probe requests no account creation, password operation, network discovery
or sync, and launches no Calendar/preference pane or account daemon. Plugin
initializers may attempt shared APIs; sandbox restrictions remain active.
No account contents or credentials are intentionally collected. Diagnostics
include library paths and exception names, not password values or account data.

Credential isolation is still under development and is NOT enabled here.
Do not use these frameworks or plugins to sign in. Plugin IDs are unchanged
for the private framework's lookup table; no plugin is installed system-wide.
Routing lasts only for the probe process. Passing means plugin loading works,
not that accounts authenticate, persist, or sync.

Compiled for x86_64 Mavericks 10.9. Original method signatures were checked;
routing verifies signatures at runtime before replacing implementations.
Dependencies, signatures, shell syntax, archive hashes/modes/symlinks checked.
Legacy code has not been executed on the modern build host.
''')
(R/'reports/account-plugin-probe01-dependencies.json').write_text(json.dumps({'redirected_edges':edges,'routing_methods':{'_loadPluginAtPath:identifiers:':'v32@0:8@16@24','createIAPluginAtPath:':'@24@0:8@16'},'credential_wrapper':'compiled separately but not installed; CalendarStore has additional SecItem/internet-password paths'},indent=2)+'\n')
manifest={'build':'account-plugin-probe-01','runtime':'pending Mavericks plugin loading test','files_sha256':{str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in D.rglob('*') if p.is_file() and not p.is_symlink() and p.name!='manifest.json'}}
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
zpath=R/'deliverables/Private-Account-Plugin-Probe-01.zip'
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
print(str(zpath));print('Private dependency redirects:',len(edges))
