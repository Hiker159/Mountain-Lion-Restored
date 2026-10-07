from pathlib import Path
import shutil,subprocess,json,hashlib,os,zipfile,stat,plistlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/account-backend-probe-01/AccountBackend';F=D/'Frameworks'
D.mkdir(parents=True,exist_ok=True)
shutil.copytree(R/'builds/calendar-network-test-01/CalendarNetwork/Mountain Lion Calendar.app/Contents/Frameworks',F,symlinks=True,dirs_exist_ok=True)
names=['CalDAV','CoreDAV','iCalendar','InternetAccounts','AOSKit','AOSMigrate','ISSupport','ApplePushService']
def run(*a):
 p=subprocess.run([str(x) for x in a],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
for name in names:
 source=R/'originals/System/Library/PrivateFrameworks'/(name+'.framework')
 shutil.copytree(source,F/source.name,symlinks=True,dirs_exist_ok=True)
 if name=='ApplePushService':
  for helper in ('apsd','apsctl'):
   target=F/source.name/helper
   if target.exists():target.unlink()
# Match each original absolute install name to its bundled canonical version.
mapping={}
for frame in F.glob('*.framework'):
 versions=[v for v in (frame/'Versions').iterdir() if not v.is_symlink() and (v/frame.stem).is_file()]
 if len(versions)!=1:continue
 binary=versions[0]/frame.stem
 info=versions[0]/'Resources/Info.plist'
 if not info.exists():
  info.parent.mkdir(parents=True,exist_ok=True)
  info.write_bytes(plistlib.dumps({'CFBundleExecutable':frame.stem,'CFBundleIdentifier':'org.local.AccountProbe.'+frame.stem,'CFBundlePackageType':'FMWK','CFBundleVersion':'1'}))
 for area in ['Frameworks','PrivateFrameworks']:
  original=R/'originals/System/Library'/area/frame.name/'Versions'/versions[0].name/frame.stem
  if original.exists():mapping['/'+str(original.relative_to(R/'originals'))]=binary
modified=[];edges=[]
for p in F.rglob('*'):
 if not p.is_file() or p.is_symlink():continue
 data=p.read_bytes()
 if data[:4] not in (b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xca\xfe\xba\xbe'):continue
 arches=run('lipo','-archs',p).split()
 if arches!=['x86_64']:
  tmp=p.with_name(p.name+'.thin');run('lipo',p,'-thin','x86_64','-output',tmp);os.replace(tmp,p)
 deps=run('otool','-L',p);args=['install_name_tool']
 for old,new in mapping.items():
  if old in deps:
   private='@loader_path/'+os.path.relpath(new,p.parent);args+=['-change',old,private];edges.append({'binary':str(p.relative_to(D)),'original':old,'private':private})
 if p in mapping.values():args+=['-id','@rpath/'+str(p.relative_to(F))]
 if len(args)>1:run(*args,p)
 run('codesign','--remove-signature',p);modified.append(p)
# Probe is a standalone CLI, not an account daemon or a replacement system service.
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-Werror','-Wl,-no_fixup_chains','-o',D/'AccountBackendProbe',R/'account_backend_probe.c')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1',D/'AccountBackendProbe')
for p in modified:
 if p.parent.name!='MacOS' and p not in mapping.values():run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',p)
suffixes=('.framework','.bundle','.app','.xpc','.sourcebundle','.syncschema')
bundles={parent for p in modified for parent in p.parents if F in parent.parents and parent.suffix in suffixes}
for p in sorted(bundles,key=lambda x:len(x.parts),reverse=True):run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',p)
for name in names:run('codesign','--verify','--deep','--strict',F/(name+'.framework'))
(R/'reports/account-backend-private-dependencies.json').write_text(json.dumps({'private_frameworks':names,'redirected_edges':edges,'system_services_and_plugin_paths':'not redirected; probe makes no account API calls'},indent=2)+'\n')
print('Private backend probe built:',D)
