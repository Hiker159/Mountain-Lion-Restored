"""Build a Mavericks-only installer. Never installs or executes legacy applications on host."""
from pathlib import Path
import shutil,subprocess,plistlib,json,os,hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/restored-apps-installer-01';ROOT=D/'payload';TARGET=ROOT/'Applications/Mountain Lion Restored Apps';S=R/'builds/restored-apps-icloud-bundle-01';OUT=R/'deliverables/Mountain-Lion-Restored-Apps-Installer-Test-01.pkg'
if D.exists() or OUT.exists():raise RuntimeError('Existing artifacts preserved')
D.mkdir();TARGET.mkdir(parents=True)
def run(*args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
launcher=D/'RestoredLauncher'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Cocoa',R/'restored_app_launcher.m','-o',launcher)
plans={}
for kind in ('Notes','Contacts','Calendar'):
 folder=TARGET/kind;shutil.copytree(S/kind,folder,symlinks=True)
 app=folder/('Mountain Lion '+kind+'.app');plist=app/'Contents/Info.plist';info=plistlib.loads(plist.read_bytes())
 assert info['CFBundleExecutable']==kind
 info['MLRestoredOriginalExecutable']=kind;info['MLRestoredAppKind']=kind;info['CFBundleExecutable']='RestoredLauncher'
 plist.write_bytes(plistlib.dumps(info))
 shutil.copy2(launcher,app/'Contents/MacOS/RestoredLauncher')
 # Original executable signatures bind Info.plist too; update them after changing CFBundleExecutable.
 run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',app/'Contents/MacOS'/kind)
 run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--preserve-metadata=entitlements','--requirements','=library => true',app)
 run('codesign','--verify','--deep','--strict',app)
 # Execute only the newly compiled launcher in a minimal fixture app, never in a legacy bundle.
 fake=D/'plan-fixtures'/kind/('Mountain Lion '+kind+'.app');(fake/'Contents/MacOS').mkdir(parents=True)
 (fake/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'RestoredLauncher','CFBundleIdentifier':'org.restored.fixture.'+kind,'MLRestoredAppKind':kind,'CFBundlePackageType':'APPL'}))
 shutil.copy2(launcher,fake/'Contents/MacOS/RestoredLauncher')
 plans[kind]=json.loads(run(fake/'Contents/MacOS/RestoredLauncher','--print-launch-plan'))
 assert plans[kind]['kind']==kind and plans[kind]['executable'].endswith('/Contents/MacOS/'+kind)
 assert '-f' in plans[kind]['arguments'] and any(a.startswith('DYLD_INSERT_LIBRARIES=') for a in plans[kind]['arguments'])
 (folder/'READ ME FIRST.txt').write_text('Open Mountain Lion '+kind+'.app directly from Finder, Applications or Launchpad. The app now applies the tested private launch settings itself. Existing optional setup and diagnostic commands remain here for troubleshooting; they are not required for normal launches.\n')
shutil.copytree(S/'Birthdays',TARGET/'Birthdays',symlinks=True)
(TARGET/'.restored-apps-installer-owner').write_text('org.local.restoredapps.installer\n')
(TARGET/'READ ME FIRST.txt').write_text('''MOUNTAIN LION RESTORED APPS - INSTALLER TEST 01
OS X Mavericks (10.9) only.

NORMAL USE
Open Mountain Lion Notes, Mountain Lion Contacts, or Mountain Lion Calendar
from /Applications/Mountain Lion Restored Apps/the corresponding app folder.
Launchpad should also discover the apps after installation. You may drag the
apps to the Dock. You do not need to run the Open commands anymore.
Keep the installation folders intact: the private sandbox profiles and helper
controls alongside each app are part of the installation.

MIGRATION
Existing private accounts and data locations are unchanged; no reset is needed.
Before installation, disable Calendar alerts and Contacts sync at login from
any OLD preview folders, stop the old Calendar helper, and quit restored apps.
The installer refuses installation while restored apps/helpers are running.
After installation, open all three apps directly. To keep background features
at login, use Enable Calendar Alerts at Login.command and Enable Contacts Sync
at Login.command in their installed folders once. Existing managed Calendar
login settings are refreshed on app startup; an existing managed Contacts job
is moved to this installation on Contacts startup. No job is installed as root.
Moved apps may ask for Keychain access again.

TEST THIS BUILD
Open all three from Finder or Launchpad without the Open commands. Check notes,
contacts/photos, calendar events, and account sign-in. Test Calendar alert
clicks with Calendar open and closed, then background alerts after logout/login.
Collect logs with the installed Collect commands if anything fails.
This installer changes launch packaging; its Mavericks runtime is not yet tested.

WHAT IS INSTALLED
User-tested iCloud Bundle01 components plus a native built-in launcher.
Google support remains; birthday export bridge is unchanged. The stock apps,
stock databases, and your private data are not replaced. Notes does not install
an app-closed sync job. iCloud Notes incoming deletions may need reopening.

INSTALLER STATUS
This is an unsigned installer with ad-hoc signed restored apps, not a Developer
ID-signed public release. Installer writes only the suite folder under Applications.
It does not log in to accounts, read user credentials, or configure user helpers.
To remove it, first disable installed Calendar/Contacts login helpers and stop
the Calendar helper, quit the apps, then remove Mountain Lion Restored Apps.
Private user data is retained.
''')
scripts=D/'scripts';scripts.mkdir()
(scripts/'preinstall').write_text('''#!/bin/bash
set -eu
case "$(/usr/bin/sw_vers -productVersion)" in 10.9|10.9.*) ;; *) echo 'This installer requires OS X Mavericks.' >&2; exit 1;; esac
DEST="${3:-/}/Applications/Mountain Lion Restored Apps"
if [ -L "$DEST" ]; then echo 'Refusing a linked destination.' >&2; exit 1; fi
if [ -e "$DEST" ]; then
 if [ ! -f "$DEST/.restored-apps-installer-owner" ] || [ -L "$DEST/.restored-apps-installer-owner" ] || [ "$(/bin/cat "$DEST/.restored-apps-installer-owner")" != org.local.restoredapps.installer ]; then
 echo 'An unrelated folder occupies the destination; it was left unchanged.' >&2; exit 1
 fi
fi
if /bin/ps -axo comm= | /usr/bin/grep -E '/Mountain Lion (Notes|Contacts|Calendar)\\.app/Contents/MacOS/(Notes|Contacts|Calendar|RestoredLauncher)$|/Mountain Lion Calendar Alerts\\.app/Contents/MacOS/CalendarAgent$|/Mountain Lion Contacts\\.app/Contents/Frameworks/AddressBook\\.framework/.*/AddressBookSourceSync\\.app/Contents/MacOS/AddressBookSourceSync$' >/dev/null; then
 echo 'Quit restored apps and stop their Calendar/Contacts helpers before installing.' >&2; exit 1
fi
exit 0
''');(scripts/'preinstall').chmod(0o755);run('bash','-n',scripts/'preinstall')
# Installed directories are root-owned; diagnostics must be written to the user's Desktop.
for command in TARGET.rglob('*.command'):
 text=command.read_text().replace('OUT="$HERE/','OUT="$HOME/Desktop/').replace('TEST_OUT="$TEST_DIR/','TEST_OUT="$HOME/Desktop/')
 if command.name=='Refresh Birthdays.command':text=text.replace('"$HERE/Contacts.vcf"','"$HOME/Desktop/Contacts.vcf"')
 command.write_text(text)
