# Mountain Lion Apps on Mavericks

This project restores the classic Mountain Lion versions of
**Notes, Contacts, and Calendar** on OS X Mavericks (10.9), including their
original visual designs. Compatibility patches and app-local frameworks let
the restored apps run alongside the stock Mavericks apps with separate data.

This also supports iCloud and Google support for all three apps. 
Calendar includes background account refresh and alerts with snooze, notification clicks, and wake/login recovery. 
Contacts includes background syncing, contacts photo syncing, and UI and export fixes.
Notes supports two-way iCloud creation, editing, and deletion; sign-in persists when reopened. Notes syncing while the app is closed is not working. 

This repository contains restoration source, build/package scripts, probes,
and tests. **Apple installers, extracted applications/frameworks, generated
app bundles, and personal diagnostic logs are not included.** Building requires
your own Mountain Lion and Mavericks installers and a Mavericks test machine.

## Source layout

- `notes/`: Notes restoration, account UI, private storage, and probes.
- `contacts/`: Contacts restoration, CardDAV setup, and background sync.
- `calendars/`: Calendar restoration, alerts, and native accounts. Shared account compatibility helpers and suite packagers also live here and are reused by Notes and Contacts.

The latest packaging source builds Installer Test03, with three directly launchable apps in `/Applications`, embedded support files, and per-user login helpers. A selective uninstaller keeps local calendar, contacts and notes data by default.

See [BUILDING.md](BUILDING.md) for input preparation, final app and installer commands, and testing.

The project is experimental and is not affiliated with Apple.
