"""Self-contained restored apps; required sandbox and helper controls live inside each app."""
from pathlib import Path
import subprocess,shutil,plistlib,json,hashlib,os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/restored-apps-installer-03';ROOT=D/'payload';APPS=ROOT/'Applications';BASE=R/'builds/restored-apps-installer-02/payload/Applications/Mountain Lion Restored Apps';A=R/'deliverables/Mountain-Lion-Restored-Apps-Installer-Test-03.pkg'
if D.exists() or A.exists():raise RuntimeError('Existing artifacts preserved')
D.mkdir();APPS.mkdir(parents=True)
def run(*args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
src=(R/'restored_app_launcher.m').read_text().replace('NSString *folder=[app stringByDeletingLastPathComponent]','NSString *folder=[app stringByAppendingPathComponent:@"Contents/Resources/RestoredSupport"]')
(D/'restored_app_launcher.m').write_text(src)
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Cocoa',D/'restored_app_launcher.m','-o',D/'RestoredLauncher')
required={'Notes':['notes-private.sb'],'Contacts':['contacts-accounts.sb','contacts_background_control.py'],'Calendar':['calendar-trial.sb','calendar-agent-trial.sb','calendar_agent_control.py','calendar_login_control.py']}
for kind,names in required.items():
 app=APPS/('Mountain Lion '+kind+'.app');shutil.copytree(BASE/kind/app.name,app,symlinks=True)
 support=app/'Contents/Resources/RestoredSupport';support.mkdir()
 for name in names:shutil.copy2(BASE/kind/name,support/name)
 for name in ['calendar_agent_control.py','contacts_background_control.py']:
  p=support/name
  if p.exists():
   text=p.read_text().replace("os.path.join(package,'Mountain Lion "+kind+".app')","os.path.abspath(os.path.join(package,'..','..','..'))")
   p.write_text(text);compile(text,str(p),'exec')
 shutil.copy2(D/'RestoredLauncher',app/'Contents/MacOS/RestoredLauncher')
 # Rebuild only our helper extension to locate the now-internal Calendar profile.
 if kind=='Calendar':
  click=(R/'calendar_notification_click.m').read_text().replace('NSString *folder=[appPath stringByDeletingLastPathComponent]','NSString *folder=[appPath stringByAppendingPathComponent:@"Contents/Resources/RestoredSupport"]')
  for old,new in [('org.local.iCal','org.authx.iCal'),('com.apple.iCal','org.authx.iCal'),('-MLCalDataDirectory','-MLCalAuthDirectory'),('Library/MLCalData','Library/MLCalAuth'),('Library/Application Support/ML-Calendar','Library/Application Support/ML-CalAuthx')]:click=click.replace(old,new)
  (D/'calendar_notification_click.m').write_text(click)
  shutil.copy2(R/'calendar_wake_recovery.m',D/'calendar_wake_recovery.m')
  lib=app/'Contents/Frameworks/MLCalendarWakeRecovery.dylib'
  run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-fblocks','-Werror','-Wno-deprecated-declarations','-framework','AppKit','-framework','Foundation','-framework','Carbon','-Wl,-no_fixup_chains,-no_implicit_dylibs','-Wl,-install_name,@rpath/MLCalendarWakeRecovery.dylib','-o',lib,D/'calendar_wake_recovery.m')
  run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',lib)
 run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',app)
 run('codesign','--verify','--deep','--strict',app)
 # Minimal new-code-only fixture: never execute the legacy app on host.
 fake=D/'fixtures'/app.name;(fake/'Contents/MacOS').mkdir(parents=True)
 (fake/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'RestoredLauncher','CFBundleIdentifier':'org.restored.fixture.'+kind,'CFBundlePackageType':'APPL','MLRestoredAppKind':kind}))
 shutil.copy2(D/'RestoredLauncher',fake/'Contents/MacOS/RestoredLauncher')
 plan=json.loads(run(fake/'Contents/MacOS/RestoredLauncher','--print-launch-plan'))
 assert any('/Contents/Resources/RestoredSupport/' in x and x.endswith('.sb') for x in plan['arguments'])
 (D/(kind+'-launch-plan.json')).write_text(json.dumps(plan,indent=2))
shared=ROOT/'Library/Application Support/ML Restored Apps';shared.mkdir(parents=True)
setup=(R/'restored_user_setup.py').read_text().replace("SUITE='/Applications/Mountain Lion Restored Apps'","SUITE='/Applications'").replace("os.path.join(SUITE,folder,script)","os.path.join(SUITE,'Mountain Lion '+folder+'.app','Contents','Resources','RestoredSupport',script)")
(shared/'restored_user_setup.py').write_text(setup)
la=ROOT/'Library/LaunchAgents';la.mkdir(parents=True)
shutil.copy2(R/'builds/restored-apps-installer-02/payload/Library/LaunchAgents/org.local.RestoredApps.UserSetup.plist',la)
# Expose only the four requested login controls; no diagnostic/open/test scripts.
controls=APPS/'Restored Apps Login Controls';controls.mkdir()
for kind,script,modes in [('Calendar','calendar_login_control.py',['enable','disable']),('Contacts','contacts_background_control.py',['enable','disable'])]:
 for mode in modes:
  name=('Enable' if mode=='enable' else 'Disable')+' '+('Calendar Alerts' if kind=='Calendar' else 'Contacts Sync')+' at Login.command'
  command=controls/name
  command.write_text('#!/bin/bash\nset -eu\n/usr/bin/python "/Applications/Mountain Lion '+kind+'.app/Contents/Resources/RestoredSupport/'+script+'" '+mode+'\n')
  command.chmod(0o755);run('bash','-n',command)
