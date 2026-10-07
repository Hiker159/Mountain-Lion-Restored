"""Consolidate tested artifacts without rebuilding apps or touching user data."""
from pathlib import Path
import hashlib,json,subprocess,shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/restored-apps-preview-02'
A=R/'deliverables/Mountain-Lion-Restored-Apps-Preview-02.zip'
V=R/'work/preview-02-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved.')
def run(*args):subprocess.run([str(a) for a in args],check=True)
def inventory(root):
 result={}
 for p in sorted(root.rglob('*')):
  key=str(p.relative_to(root))
  if p.is_symlink():result[key]={'link':str(p.readlink())}
  elif p.is_file():result[key]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}
 return result
run('ditto',R/'builds/restored-apps-preview-01',D)
run('ditto',R/'builds/birthday-bridge-test-06/Birthdays',D/'Birthdays')
shutil.copy2(R/'preview-02-readme.txt',D/'READ ME FIRST.txt')
p=D/'Birthdays/READ ME FIRST.txt'
s=p.read_text().replace('inside the existing restored-apps-preview-01 folder.','inside the existing restored-apps package folder.')
s=s.replace('17 local parser/planning/guard/workflow tests passed. Calendar scripts compile\non the build host. Calendar scripting on Mavericks remains unverified.',
'''17 local parser/planning/guard/workflow tests passed. The user subsequently
confirmed birthday creation, repeat import, updates, removal and persistence
on Mavericks. These checks are reported success, not exhaustive coverage.''')
p.write_text(s)
m=json.loads((D/'Birthdays/bridge-manifest.json').read_text())
m['runtime_status']='User confirmed import/repeat/update/remove/reopen checks passed'
m['files_sha256']['READ ME FIRST.txt']=hashlib.sha256(p.read_bytes()).hexdigest()
(D/'Birthdays/bridge-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
for name in ('Notes','Contacts','Calendar'):
 assert inventory(D/name)==inventory(R/'builds/restored-apps-preview-01'/name)
apps=[D/n/('Mountain Lion '+n+'.app') for n in ('Notes','Contacts','Calendar')]+[D/'Birthdays/Birthday Bridge.app']
for app in apps:run('codesign','--verify','--deep','--strict',app)
for p in D.rglob('*.command'):run('bash','-n',p)
(D/'package-manifest.json').unlink()
manifest={'package':'Preview 02','components':['Notes 05','Contacts 09','Calendar 10','Birthday Bridge 06'],
 'status':'Consolidation of user-tested components; package-path upgrade not yet laptop-tested',
 'validation':['App folders identical to Preview 01','Four deep strict app signatures passed','Shell syntax passed'],
 'files':inventory(D)}
(D/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A)
run('ditto','-x','-k',A,V)
assert inventory(D)==inventory(V/D.name)
for app in apps:run('codesign','--verify','--deep','--strict',V/D.name/app.relative_to(D))
report={'archive':str(A),'sha256':hashlib.sha256(A.read_bytes()).hexdigest(),'archive_roundtrip':'all file hashes, symlink targets and executable flags match','signatures':'all four pass after extraction','components':'unchanged app code','user_validation':'birthday full sequence reported passed'}
(R/'reports/preview-02-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(A)
