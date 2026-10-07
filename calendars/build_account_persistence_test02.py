from pathlib import Path
import subprocess,shutil,json,hashlib,zipfile,stat,os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/account-credential-persistence-02/AccountCredentials'
def run(*a):
 p=subprocess.run([str(x) for x in a],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
if D.exists():raise RuntimeError('Destination exists')
D.mkdir(parents=True)
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fblocks','-Werror','-Wno-deprecated-declarations','-framework','CoreFoundation','-Wl,-no_fixup_chains,-reexport_framework,Security','-Wl,-install_name,@rpath/MLAccountSecurity.dylib','-Wl,-compatibility_version,55179.3.0','-Wl,-current_version,55179.13.0','-o',D/'MLAccountSecurity.dylib',R/'account_security_compat.c')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1',D/'MLAccountSecurity.dylib')
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Security','-framework','CoreFoundation','-o',D/'AccountCredentialPersistence',R/'account_credential_persistence.c')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1',D/'AccountCredentialPersistence')
for p in [D/'AccountCredentialPersistence',D/'MLAccountSecurity.dylib']:run('codesign','--verify','--strict',p)
(D/'Test Dummy Credentials.command').write_text('''#!/bin/bash
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$(/usr/bin/sw_vers -productVersion)" in 10.9|10.9.*) ;; *) echo 'Run on Mavericks.'; exit 1;; esac
if [ "$(/usr/bin/id -u)" = 0 ]; then echo 'Run without sudo.'; exit 1; fi
OUT="$HERE/Account-credentials-$(/bin/date +%Y%m%d-%H%M%S)-$$"
/bin/mkdir "$OUT" || exit 1
KEYCHAIN="$OUT/disposable-test.keychain"
LOG="$OUT/credentials.log"
PROBE="$HERE/AccountCredentialPersistence"
SHIM="$HERE/MLAccountSecurity.dylib"
/usr/bin/codesign --verify "$PROBE" || exit 1
/usr/bin/codesign --verify "$SHIM" || exit 1
run_phase() {
 /usr/bin/sandbox-exec -D "HOME_KEYCHAINS=$HOME/Library/Keychains" -D "HOME_ACCOUNTS=$HOME/Library/Accounts" -D "HOME_INET=$HOME/Library/Internet Accounts" -f "$HERE/credential-test.sb" "$PROBE" "$1" "$KEYCHAIN" "$SHIM"
}
run_phase create > "$LOG" 2>&1
RESULT=$?
echo "Create phase exit status: $RESULT" >> "$LOG"
if [ "$RESULT" = 0 ]; then
 run_phase verify >> "$LOG" 2>&1
 RESULT=$?
 echo "Reopen phase exit status: $RESULT" >> "$LOG"
fi
if [ -f "$KEYCHAIN" ]; then
 run_phase cleanup >> "$LOG" 2>&1
 CLEANUP=$?
 echo "Cleanup exit status: $CLEANUP" >> "$LOG"
 if [ "$CLEANUP" != 0 ]; then RESULT=$CLEANUP; fi
fi
/bin/cat "$LOG"
/bin/cp "$HERE/manifest.json" "$OUT/manifest.json"
# Diagnostics deliberately exclude the temporary Keychain and any credentials.
/usr/bin/zip -j "$OUT.zip" "$LOG" "$OUT/manifest.json"
echo "Send: $OUT.zip"
echo 'No real account password is required. Press Return to close.'
read -r DONE
exit "$RESULT"
''')
(D/'Test Dummy Credentials.command').chmod(0o755);run('bash','-n',D/'Test Dummy Credentials.command')
(D/'credential-test.sb').write_text('''(version 1)
(allow default)
(deny network-outbound)
(deny file-read* file-write*
 (subpath (param "HOME_KEYCHAINS"))
 (subpath (param "HOME_ACCOUNTS"))
 (subpath (param "HOME_INET")))
''')
(D/'READ ME FIRST.txt').write_text('''DUMMY CREDENTIAL PERSISTENCE TEST 02

Ownership checks now explicitly request the service/realm attribute.
Probe 01 requested no attributes and incorrectly rejected its own entry.

Extract AccountCredentials separately on Mavericks. Run Test Dummy
Credentials.command and send the Account-credentials ZIP. No Google sign-in,
real password, or Keychain approval is needed. Keep experimental sync stopped.
If any authorization prompt appears, cancel it and send the log.

This creates a disposable Keychain inside the test output folder, using a
fixed password for dummy data only. It saves and restores the Keychain search
list immediately around creation; it does not change the default Keychain.
It never requests credentials from existing Keychains. Every credential
query uses the temporary Keychain explicitly. The sandbox blocks networking,
stock account folders and the normal user Keychain folder.

Ordinary dummy entries and private dummy entries use the same provider/login
and server/realm. Tests check that both remain independent; private entries
survive a second process, can be updated, and can be deleted without changing
the ordinary dummy entries. A wrapper delete of an ordinary dummy reference
must be rejected. A private persistent reference is created and resolved.
The temporary Keychain is deleted at the end. Failure is reported without
weakening the sandbox. If cleanup fails, its test-only file may remain in
the output folder; do not share that file.

Diagnostics ZIP contains only status messages and the build manifest, never
the Keychain, dummy values, actual passwords, or existing Keychain details.
This verifies dummy persistence, not Google authentication or app integration.
No restored Calendar or account setup plugin is launched.

Built for x86_64 Mavericks 10.9. Signatures, shell syntax, archive contents,
file hashes and executable modes checked locally. Keychain integration test
has not been executed on the modern build host.
''')
manifest={'build':'account-credential-persistence-02','runtime':'pending Mavericks integration test','files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.is_file()}}
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
zpath=R/'deliverables/Private-Account-Dummy-Credentials-Test-02.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in D.iterdir():z.write(p,'AccountCredentials/'+p.name)
with zipfile.ZipFile(zpath) as z:
 for rel,h in manifest['files_sha256'].items():
  assert hashlib.sha256(z.read('AccountCredentials/'+rel)).hexdigest()==h
  p=D/rel;assert ((z.getinfo('AccountCredentials/'+rel).external_attr>>16)&0o111)==(p.stat().st_mode&0o111)
print(zpath)
