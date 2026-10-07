from pathlib import Path
import shutil,subprocess,json,hashlib,os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/calendar-google-sound-01/Calendar';A=R/'deliverables/Calendar-Google-Sound-Test-01.zip';V=R/'work/google-sound-01-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*args):return subprocess.check_output([str(x) for x in args],text=True,stderr=subprocess.STDOUT)
shutil.copytree(R/'builds/restored-apps-preview-04/Calendar',D,symlinks=True)
app=D/'Mountain Lion Calendar.app';lib=app/'Contents/Frameworks/MLAccountBootstrap.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-Wl,-install_name,@rpath/MLAccountBootstrap.dylib','-o',lib,R/'account_app_bootstrap_sound.m')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',lib)
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',app)
run('codesign','--verify','--deep','--strict',app)
(D/'READ ME FIRST.txt').write_text('''GOOGLE SOUND ALERT TEST 01 — MAVERICKS

Standalone Calendar folder for the Preview 04 account/data store. Quit the
current restored Calendar, disable its login helper temporarily if enabled,
and stop its helper before launching this copy with Open Calendar.command.
Do not run two copies at once. Keep Preview 04 for rollback.

This changes outgoing raw Google CalDAV sound alarms from AUDIO to DISPLAY,
retains trigger/attachment values and adds a private local-audio marker.
The restored iCalendar reader recognizes the marker to restore local sound.
Ordinary message alerts and non-Google uploads remain unchanged. Native Google
server preservation of the marker/attachment is unverified. Bulk XML uploads
are not transformed by this initial test. No password data is logged.

TEST
Create a disposable timed event on a Google calendar a few minutes ahead.
Choose Message with Sound and a recognizable sound. Check that Android and
Google Calendar web show a reminder. Wait for sync/refresh, quit and relaunch
Calendar, and check its sound selection survives. Confirm the alert plays on
this Mac and the phone. Repeat with Message only: it should remain silent on
this Mac. Collect Account Setup Log.command and report each result.
If the helper or app fails, collect that log anyway, then stop this helper and
return to Preview 04. Disable this package's login setting before switching.
The existing Test 10/Preview 04 Google account and data are retained.
''')
for p in D.glob('*.command'):run('bash','-n',p)
for p in D.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
def inventory(root):
 out={}
 for p in root.rglob('*'):
  if p.is_symlink():out[str(p.relative_to(root))]={'link':str(p.readlink())}
  elif p.is_file():out[str(p.relative_to(root))]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}
 return out
m={'build':'Google sound test 01','runtime':'pending Mavericks hook/upload/roundtrip checks','files':inventory(D)}
(D/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V)
assert inventory(D)==inventory(V/'Calendar')
run('codesign','--verify','--deep','--strict',V/'Calendar/Mountain Lion Calendar.app')
(R/'reports/google-sound-01-validation.json').write_text(json.dumps({'archive':str(A),'archive_sha256':hashlib.sha256(A.read_bytes()).hexdigest(),'signatures':'passed after extraction','roundtrip':'all hashes, symlinks and executable flags match','tests':'in-memory host guard/body transform tests passed; no legacy apps executed on build host','runtime':'pending'},indent=2)+'\n')
print(A)
