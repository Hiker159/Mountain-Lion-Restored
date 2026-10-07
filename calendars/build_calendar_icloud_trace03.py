"""Build an isolated provider-options trial from the tested Calendar package; never run legacy code."""
from pathlib import Path
import os, shutil, subprocess, plistlib, hashlib, json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/calendar-provider-options-03/CalendarAccounts'
APP=D/'Mountain Lion Calendar.app'; F=APP/'Contents/Frameworks'
def run(*args):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr or p.stdout)
    return p.stdout
if D.exists(): raise RuntimeError('Destination already exists')
shutil.copytree(R/'builds/restored-apps-preview-06/Calendar',D,symlinks=True)
new=[]
for name in ('Yahoo','Exchange'):
    dest=APP/'Contents/AccountPlugins'/f'{name}.iaplugin'
    shutil.copytree(R/'work/calendar-provider-assets/System/Library/InternetAccounts'/dest.name,dest,symlinks=True)
    new.append(dest)
dest=F/'ExchangeWebServices.framework'
shutil.copytree(R/'originals/System/Library/PrivateFrameworks'/dest.name,dest,symlinks=True);new.append(dest)
for area,name in (('Frameworks','ServerNotification'),('PrivateFrameworks','AOSNotification')):
    dest=F/(name+'.framework')
    shutil.copytree(R/'originals/System/Library'/area/dest.name,dest,symlinks=True);new.append(dest)
# Installer-era loose resources must live inside the sealed version resources.
for frame in new:
    if frame.suffix!='.framework':continue
    for p in list(frame.iterdir()):
        if p.is_file() and not p.is_symlink():
            target=frame/'Versions/A/Resources'/p.name
            assert not target.exists(),target
            target.parent.mkdir(parents=True,exist_ok=True)
            p.rename(target)
mapping={}
for frame in F.glob('*.framework'):
    for v in (frame/'Versions').iterdir():
        if v.is_symlink() or not (v/frame.stem).is_file(): continue
        for area in ('Frameworks','PrivateFrameworks'):
            mapping[f'/System/Library/{area}/{frame.name}/Versions/{v.name}/{frame.stem}']=v/frame.stem
mapping['/System/Library/Frameworks/Security.framework/Versions/A/Security']=F/'MLAccountSecurity.dylib'
modified=[];edges=[]
for root in [APP]:
    for p in root.rglob('*'):
        if not p.is_file() or p.is_symlink(): continue
        data=p.read_bytes()
        if data[:4] in (b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe'):
            if run('lipo','-archs',p).split()!=['x86_64']:
                temp=p.with_name(p.name+'.thin');run('lipo',p,'-thin','x86_64','-output',temp);os.replace(temp,p)
            p.write_bytes(p.read_bytes().replace(b'com.apple.iCal',b'org.authx.iCal'))
            args=['install_name_tool']
            for dep in [l.strip().split(' (')[0] for l in run('otool','-L',p).splitlines()[1:]]:
                if dep in mapping and not (p.name=='MLAccountSecurity.dylib' or (p.name=='DataDetectors' and '/Security.framework/' in dep)):
                    target='@loader_path/'+os.path.relpath(mapping[dep],p.parent)
                    args+=['-change',dep,target];edges.append({'binary':str(p.relative_to(APP)),'original':dep,'private':target})
            if len(args)>1:run(*args,p)
            modified.append(p)
        elif p.suffix=='.plist':
            try:info=plistlib.loads(data)
            except Exception:continue
            def rewrite(x):
                if isinstance(x,str):return x.replace('com.apple.iCal','org.authx.iCal')
                if isinstance(x,list):return [rewrite(v) for v in x]
                if isinstance(x,dict):return {k:rewrite(v) for k,v in x.items()}
                return x
            p.write_bytes(plistlib.dumps(rewrite(info)))
bootstrap=F/'MLAccountBootstrap.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-Wl,-install_name,@rpath/MLAccountBootstrap.dylib','-o',bootstrap,R/'account_icloud_trace.m');modified.append(bootstrap)
# Re-sign changed executable leaves and enclosing bundles, keeping entitlements.
suffixes={'.framework','.app','.xpc','.bundle','.iaplugin','.sourcebundle','.syncschema','.docktileplugin','.sharingservice','.webplugin'}
bundles=set()
for p in modified:
    owners=[a for a in p.parents if a==APP or (APP in a.parents and a.suffix in suffixes)];bundles.update(owners)
    main=p.parent.name=='MacOS' or any(a.suffix=='.framework' and p.name==a.stem for a in owners)
    if not main:run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',p)