with (TARGET/'Birthdays/READ ME FIRST.txt').open('a') as f:f.write('\nInstalled version: put the exported Contacts.vcf on your Desktop before running Refresh Birthdays.command. Diagnostic ZIPs are also saved on the Desktop. The birthday bridge itself is unchanged.\n')
for p in TARGET.rglob('*.command'):run('bash','-n',p)
for p in TARGET.rglob('*.py'):compile(p.read_bytes(),str(p),'exec')
components=D/'components.plist';run('pkgbuild','--analyze','--root',ROOT,components)
c=plistlib.loads(components.read_bytes())
for item in c:
 item['BundleIsRelocatable']=False;item['BundleHasStrictIdentifier']=True
components.write_bytes(plistlib.dumps(c))
component=D/'RestoredApps.pkg';run('pkgbuild','--root',ROOT,'--component-plist',components,'--scripts',scripts,'--ownership','recommended','--identifier','org.local.restoredapps.installer','--version','0.1.0','--install-location','/',component)
resources=D/'resources';resources.mkdir();(resources/'welcome.html').write_text('<html><body><h2>Mountain Lion Restored Apps</h2><p>Install the tested iCloud versions of Notes, Contacts and Calendar on Mavericks. Open the apps directly from Applications or Launchpad.</p><p>Before installing, disable old Calendar/Contacts login helpers, stop the old Calendar helper, and quit restored apps. Existing private accounts and data are retained.</p><p>This is an unsigned installer test release. Direct-launch and moved-helper behavior need Mavericks validation.</p></body></html>')
dist=D/'Distribution.xml';dist.write_text('''<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
<title>Mountain Lion Restored Apps</title><welcome file="welcome.html"/>
<options customize="never" require-scripts="true" hostArchitectures="x86_64"/>
<domains enable_localSystem="true" enable_currentUserHome="false" enable_anywhere="false"/>
<installation-check script="checkOS()"/>
<script><![CDATA[function checkOS(){var v=system.version.ProductVersion;if(system.compareVersions(v,'10.9')>=0 &amp;&amp; system.compareVersions(v,'10.10')<0)return true;my.result.title='OS X Mavericks required';my.result.message='Install this suite only on OS X Mavericks (10.9).';my.result.type='Fatal';return false;}]]></script>
<choices-outline><line choice="suite"/></choices-outline><choice id="suite" title="Restored Apps"><pkg-ref id="org.local.restoredapps.installer"/></choice>
<pkg-ref id="org.local.restoredapps.installer" version="0.1.0" auth="Root">RestoredApps.pkg</pkg-ref>
</installer-gui-script>
'''.replace('&amp;&amp;','&&'))
run('productbuild','--distribution',dist,'--package-path',D,'--resources',resources,OUT)
expanded=D/'expanded';run('pkgutil','--expand',OUT,expanded)
assert (expanded/'Distribution').exists()
report={'installer':str(OUT),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'size_bytes':OUT.stat().st_size,'signatures':'three modified apps passed deep strict verification','launch_plan_fixtures':'all three native launcher plans passed without legacy execution','package_expansion':'passed','runtime':'pending on Mavericks; host not installed','unsigned_installer':True}
(R/'reports/installer01-validation.json').write_text(json.dumps(report,indent=2)+'\n')
shutil.copy2(TARGET/'READ ME FIRST.txt',R/'deliverables/Restored-Apps-Installer-Test-01-README.txt')
print(json.dumps(report,indent=2))
