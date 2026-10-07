MOUNTAIN LION RESTORED APPS — PREVIEW 02 FOR MAVERICKS

Includes the tested Notes 05, Contacts 09, Calendar 10 and vCard Birthday Bridge
06. App binaries and launchers are unchanged from the working packages.
Continue using your persistent temporary account and test data. Internet
Accounts and syncing with stock apps are not supported. Notes can share the
stock Notes data location; Contacts and Calendar use separate local stores.

UPGRADING FROM PREVIEW 01
You do not need to upgrade a working Preview 01 plus Birthday Bridge 06 setup.
Preview 02 consolidates those same components and updates documentation.
If switching to this folder:
1. In the OLD folder, run Calendar/Disable Calendar Alerts at Login.command
   if login alerts were enabled. Otherwise run Stop Calendar Helper.command.
2. Quit all restored apps with Command-Q.
3. Extract Preview 02 to a permanent writable location. Do not replace Apple's
   apps or move this folder again while login alerts are enabled.
4. Launch each app using its new Open command. Existing data belongs to your
   user account, not the package folder, and should still appear. Keep the old
   folder until you have checked this. Never delete data to upgrade.
5. If wanted, run the NEW Calendar/Enable Calendar Alerts at Login.command.
   This points login alerts at the new folder. Check Calendar Alerts Status.
6. Copy your private Contacts.vcf into the NEW Birthdays folder if you want to
   reuse that export. Do not run old and new restored app copies together.

EVERYDAY USE
Inside Notes, Contacts and Calendar, use the matching Open .command launcher.
These supply the framework/plugin paths and Calendar protection/helper setup.
Do not open the inner app bundles directly. Terminal may be closed once the
launcher says launch requested. Quit applications normally with Command-Q.
If Finder blocks a command, Control-click and choose Open.

BIRTHDAYS FROM RESTORED CONTACTS
In restored Contacts, select the contacts to export and choose File > Export >
Export vCard. Save as Contacts.vcf in Birthdays (vCard 3.0). Keep restored Calendar
open and run Birthdays/Refresh Birthdays.command. Look in Contacts Birthdays,
not the native Birthdays calendar. Contacts itself need not remain open.

After editing a name or birthday, export again, replacing Contacts.vcf, and
refresh. Repeating an unchanged export does not duplicate generated events.
Omitted contacts are preserved: an export of a selection does not remove other
birthdays. To remove a birthday, clear its birthday field, export that contact,
and refresh. Deleting a contact outright does not remove its generated event;
clear/export first, or manually remove the corresponding event from Calendar.
Do not edit generated descriptions; they identify importer-owned entries.

Exports must come from the same restored Contacts store. UID or X-ABUID supplies
stable identity. Birthdays are yearly all-day events, with no displayed age.
February 29 recurs only in leap years. No explicit alarms are added; Calendar
settings may apply. Keep vCards private: they may contain other contact details.
They are not included in birthday diagnostic ZIPs.

CALENDAR ALERTS
Opening Calendar starts its alert helper. Alerts can fire with Calendar closed.
Enable Calendar Alerts at Login.command optionally starts the helper after
login; it does not open the Calendar window. Disable removes our login setting
and stops our helper without deleting events. Stop Calendar Helper stops the
current helper while leaving an existing login setting in place.
Disable before moving/removing this folder, then enable from its new location.
No sudo is needed. The stock CalendarAgent is separate and should be left alone.

WHAT HAS BEEN TESTED
User reported success on Mavericks for local Notes creation/persistence/sharing/
deletion/fullscreen; Contacts editing/rendering/view transitions; Calendar local
events, closed-app alerts/sound, changed/deleted event alerts, alarm icon, snooze,
and login startup. A positive sleep/wake check was reported; broader coverage
is still needed. An earlier immediate-on-creation alert remains unexplained.
Birthday creation, repeat import, rename/date change, clearing a birthday and
persistence after reopening were reported working. The two supplied initial
import logs independently confirm creation/readback; later checks are based
on the user's report, not additional diagnostic archives.

NEXT OPTIONAL TEST
Create a disposable daily recurring Calendar event a few minutes ahead, with
an at-time sound alert. Change only the next occurrence to a later time, quit
Calendar, and check that it alerts at the new time, not the original time.
Delete a later single occurrence and check that it does not alert, while the
remaining series still exists. Keep the laptop awake for this test so recurrence
behavior is checked separately from sleep recovery. Record expected/actual
alert times and use the existing Calendar diagnostic workflow to collect logs.

DIAGNOSTICS AND DATA
Each app has its existing Diagnose command. Quit that app before using it.
Calendar diagnostics restart its helper; use Collect Calendar Startup Log for
login behavior without restarting. Birthday refresh creates a diagnostic ZIP
in Birthdays. Review all logs before sharing; they may contain personal data.

Local data:
Contacts: ~/Library/Application Support/ML-Contacts
Calendar: ~/Library/MLCalData and ~/Library/Application Support/ML-Calendar
Birthday recovery journal: ~/Library/Application Support/ML-Calendar/BirthdayBridge
Notes: its existing Notes container; do not delete it to uninstall.

To remove the package, disable its Calendar login alerts, quit the restored
apps, stop the helper and remove the package folder. Data and logs remain.
No system apps/frameworks are replaced and no privileged service is installed.
