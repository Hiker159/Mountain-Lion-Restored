"""Package validated trial binaries with everyday launchers; never install locally."""
from pathlib import Path
import subprocess,shutil,json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root()
D=R/'builds/restored-apps-preview-01'
if D.exists():raise SystemExit('Existing package preserved; choose a new version.')
D.mkdir()
def run(*a):subprocess.run([str(x) for x in a],check=True)
def command(path,body):path.write_text(body);path.chmod(0o755)
header='''#!/bin/bash
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$(/usr/bin/sw_vers -productVersion)" in
  10.9|10.9.*) ;;
  *) echo 'Use this package on Mavericks only.'; exit 1 ;;
esac
if [ "$(/usr/bin/id -u)" = 0 ]; then echo 'Run without sudo.'; exit 1; fi
'''
for name,build in [('Notes','notes-trial-05'),('Contacts','contacts-trial-09'),('Calendar','calendar-trial-10')]:
 dest=D/name;dest.mkdir();src=R/'builds'/build
 app='Mountain Lion '+name+'.app'
 run('ditto',src/app,dest/app)
 shutil.copy2(src/('Diagnose '+name+'.command'),dest/('Diagnose '+name+'.command'))
 shutil.copy2(src/'manifest.json',dest/'manifest.json')
 run('codesign','--verify','--deep','--strict',dest/app)
 body=header+'''LOG_DIR="$HOME/Library/Logs/Mountain Lion Restored Apps"
/bin/mkdir -p "$LOG_DIR"
'''+('APP="$HERE/'+app+'"\n')+'''/usr/bin/codesign --verify --deep "$APP"
'''
 if name=='Notes':body+='''/usr/bin/nohup "$APP/Contents/MacOS/Notes" >> "$LOG_DIR/Notes.log" 2>&1 < /dev/null &
'''
 elif name=='Contacts':body+='''DATA="$HOME/Library/Application Support/ML-Contacts"
/bin/mkdir -p "$DATA"
/usr/bin/nohup /usr/bin/env ML_CONTACTS_PLUGINS="$APP/Contents/PlugIns/ContactSources" "$APP/Contents/MacOS/Contacts" -MLAlternateDataStoreDirectory "$DATA" >> "$LOG_DIR/Contacts.log" 2>&1 < /dev/null &
'''
 else:
  for f in ['calendar_agent_control.py','calendar_login_control.py','calendar-trial.sb','calendar-agent-trial.sb','Stop Calendar Helper.command','Collect Calendar Startup Log.command']:shutil.copy2(R/f,dest/f)
  body+='''/usr/bin/python "$HERE/calendar_login_control.py" open
DATA="$HOME/Library/MLCalData"
SUPPORT="$HOME/Library/Application Support/ML-Calendar"
/bin/mkdir -p "$DATA" "$SUPPORT"
SANDBOX=(/usr/bin/sandbox-exec
  -D "STOCK_CALENDARS=$HOME/Library/Calendars"
  -D "STOCK_ICAL_SUPPORT=$HOME/Library/Application Support/iCal"
  -D "STOCK_CONTACTS=$HOME/Library/Application Support/AddressBook"
  -D "STOCK_ICAL_PREFS=$HOME/Library/Preferences/com.apple.iCal.plist"
  -f "$HERE/calendar-trial.sb")
"${SANDBOX[@]}" /usr/bin/true
/usr/bin/nohup "${SANDBOX[@]}" "$APP/Contents/MacOS/Calendar" -MLCalDataDirectory "$DATA" -iCalApplicationSupportDirectory "$SUPPORT" >> "$LOG_DIR/Calendar.log" 2>&1 < /dev/null &
'''
  for label,mode in [('Enable Calendar Alerts at Login','enable'),('Disable Calendar Alerts at Login','disable')]:
   command(dest/(label+'.command'),header+'/usr/bin/python "$HERE/calendar_login_control.py" '+mode+'\necho "Press Return to close."\nread -r DONE\n')
  command(dest/'Calendar Alerts Status.command',header+'''/usr/bin/python "$HERE/calendar_agent_control.py" status || true
if [ -f "$HOME/Library/LaunchAgents/org.local.CalendarAgent.plist" ]; then
  echo 'A Calendar login configuration is present.'
else
  echo 'No Calendar login configuration is installed.'
fi
echo 'Press Return to close.'
read -r DONE
''')
 body+='''echo 'Launch requested. You can close this Terminal window.'
echo "If no app appears, see the log in: $LOG_DIR"
'''
 command(dest/('Open '+name+'.command'),body)
 for script in dest.glob('*.command'):run('bash','-n',script)
