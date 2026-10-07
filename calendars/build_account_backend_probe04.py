from pathlib import Path
import shutil, subprocess, os, hashlib, json, zipfile, stat, collections
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/account-backend-probe-04/AccountBackend';F=D/'Frameworks'
def run(*args):
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
if D.exists():raise RuntimeError('Build destination already exists')
shutil.copytree(R/'builds/account-backend-probe-03/AccountBackend',D,symlinks=True)
shutil.copytree(R/'originals/System/Library/PrivateFrameworks/WhitePages.framework',F/'WhitePages.framework',symlinks=True)
mapping={}
for frame in F.glob('*.framework'):
 for v in (frame/'Versions').iterdir():
  if v.is_symlink() or not (v/frame.stem).is_file():continue
  for area in ['Frameworks','PrivateFrameworks']:
   mapping[f'/System/Library/{area}/{frame.name}/Versions/{v.name}/{frame.stem}']=v/frame.stem
changed=[];edges=[]
for p in F.rglob('*'):
 if p.is_symlink() or not p.is_file():continue
 if p.read_bytes()[:4] not in (b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xca\xfe\xba\xbe'):continue
 dirty=False
 if run('lipo','-archs',p).split()!=['x86_64']:
  temp=p.with_name(p.name+'.thin');run('lipo',p,'-thin','x86_64','-output',temp);os.replace(temp,p);dirty=True
 deps=[l.strip().split(' (')[0] for l in run('otool','-L',p).splitlines()[1:]]
 args=['install_name_tool']
 for dep in deps:
  if dep in mapping:
   new='@loader_path/'+os.path.relpath(mapping[dep],p.parent)
   args+=['-change',dep,new];edges.append({'binary':str(p.relative_to(D)),'old':dep,'new':new})
 if p.name=='WhitePages':args+=['-id','@rpath/WhitePages.framework/Versions/A/WhitePages']
 if len(args)>1:run(*args,p);dirty=True
 if dirty:changed.append(p)
for p in changed:
 frame=next(a for a in p.parents if a.suffix=='.framework')
 run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',frame)
for frame in F.glob('*.framework'):run('codesign','--verify','--deep','--strict',frame)
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-Werror','-Wl,-no_fixup_chains','-o',D/'AccountBackendProbe',R/'account_backend_probe.c')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1',D/'AccountBackendProbe')
run('codesign','--verify','--strict',D/'AccountBackendProbe')
run('bash','-n',D/'Check Account Backend.command')
# Follow private imports and extracted Mavericks imports without executing libraries.
q=collections.deque([(F/'AOSAccounts.framework/Versions/A/AOSAccounts',[])])
seen=set();hits=[];missing=[]
while q:
 p,chain=q.popleft();p=p.resolve()
 if p in seen:continue
 if not p.exists():missing.append(str(p));continue
 seen.add(p);chain=chain+[str(p.relative_to(R))]
 for l in run('otool','-L',p).splitlines()[1:]:
  dep=l.strip().split(' (')[0]
  if dep.startswith('@loader_path/'):n=p.parent/dep[len('@loader_path/'):]
  elif dep.startswith('/System/Library/'):n=R/'mavericks-originals'/dep[1:]
  else:continue
  if n.resolve()==p:continue
  if 'mavericks-originals' in n.parts and any('/'+x+'.framework/' in str(n) for x in ['InternetAccounts','AOSKit','ISSupport','AddressBook','CalendarStore','CalendarPersistence']):hits.append(chain+[str(n.relative_to(R))]);continue
  q.append((n,chain))
report={'build':'04','visited':len(seen),'system_stack_reentry':hits,'unavailable_extracted_dependencies':sorted(set(missing)),'rewritten_edges':edges,'limitation':'Static imports only; runtime dynamic loads require laptop probe'}
(R/'reports/account-backend-probe04-dependencies.json').write_text(json.dumps(report,indent=2)+'\n')
assert not hits,hits
readme=D/'READ ME FIRST.txt'
s=readme.read_text().replace('PRIVATE ACCOUNT BACKEND PROBE 03','PRIVATE ACCOUNT BACKEND PROBE 04').replace('AOSKit has Apple service dependencies, and Google requires supported OAuth.','AOSKit has Apple service dependencies. Google authentication, including this\nuser\'s working Mavericks app password, still requires a separate local test.')
s+='\nPROBE 04 — WHITEPAGES DEPENDENCY\nCalendarStore also loaded system WhitePages, which loaded system AddressBook\nand the account stack. WhitePages is now bundled privately and its AddressBook\nimport redirected. The static graph has no observed native account/calendar\nstack reentry. Dynamic loading still needs Mavericks verification. The log\nnow lists every loaded image to help trace any remaining collisions.\nRun Check Account Backend.command and send the resulting ZIP. No password\nor account changes are needed.\n'
readme.write_text(s)
manifest={'build':'account-backend-probe-04','change':'Private WhitePages closes second observed AddressBook reentry; full image inventory','runtime':'Mavericks isolated-load retest pending','files_sha256':{str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(D.rglob('*')) if p.is_file() and not p.is_symlink() and p.name!='manifest.json'}}
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
zpath=R/'deliverables/Private-Account-Backend-Probe-04.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  name='AccountBackend/'+str(p.relative_to(D))
  if p.is_symlink():
   info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,os.readlink(p))
  elif p.is_file():z.write(p,name)
with zipfile.ZipFile(zpath) as z:
 for rel,h in manifest['files_sha256'].items():assert hashlib.sha256(z.read('AccountBackend/'+rel)).hexdigest()==h
 for p in D.rglob('*'):
  name='AccountBackend/'+str(p.relative_to(D))
  if p.is_symlink():assert z.read(name).decode()==os.readlink(p)
  elif p.is_file():assert ((z.getinfo(name).external_attr>>16)&0o111)==(p.stat().st_mode&0o111)
print(json.dumps({'archive':str(zpath),'changed_binaries':len(changed),'static_reentry_paths':len(hits),'visited':len(seen),'unavailable_extracted_dependencies':len(set(missing))}))