scripts=D/'scripts';shutil.copytree(R/'builds/restored-apps-installer-02/scripts',scripts)
pre=(scripts/'preinstall').read_text();start=pre.index('DEST=');end=pre.index('if /bin/ps',start)
pre=pre[:start]+'''for KIND in Notes Contacts Calendar; do
 DEST="${3:-/}/Applications/Mountain Lion $KIND.app"
 [ ! -L "$DEST" ] || { echo 'Refusing a linked app destination.' >&2; exit 1; }
 if [ -e "$DEST" ]; then
  case "$KIND" in Notes) EXPECT=org.ntest.Notes;; Contacts) EXPECT=org.ctest.AddressBook;; Calendar) EXPECT=org.authx.iCal;; esac
  IDENT="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$DEST/Contents/Info.plist" 2>/dev/null || true)"
  [ "$IDENT" = "$EXPECT" ] || { echo 'An unrelated app occupies the destination; left unchanged.' >&2; exit 1; }
 fi
done
''' +pre[end:]
# Launch setup after an upgrade too; remove only the setup job, never user preferences.
post=(scripts/'postinstall').read_text().replace('/bin/launchctl load /Library/LaunchAgents/org.local.RestoredApps.UserSetup.plist','/bin/launchctl load /Library/LaunchAgents/org.local.RestoredApps.UserSetup.plist')
(scripts/'preinstall').write_text(pre);(scripts/'postinstall').write_text(post)
for p in scripts.iterdir():run('bash','-n',p)
compile(setup,'restored_user_setup.py','exec')
components=D/'components.plist';run('pkgbuild','--analyze','--root',ROOT,components)
c=plistlib.loads(components.read_bytes())
for item in c:item['BundleIsRelocatable']=False;item['BundleHasStrictIdentifier']=True;item['BundleIsVersionChecked']=False
components.write_bytes(plistlib.dumps(c))
run('pkgbuild','--root',ROOT,'--component-plist',components,'--scripts',scripts,'--ownership','recommended','--identifier','org.local.restoredapps.installer','--version','0.3.0','--install-location','/',D/'RestoredApps.pkg')
shutil.copytree(R/'builds/restored-apps-installer-02/resources',D/'resources')
dist=(R/'builds/restored-apps-installer-02/Distribution.xml').read_text().replace('0.2.0','0.3.0');(D/'Distribution.xml').write_text(dist)
run('productbuild','--distribution',D/'Distribution.xml','--package-path',D,'--resources',D/'resources',A)
run('pkgutil','--expand',A,D/'expanded')
readme='''RESTORED APPS - CLEAN INSTALLER TEST 03\n\nInstall on Mavericks only. The three apps are installed directly in /Applications. Required sandbox profiles and helper controls are inside each app in Contents/Resources/RestoredSupport. Keep each .app intact. No external Open scripts or diagnostic/test scripts are installed. Four Enable/Disable login commands are in /Applications/Restored Apps Login Controls. Shared one-time per-user setup remains in /Library.\n\nBefore upgrading, disable old Calendar/Contacts login helpers, stop the Calendar helper, and quit restored apps. If upgrading from Installer Test02, after installing use both Enable commands once: the existing setup marker deliberately preserves your prior choices. New users receive automatic helper setup at login. Do not delete private data. The old /Applications/Mountain Lion Restored Apps folder is not removed automatically; use only the new top-level apps during testing. The birthday bridge is not changed or repackaged; keep your prior copy.\n\nTest opening all three directly, account/data persistence and syncing, Calendar notification clicks with Calendar open and closed, and background alerts/sync after logout/login. Existing users retain separate databases and credentials. This unsigned test installer changes support paths and still requires Mavericks validation.\n'''
(R/'deliverables/Restored-Apps-Installer-Test-03-README.txt').write_text(readme)
report={'installer':str(A),'sha256':hashlib.sha256(A.read_bytes()).hexdigest(),'signatures':'all three apps deep strict passed','launch_plans':'internal support paths passed in new-code-only fixtures','visible_files':'three apps and four login commands only','shared_library_files':'one setup script and one LaunchAgent','legacy_execution_on_host':False,'runtime':'pending on Mavericks, especially notification clicks and relocated helper paths'}
(R/'reports/installer03-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
