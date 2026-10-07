from pathlib import Path
import subprocess,shutil,hashlib,json,struct,importlib.util
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/restored-apps-shared-experimental-01'
def run(*args):return subprocess.check_output([str(x) for x in args],stderr=subprocess.STDOUT)
shutil.copy2(R/'shared-experimental-readme.txt',D/'READ ME FIRST.txt')
p=D/'Collect Shared Test Logs.command';shutil.copy2(R/'shared-experimental-collector.command',p);p.chmod(0o755)
for p in D.rglob('*.command'):run('bash','-n',p)
for name in ['Notes','Contacts','Calendar']:run('codesign','--verify','--deep','--strict',D/name/('Mountain Lion '+name+'.app'))
contacts=D/'Contacts/Mountain Lion Contacts.app/Contents/Frameworks/AddressBook.framework/Versions/A/AddressBook'
data=contacts.read_bytes();pointer,length=struct.unpack_from('<QQ',data,0x37f580+16);assert data[pointer:pointer+length]==b'AddressBook'
assert b'\0ABAlternateDataStoreDirectory\0' in data and b'\0MLAlternateDataStoreDirectory\0' not in data
cal=D/'Calendar/Mountain Lion Calendar.app/Contents/Frameworks/CalendarStore.framework/Versions/A/CalendarStore'
data=cal.read_bytes();assert b'\0CalendarsDirectory\0' in data and b'\0MLCalDataDirectory\0' not in data
assert b'%@/Library/Calendars\0' in data and b'org.share' in data
spec=importlib.util.spec_from_file_location('shared_control',D/'Calendar/calendar_agent_control.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
job,args,paths=module.make_job(str(D/'Calendar'),'/Users/Disposable')
assert job['Label']=='org.share.CalendarAgent'
assert paths['data']=='/Users/Disposable/Library/Calendars'
assert paths['support']=='/Users/Disposable/Library/Application Support/iCal'
assert 'ML-Shared-Experiment/Agent' in paths['state']
assert '-CalendarsDirectory' in job['ProgramArguments']
run('python3',R/'check_wake_extension.py',D/'Calendar/Mountain Lion Calendar.app/Contents/Frameworks/MLCalendarWakeRecovery.dylib')
# Avoid shipping Python bytecode created by this offline controller check.
cache=D/'Calendar/__pycache__'
if cache.exists():shutil.rmtree(cache)
def inventory(root):
 return {str(p.relative_to(root)):({'symlink':str(p.readlink())} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
assert inventory(D/'Notes/Mountain Lion Notes.app')==inventory(R/'builds/restored-apps-preview-03/Notes/Mountain Lion Notes.app')
a=R/'deliverables/Restored-Apps-Shared-Database-Experiment-01.zip'
run('ditto','-c','-k','--keepParent',D,a)
v=R/'work/shared-store-archive-verification';run('ditto','-x','-k',a,v)
assert inventory(D)==inventory(v/D.name)
for name in ['Notes','Contacts','Calendar']:run('codesign','--verify','--deep','--strict',v/D.name/name/('Mountain Lion '+name+'.app'))
report={'archive':str(a),'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'validation':['stock Contacts default directory and keys checked','stock Calendar directory and key checked','separate experimental helper identity and stock data/support paths checked','click extension imports available on Mavericks','Notes byte-identical to Preview 03','shell syntax and three deep signatures passed','ZIP contents/symlinks/executable flags and extracted signatures verified'],'runtime_status':'Unverified on Mavericks; disposable account only'}
(R/'reports/shared-store-experiment-01-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(a)