for b in sorted(bundles,key=lambda p:len(p.parts),reverse=True):
    run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',b)
run('codesign','--verify','--deep','--strict',APP)
# Every relative import must resolve inside this package.
checked=0
for p in APP.rglob('*'):
    if not p.is_file() or p.is_symlink() or p.read_bytes()[:4] not in (b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe'):continue
    for dep in [l.strip().split(' (')[0] for l in run('otool','-L',p).splitlines()[1:]]:
        if dep in mapping and mapping[dep].resolve()!=p.resolve() and not (p.name=='MLAccountSecurity.dylib' or (p.name=='DataDetectors' and '/Security.framework/' in dep)):
            raise AssertionError(('Unredirected private framework',p,dep))
        if dep.startswith('@loader_path/'):
            target=(p.parent/dep[len('@loader_path/'):]).resolve()
            assert target.is_file() and APP.resolve() in target.parents,(p,dep)
            checked+=1
(D/'READ ME FIRST.txt').write_text('''CALENDAR ACCOUNT OPTIONS — ICLOUD TRACE 03

This adds the original Mountain Lion Yahoo and Exchange account providers beside Google and generic CalDAV. Google is tested; the added providers are not yet tested on Mavericks. A provider appearing in the wizard does not guarantee that its server still accepts the legacy authentication method.

1. In your previous Calendar package, run Disable Calendar Alerts at Login.command and Stop Calendar Helper.command, then quit restored Calendar.
2. Extract this package to a permanent location and run Open Calendar.command. It uses the existing private Calendar data and accounts, so do not delete or reset them.
3. Open Calendar > Preferences > Accounts and click +. Check which account types appear. For a generic CalDAV service, use its provider's documented server settings. Select Calendars only when offered other services.
4. Test downloading events, creating and editing a temporary event, then quitting and reopening. Run Collect Account Setup Log.command and send the resulting archive with the provider name and what worked.
5. Leave login alerts disabled until the provider test passes. The existing alert helper is unchanged.

Full iCloud and OS X Server setup are not enabled in this trial; they require additional system services. Manual CalDAV may be usable with iCloud, but is untested. Exchange is the legacy EWS provider, not a modern Microsoft 365 OAuth implementation.

The stock accounts and Calendar databases remain protected by the existing sandbox. This is not a separate System Preferences pane. Credentials still use the private Keychain namespace and may trigger access prompts. Do not include passwords in your report.

To return to the tested build: stop this helper, quit the app, then use your Preview06 launcher. Any newly added private accounts remain; remove unwanted trial accounts through Calendar's preferences.
''')
archive=R/'deliverables/Calendar-iCloud-Trace-Test-03.zip'
run('ditto','-c','-k','--sequesterRsrc','--keepParent',D,archive)
verify=R/'work/calendar-provider-options-03-verify';verify.mkdir()
run('ditto','-x','-k',archive,verify)
restored=verify/D.name
run('codesign','--verify','--deep','--strict',restored/APP.name)
def inventory(root):
    result={}
    for p in root.rglob('*'):
        if p.is_symlink():result[str(p.relative_to(root))]=['link',os.readlink(p)]
        elif p.is_file():result[str(p.relative_to(root))]=['file',hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode&0o777]
    return result
assert inventory(D)==inventory(restored)
report={'archive':archive.name,'added_providers':['Yahoo','Exchange'],'deferred_providers':['iCloud','OSXServer'],'relative_imports_checked':checked,'rewritten_imports':edges,'signature_verification':'passed before and after archive extraction','archive_inventory':'identical','runtime_test':'pending on Mavericks'}
(R/'reports/calendar-provider-options-03.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='rewritten_imports'},indent=2))
