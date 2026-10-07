RESTORED APPS — SHARED DATABASE EXPERIMENT 01

THIS IS A SEPARATE, UNVERIFIED EXPERIMENT, NOT AN UPGRADE TO PREVIEW 03.
Use a NEW disposable macOS user account with no Internet Accounts and only
throwaway local data. Do not run it in the account holding your Google sync
or working restored-app data. Older Contacts previously rebuilt Mavericks
store metadata when pointed at its database. Shared writes may change, rebuild
or corrupt data used by stock apps. Merely removing this package cannot undo
such changes. A fresh disposable account keeps that risk away from real data.

WHAT CHANGED
Notes is unchanged: it already uses the stock Notes identity/data location.
Contacts now uses ~/Library/Application Support/AddressBook, original database
preference keys and stock AddressBook change notifications. The source plugin
fix and working view-transition behavior remain.
Calendar uses ~/Library/Calendars and ~/Library/Application Support/iCal for
both its UI and helper. Its experimental app/helper use org.share identities,
separate from the working org.local preview. The helper is session-only; no
login installer is included. It does not stop the stock CalendarAgent.

Calendar's native Contacts/birthday integration and legacy external-sync
launch remain disabled. Existing working compatibility patches are retained.
Calendar networking remains blocked for the experimental helper/UI; this is
not a direct Google/iCloud sync build. Contacts retains its old runtime behavior,
which is why the fresh test account must have no connected accounts.
No birthday or Google mirror is included. A shared path does not guarantee
compatible schemas, inter-app updates, alarms, or native birthday behavior.
Stock and restored helpers may both observe the same events and duplicate alerts.

FIRST TEST — LOCAL DATA ONLY
1. Create a new Standard macOS user account; sign into it. Do not add accounts.
2. Open stock Contacts/Calendar/Notes. Create one disposable local contact,
   one local calendar event without alerts, and one note. Quit the stock apps.
3. Extract this package separately. Do not replace any existing preview folder.
4. Run Contacts/Open Shared Contacts.command. Check whether the stock contact
   appears. Note any database warnings. Quit it with Command-Q, reopen stock
   Contacts, and check that the contact is still intact. Stop if anything is
   missing, reset, or rebuilt. Do not use an import to mask a failure.
5. Only if that passes, try Calendar/Open Shared Calendar.command, then quit
   it and run Calendar/Stop Shared Calendar Helper.command before reopening
   stock Calendar to check the event. Leave Apple's background helper alone.
6. Test Notes in the same sequence using Notes/Open Shared Notes.command.
7. Collect Shared Test Logs.command gathers logs and file metadata (not database
   copies). Send its ZIP and observations before attempting edit-back tests.

Use only one version of each foreground app at a time. This reduces concurrent
editing but does not prevent Apple's background services from accessing data.
Use the supplied Open Shared commands, not the inner app bundles directly.
Do not use existing diagnostic launchers or bridges from the normal preview.

REMOVAL / ROLLBACK
Quit all experimental apps and run Stop Shared Calendar Helper.command. Remove
this extracted package. The account's stock stores remain modified if the old
apps wrote them; deleting the app is not a database rollback. Discarding this
fresh disposable test account is the clean reset. Keep normal work in the
original account with Preview 03 and its isolated Contacts/Calendar stores.

HOST VALIDATION
Only code/resources in this project were changed. No host user databases were
opened or modified, no services installed, and no legacy apps launched.
Build/signature/archive checks establish packaging consistency, not database
compatibility. Actual shared-store behavior requires the disposable laptop test.