(D/'READ ME FIRST.txt').write_text('''MOUNTAIN LION RESTORED APPS — PREVIEW 01 FOR MAVERICKS

This package combines Notes Test 05, Contacts Test 09 and Calendar Test 10.
Their app binaries are unchanged. New launchers and optional login setup need
verification on the Mavericks laptop. Continue using a temporary Standard user
with disposable data and no Internet Accounts. Guest data may vanish at logout.

GETTING STARTED

1. Quit previous restored apps and stop the old Calendar helper.
2. Place this entire extracted folder somewhere permanent and writable, such
   as your user's Applications folder. Do not replace Apple's apps. Keep each
   app with its accompanying files; folder paths may contain spaces.
3. Inside Notes, Contacts or Calendar, double-click Open Notes.command,
   Open Contacts.command or Open Calendar.command. If Finder blocks a command,
   Control-click and choose Open. Do not disable system security settings.
4. The launcher exits after requesting launch. You may close its Terminal
   window. Use the app normally, and Command-Q to quit. Quit the previous copy
   before using a new package. Launch requests are logged under
   ~/Library/Logs/Mountain Lion Restored Apps.

Use the Open commands rather than opening the inner apps directly: Contacts
needs its bundled source-plugin path, and Calendar needs its protections and
background helper. These are not yet standalone drag-to-Applications apps.

OPTIONAL CALENDAR ALERTS AT LOGIN

Opening Calendar starts its separate alert helper for the current session.
Calendar may be quit while alerts continue. By default nothing starts at login.
To opt in, run Calendar/Enable Calendar Alerts at Login.command. It starts the
helper now and adds one user-only LaunchAgent. No password or sudo is needed.
It starts the helper, not the Calendar window, on subsequent logins.

After enabling, keep this folder at its current location. Disable login alerts
BEFORE moving/removing it or upgrading macOS. After moving, enable again from
the new location. Disable Calendar Alerts at Login.command removes only our
marked login configuration and stops this helper; event data is retained.
Stop Calendar Helper.command stops alerts for this session but leaves optional
login startup enabled. Calendar Alerts Status.command reports helper status.
Previously queued notifications may still appear after stopping the helper.

The login file is ~/Library/LaunchAgents/org.local.CalendarAgent.plist.
The setup refuses to overwrite an unrelated file there. It never unloads the
stock com.apple.CalendarAgent. Enabling login alerts is a new, unverified feature.

NEXT LAPTOP CHECK

First launch each app with its Open command and confirm existing temporary data
appears. For Calendar, create a fresh future alert, quit the app, and confirm it
fires. Then, if using a persistent temporary Standard account, enable login
alerts, create a fresh event roughly ten minutes ahead, and log out and back in
before it is due. Do not open Calendar after logging in. Confirm the alert and
sound, then run Collect Calendar Startup Log.command and share the resulting ZIP.
This collector does not restart the helper.
Guest is unsuitable for checking data across logout. Finally disable login
alerts and verify the status command no longer lists a running helper.

DIAGNOSTICS

Each app includes its existing Diagnose command. Quit the app before using it.
Calendar diagnostics restart the helper and wait after Calendar quits for your
alert test; press Return to collect its ZIP. Diagnostics may contain personal
information; review before sharing. Ordinary launch logs do not replace the
full diagnostic archive. Login failures are logged at
~/Library/Application Support/ML-Calendar/Agent/CalendarAgent.log.

WHAT IS AND IS NOT VERIFIED

Notes: local creation, persistence, sharing, deletion and fullscreen tested.
Contacts: local creation/editing/rendering and view transitions tested.
Calendar: local events, closed-app sound alerts, moved/deleted alerts, restored
alarm icon and one-minute snooze tested. A positive sleep/wake test and wake
callback logs exist; broad sleep/recurrence/click-action testing is unfinished.
An isolated immediate-on-creation alert remains unexplained.

Contacts and Calendar have separate data stores. Birthdays integration, online
accounts and syncing with stock apps remain unsupported. Notes retains Apple's
bundle identity and may share the stock Notes data location in the same user;
it is not isolated like Contacts/Calendar. Use the temporary account.

DATA AND REMOVAL

Contacts: ~/Library/Application Support/ML-Contacts
Calendar: ~/Library/MLCalData and ~/Library/Application Support/ML-Calendar
Notes: its existing Notes container/data location; do not delete it to uninstall.

To remove this package: disable Calendar login alerts, quit all restored apps,
stop the helper, and remove the extracted folder. Data/logs remain for recovery.
Nothing replaces system apps/frameworks or installs a privileged service.
''')
print(D)
