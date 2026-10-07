from pathlib import Path
import subprocess,json,hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/calendar-click-test-03';A=D/'Calendar/Mountain Lion Calendar.app'
def run(*args):return subprocess.check_output([str(x) for x in args],stderr=subprocess.STDOUT)
if D.exists():raise SystemExit('Preserve existing trial')
run('ditto',R/'builds/calendar-click-test-02/Calendar',D/'Calendar')
lib=A/'Contents/Frameworks/MLCalendarWakeRecovery.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-fblocks','-Werror','-Wno-deprecated-declarations','-framework','AppKit','-framework','Foundation','-framework','Carbon','-Wl,-no_fixup_chains,-no_implicit_dylibs','-Wl,-install_name,@rpath/MLCalendarWakeRecovery.dylib','-o',lib,R/'calendar_wake_recovery.m')
(R/'reports/calendar-click-03-imports.json').write_bytes(run('python3',R/'check_wake_extension.py',lib))
for name in ['notification_click','wake_recovery']:
 exe=R/('work/test_calendar_'+name)
 run('xcrun','clang','-Werror','-fno-objc-arc','-fblocks','-Wno-deprecated-declarations','-framework','AppKit','-framework','Carbon',R/('test_calendar_'+name+'.m'),'-o',exe)
 print(run(exe).decode())
for p in [lib,A]:run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',p)
run('codesign','--verify','--deep','--strict',A)
p=D/'Calendar/manifest.json';m=json.loads(p.read_text());m['notification_click_trial']='03; direct child inherits helper sandbox; exact app URL routing; runtime pending';m['click_extension_sha256']=hashlib.sha256(lib.read_bytes()).hexdigest();p.write_text(json.dumps(m,indent=2)+'\n')
(D/'READ ME FIRST.txt').write_text('''CALENDAR CLICK TEST 03

The previous log showed sandbox-exec refusing to apply a second sandbox.
This version directly starts restored Calendar from the protected helper;
its child inherits that existing sandbox. No system protections are disabled.
The inherited helper profile is stricter than a normal UI launch, including
blocked networking, so keep this trial to local events.

INSTALL
Disable login alerts or stop the helper from your current Calendar folder.
Quit restored Calendar. Back up that folder, then replace only Calendar with
this package's Calendar folder at the same path. Open Calendar with its Open
command and re-enable login alerts if you used them.

TEST
Create a fresh local event with a sound alert a few minutes ahead. Quit Calendar
and click the new notification body when it appears. Check that restored
Calendar opens and selects the correct event. Allow 30 seconds after clicking
before collecting the startup log. Then repeat with Calendar already open.
Run Collect Calendar Startup Log.command and send the ZIP plus your observations.
If either fails, do not change URL defaults or delete any data.

ROLLBACK
Stop/disable this helper, quit restored Calendar, put your backed-up Calendar
folder back at the same path and launch normally. Re-enable login alerts if
wanted. Calendar databases are outside these package folders and remain intact.

Host checks: compiled without warnings, imports available on Mavericks,
click hook/path/input checks and wake regression tests passed, app signature
and extracted archive verified. Actual UI/event selection is still unverified.
''')
z=R/'deliverables/Calendar-Notification-Click-Test-03.zip';run('ditto','-c','-k','--keepParent',D,z)
v=R/'work/calendar-click-03-verification';run('ditto','-x','-k',z,v)
copy=v/D.name/'Calendar/Mountain Lion Calendar.app';run('codesign','--verify','--deep','--strict',copy)
assert hashlib.sha256((copy/'Contents/Frameworks/MLCalendarWakeRecovery.dylib').read_bytes()).hexdigest()==m['click_extension_sha256']
print(z)
