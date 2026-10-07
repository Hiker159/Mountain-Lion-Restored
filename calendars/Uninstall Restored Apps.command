#!/bin/bash
# Remove only Installer Test03 restored apps and this user's optional private data.
set -eu
if [ "$(id -u)" = 0 ]; then
 echo 'Run this by double-clicking it as your normal user, without sudo.'; exit 1
fi
printf '\nRestored Apps Uninstaller\n\nApps are installed for all users. Removing them affects everyone on this Mac.\nData cleanup applies ONLY to your current user. Other users retain their data.\nStock Apple apps and cloud data will not be deleted.\nQuit the restored apps before continuing.\n\n'
read -r -p 'Remove Notes? [y/N] ' notes
read -r -p 'Remove Contacts? [y/N] ' contacts
read -r -p 'Remove Calendar? [y/N] ' calendar
selected=()
for kind in Notes Contacts Calendar; do
 case "$kind" in Notes) answer="$notes";; Contacts) answer="$contacts";; Calendar) answer="$calendar";; esac
 case "$answer" in y|Y|yes|YES) selected+=("$kind");; esac
done
if [ "${#selected[@]}" -eq 0 ]; then echo 'Nothing selected. Cancelled.'; exit 0; fi
printf '\nSelected apps: %s\n' "${selected[*]}"
printf '\nWARNING: Deleting private data permanently removes your selected restored apps\047\n"On My Mac" notes, contacts, calendars/events, and private account settings.\nExport anything you want to keep first. Cloud copies are not deleted.\nKeeping data allows it to be used again after reinstalling.\n\n'
read -r -p 'Keep your local data? [Y/n] ' keep
delete_data=no
case "$keep" in n|N|no|NO)
 read -r -p "Type DELETE LOCAL DATA to permanently erase this user's selected app data: " confirm
 [ "$confirm" = 'DELETE LOCAL DATA' ] || { echo 'Cancelled; no changes made.'; exit 0; }
 delete_data=yes;;
esac
read -r -p 'Type UNINSTALL to proceed: ' confirm
[ "$confirm" = UNINSTALL ] || { echo 'Cancelled; no changes made.'; exit 0; }
# Validate all destinations before changing anything; never follow linked app bundles.
for kind in "${selected[@]}"; do
 app="/Applications/Mountain Lion $kind.app"
 [ ! -L "$app" ] || { echo "Linked app left unchanged: $app"; exit 1; }
 if [ -e "$app" ]; then
  case "$kind" in Notes) expected=org.ntest.Notes;; Contacts) expected=org.ctest.AddressBook;; Calendar) expected=org.authx.iCal;; esac
  actual=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$app/Contents/Info.plist")
  [ "$actual" = "$expected" ] || { echo "Unrelated app left unchanged: $app"; exit 1; }
  if /bin/ps -axo command= | /usr/bin/grep -F "$app/Contents/MacOS/" | /usr/bin/grep -v grep >/dev/null; then
   echo "Quit $kind and run this again. Nothing removed."; exit 1
  fi
 fi
done
# Stop the selected current-user helpers before removing their controllers.
for kind in "${selected[@]}"; do
 support="/Applications/Mountain Lion $kind.app/Contents/Resources/RestoredSupport"
 case "$kind" in
  Calendar) control="$support/calendar_login_control.py";;
  Contacts) control="$support/contacts_background_control.py";;
  Notes) continue;;
 esac
 if [ -f "$control" ]; then /usr/bin/python "$control" disable; fi
done
# Administrator access is needed only for shared installed files.
/usr/bin/sudo -v
for kind in "${selected[@]}"; do
 /usr/bin/sudo /bin/rm -rf "/Applications/Mountain Lion $kind.app"
 case "$kind" in
 Calendar) /usr/bin/sudo /bin/rm -f '/Applications/Restored Apps Login Controls/Enable Calendar Alerts at Login.command' '/Applications/Restored Apps Login Controls/Disable Calendar Alerts at Login.command';;
 Contacts) /usr/bin/sudo /bin/rm -f '/Applications/Restored Apps Login Controls/Enable Contacts Sync at Login.command' '/Applications/Restored Apps Login Controls/Disable Contacts Sync at Login.command';;
 esac
 if [ "$delete_data" = yes ]; then
  case "$kind" in
   Notes) paths=('Library/Application Support/ML Private Notes');;
   Contacts) paths=('Library/Application Support/ML-GContact');;
   Calendar) paths=('Library/Application Support/ML-AcctBook' 'Library/MLCalAuth' 'Library/Application Support/ML-CalAuthx');;
  esac
  for relative in "${paths[@]}"; do
   target="$HOME/$relative"
   [ ! -L "$HOME/Library" ] && [ ! -L "$HOME/Library/Application Support" ] && [ ! -L "$target" ] || { echo "Linked data path left unchanged: $target"; continue; }
   /bin/rm -rf "$target"
  done
 fi
done
if [ ! -e '/Applications/Mountain Lion Notes.app' ] && [ ! -e '/Applications/Mountain Lion Contacts.app' ] && [ ! -e '/Applications/Mountain Lion Calendar.app' ]; then
 /bin/launchctl unload /Library/LaunchAgents/org.local.RestoredApps.UserSetup.plist 2>/dev/null || true
 /usr/bin/sudo /bin/rm -f /Library/LaunchAgents/org.local.RestoredApps.UserSetup.plist '/Library/Application Support/ML Restored Apps/restored_user_setup.py'
 /usr/bin/sudo /bin/rmdir '/Library/Application Support/ML Restored Apps' '/Applications/Restored Apps Login Controls' 2>/dev/null || true
fi
printf '\nUninstall complete. Local data deletion: %s.\n' "$delete_data"
echo "Other users should disable the removed apps' helpers in their own accounts."
echo 'Earlier preview folders, Keychain entries, and the birthday bridge were left alone.'
read -r -p 'Press Return to close. ' ignored
