# Building the portable restored apps

## Requirements

Use a macOS build machine with Xcode command-line tools, Python 3.9 or newer,
and the macOS tools `xcrun`, `codesign`, `ditto`, `lsbom`, `pkgbuild`,
`productbuild`, and `pkgutil`. Compilation targets x86_64 and OS X 10.9.
Use a separate Mavericks Mac for runtime testing. Do not run the legacy apps,
frameworks, or account helpers on the modern build machine.

Supply your own Mountain Lion and Mavericks installers. Apple software is
not included in this repository.

## Repository layout

Run commands from the repository root. Notes sources are in `notes/`, Contacts
sources in `contacts/`, and Calendar and shared account/installer sources in
`calendars/`. `project_layout.py` maps old flat source references to these folders.
Generated output remains at repository root, outside the source folders.

Prepare the working directories:

```sh
mkdir -p builds deliverables work reports originals mavericks-originals
```

Keep installers, extracted Apple assets, outputs, logs, credentials, and user
information out of Git. The supplied `.gitignore` excludes their usual locations.

## Preparing Apple assets

Place your Mountain Lion `InstallESD.dmg` and Mavericks
`InstallESD.dmg` at repository root locally. Mount their installer
images read-only and locate the installation packages. The Mavericks download
may contain another installer or disk image, so its layout can differ.

Extract the installation packages without installing them or running their
scripts. Populate `originals/` with the Mountain Lion file hierarchy and
`mavericks-originals/` with the Mavericks hierarchy, preserving permissions and
framework symlinks. Paths must include `Applications/` and `System/Library/`.
Do not flatten the app or framework directories.

The account-plugin extractors also require the Mountain Lion Essentials
package's original `Payload` and `Bom` under `work/Essentials/`. Expand the
package container to obtain these files; retain the compressed Payload in its
original form. The checked-in selective extractors read its bzip2 odc-cpio
stream and verify selected entries against the BOM.

Once those inputs exist, run the required plugin extractors:

```sh
python3 calendars/extract_account_plugins.py
python3 calendars/extract_calendar_provider_plugins.py
python3 contacts/extract_contacts_account_plugins.py
python3 notes/extract_notes_account_plugins.py
```

Read each extractor's input and output paths first. An installer with a different
Payload encoding will require adapting the extraction step.

## Important limitation: staged builds

This is a staged restoration research project, not yet a one-command build from
installer images. Builders frequently copy an earlier modified app and apply the
next patch. They deliberately refuse to overwrite existing build destinations.
The source includes the current compatibility patches and packaging code, but
some earlier intermediate packages were assembled during development without a
standalone producer script. A complete fresh build of the historical chain has
not been validated.

[BUILD-STAGES.md](BUILD-STAGES.md) lists the static dependencies of the latest
installer and identifies missing historical staging steps. If starting with only
installer images, reconstruct those steps before running the later builders.
Do not substitute an unmodified Apple app for a modified prerequisite.

The initial app builders accept an output name and permission mode:

```sh
python3 notes/build_notes_trial.py notes-trial-05 public-only
python3 contacts/build_contacts_trial.py contacts-trial-09 public-only
python3 calendars/build_calendar_trial.py calendar-trial-10 public-only
```

These create initial restored apps, not the finished cloud-sync versions.
`package_restored_apps.py` expects those three directory names. Later account
builders require the additional stages listed in BUILD-STAGES.md. The birthday
bridge's source is retained in `calendars/birthday-bridge/`; its historical
`builds/birthday-bridge-test-06/Birthdays` package is another staged prerequisite.
The obsolete Google app-to-app calendar mirror/bridge is not needed or included.

## Build the latest iCloud-compatible versions

After the prerequisite stages exist, the final app builders are:

```sh
python3 notes/build_notes_icloud_menu14.py
python3 contacts/build_contacts_icloud_photo16.py
python3 calendars/build_calendar_background04.py
python3 calendars/package_icloud_bundle01.py
```

Their required inputs are respectively:

- Notes: `builds/notes-private-accounts-04/NotesAccounts`.
- Contacts: `builds/contacts-background-01/ContactsAccounts`.
- Calendar: `builds/restored-apps-preview-06/Calendar`, extracted provider assets,
  and the framework inputs referenced by `build_calendar_background04.py`.
- Bundle: the three outputs above plus
  `builds/restored-apps-preview-06/Birthdays`.

**Stop here for the recommended portable layout.** The combined output is
`builds/restored-apps-icloud-bundle-01/`, packaged as
`deliverables/Mountain-Lion-Restored-Apps-iCloud-Bundle-01.zip`.
It contains the original apps and their matching external scripts/profiles;
no installer, native RestoredLauncher conversion, or system-wide setup is added.
See [PORTABLE-LAYOUT.md](PORTABLE-LAYOUT.md). Notes supports Google and iCloud; Contacts supports native
CardDAV with the iCloud photo fix; Calendar includes native cloud accounts and
background refresh/alerts. Incoming Notes changes may need a relaunch. Reliable
local sound for cloud Calendar alerts remains unresolved.

## Optional: build the experimental installer

With iCloud Bundle01 staged, run:

```sh
python3 calendars/build_installer02.py
python3 calendars/build_installer03.py
```

Test02 is a build prerequisite for Test03; you do not need to install it.
The final output is:

`deliverables/Mountain-Lion-Restored-Apps-Installer-Test-03.pkg`

Test03 installs the three apps directly into `/Applications`. Necessary sandbox
profiles and helper controllers are embedded in each app under
`Contents/Resources/RestoredSupport`. Only four enable/disable login commands
are exposed in `/Applications/Restored Apps Login Controls`. A shared setup
script and Aqua LaunchAgent in `/Library` enable each user's private helpers
once. Data and account settings remain under each user's Library.

The installer is unsigned; the apps use ad-hoc signatures. Builders verify app
signatures and exercise only our new launcher in minimal fixtures. They do not
execute Apple's legacy binaries on the build machine. Finder/Launchpad startup,
relocated helpers, notification clicks, and multi-user installer behavior still
require Mavericks runtime validation.

The standalone uninstaller source is
`calendars/Uninstall Restored Apps.command`. It selects individual Test03 apps,
keeps local data by default, and requires explicit confirmation to erase it.
It is not currently embedded in the installer. The birthday bridge is unchanged
and is not installed by Test03; keep its separate package if needed.

## Test the portable bundle on Mavericks

Disable old Calendar/Contacts login helpers, stop the old Calendar helper, and
quit the restored apps. Extract the ZIP to a permanent location and keep its
folders together. Launch Notes with `Notes/Open Private Notes.command`, Contacts
with `Contacts/Open Contacts.command`, and Calendar with
`Calendar/Open Calendar.command`. Run the optional Enable commands from the new
Contacts and Calendar folders to restore login helpers at the new location.
Existing private data and accounts are retained. Check cloud changes, Contacts
photos, Calendar alerts/clicks, and logout/login. Do not open the legacy app
binaries directly or delete their sibling support files.

## Optional installer testing on Mavericks

Before upgrading, disable old Calendar and Contacts login helpers, stop the
Calendar helper, and quit the restored apps. Back up local-only data. Install
Test03 and open all three apps directly from Applications. Existing Test02 users
should run the two Enable commands once to update the helper paths.

Check existing accounts/data, create/edit/delete cloud items, Contacts photos,
Calendar alerts with the app closed, notification clicks, and logout/login.
Test separate user accounts to confirm data separation. Do not delete or replace
Apple's stock apps. Keep the restored app filenames unchanged.

Read the generated Test03 README for the current upgrade checklist. Publicly
sharing original source does not grant permission to redistribute Apple apps,
frameworks, icons, or installer images; those remain subject to Apple's terms.
