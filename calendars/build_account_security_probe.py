from pathlib import Path
import subprocess,shutil,os,json,hashlib,zipfile,stat
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/account-security-probe-01/AccountBackend';F=D/'Frameworks'
def run(*a):
 p=subprocess.run([str(x) for x in a],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 return p.stdout
if D.exists():raise RuntimeError('Build destination exists')
shutil.copytree(R/'builds/account-plugin-probe-01/AccountBackend',D,symlinks=True)
shim=F/'MLAccountSecurity.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fblocks','-Werror','-Wno-deprecated-declarations','-framework','CoreFoundation','-Wl,-no_fixup_chains,-reexport_framework,Security','-Wl,-install_name,@rpath/MLAccountSecurity.dylib','-Wl,-compatibility_version,55179.3.0','-Wl,-current_version,55179.13.0','-o',shim,R/'account_security_compat.c')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1',shim)
# Check every native Security symbol required by the wrapper against 10.9.
security=R/'mavericks-originals/System/Library/Frameworks/Security.framework/Versions/A/Security'
exports={l.split()[-1] for l in run('nm','-g',security).splitlines() if len(l.split())>=3 and l.split()[-2]!='U'}
needed={l.strip() for l in run('nm','-u',shim).splitlines() if l.strip().startswith('_kSec')}
assert not needed-exports,needed-exports
edges=[];bundles=set();old='/System/Library/Frameworks/Security.framework/Versions/A/Security'
for area in [F,D/'AccountPlugins']:
 for p in area.rglob('*'):
  if p.is_symlink() or not p.is_file() or p==shim:continue
  if p.read_bytes()[:4]!=b'\xcf\xfa\xed\xfe':continue
  deps=[l.strip().split(' (')[0] for l in run('otool','-L',p).splitlines()[1:]]
  if old not in deps:continue
  new='@loader_path/'+os.path.relpath(shim,p.parent);run('install_name_tool','-change',old,new,p)
  edges.append({'binary':str(p.relative_to(D)),'security_wrapper':new})
  owners=[a for a in p.parents if a.suffix in ['.framework','.iaplugin','.app','.xpc','.bundle']]
  bundles.update(owners)
  if not owners:run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1',p)
for b in sorted(bundles,key=lambda p:len(p.parts),reverse=True):
 run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',b);run('codesign','--verify','--deep','--strict',b)
probe=D/'AccountSecurityProbe'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','CoreFoundation','-o',probe,R/'account_security_probe.c')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1',probe)
for p in [shim,probe]:run('codesign','--verify','--strict',p)
launcher=D/'Check Account Backend.command';s=launcher.read_text();start=s.index('/bin/cat "$OUT/backend.log"')
addition='''/usr/bin/sandbox-exec \\
 -D "HOME_ACCOUNTS=$HOME/Library/Accounts" \\
 -D "HOME_INET_ACCOUNTS=$HOME/Library/Internet Accounts" \\
 -D "HOME_KEYCHAINS=$HOME/Library/Keychains" \\
 -D "HOME_CALENDARS=$HOME/Library/Calendars" \\
 -D "HOME_ADDRESSBOOK=$HOME/Library/Application Support/AddressBook" \\
 -f "$HERE/backend-probe.sb" "$HERE/AccountSecurityProbe" \\
 "$F/MLAccountSecurity.dylib" >> "$OUT/backend.log" 2>&1
SECURITY_RESULT=$?
echo "Credential wrapper exit status: $SECURITY_RESULT" >> "$OUT/backend.log"
if [ "$SECURITY_RESULT" != 0 ]; then RESULT=$SECURITY_RESULT; fi
'''
launcher.write_text(s[:start]+addition+s[start:]);run('bash','-n',launcher)
(D/'READ ME FIRST.txt').write_text('''PRIVATE ACCOUNT CREDENTIAL WRAPPER PROBE 01

Extract AccountBackend separately on Mavericks. Keep CalendarNetwork and
background GoogleSync stopped. Run Check Account Backend.command; send the
resulting ZIP. No password, account setup, or Keychain approval is needed.

Repeats private library, storage-path and plugin loading checks after routing
bundled Security imports through a credential wrapper. It then verifies 15
wrapper exports and checks two invalid queries are rejected before reaching
Keychain. Expected: previous checks pass; CREDENTIAL_WRAPPER_CHECK_PASS and
Credential wrapper exit status: 0. It creates no credential or account.

The wrapper namespaces generic-password service names and Internet-password
security domains. Dictionary operations and legacy searches use those names.
Reference-based content access, mutation/deletion and persistent references
check the item's namespace attributes. Unqualified/unsupported queries are
rejected. Other Security APIs remain Mavericks APIs via reexport.

This is still not a sign-in test. The sandbox continues to block networking
and stock account/Keychain/calendar/contact folders. No native Keychain
operation is requested by the two invalid-query tests. Initialization may
attempt restricted APIs; report failures instead of removing the sandbox.

In-memory tests passed locally for dictionary create/read/update/delete,
namespace separation, original query preservation, foreign-reference rejection
and malformed queries; they use a fake provider and no host Keychain data.
Actual credential persistence, authentication and sync remain untested.
Do not install these frameworks into restored apps or sign in yet.

Compiled for x86_64 Mavericks 10.9. Security constants checked against the
Mavericks installer; framework signatures, dependency redirects, launcher and
archive hashes/modes/symlinks verified. Legacy binaries not run on build host.
''')
(R/'reports/account-security-probe01-dependencies.json').write_text(json.dumps({'redirected_edges':edges,'mavericks_security_constants':sorted(needed),'unit_tests':'in-memory provider passed','runtime':'pending; no actual credential operations in this probe'},indent=2)+'\n')
manifest={'build':'account-security-probe-01','runtime':'pending Mavericks wrapper test','files_sha256':{str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in D.rglob('*') if p.is_file() and not p.is_symlink() and p.name!='manifest.json'}}
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
zpath=R/'deliverables/Private-Account-Credential-Probe-01.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  n='AccountBackend/'+str(p.relative_to(D))
  if p.is_symlink():
   info=zipfile.ZipInfo(n);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,os.readlink(p))
  elif p.is_file():z.write(p,n)
with zipfile.ZipFile(zpath) as z:
 for rel,h in manifest['files_sha256'].items():assert hashlib.sha256(z.read('AccountBackend/'+rel)).hexdigest()==h
 for p in D.rglob('*'):
  n='AccountBackend/'+str(p.relative_to(D))
  if p.is_symlink():assert z.read(n).decode()==os.readlink(p)
  elif p.is_file():assert ((z.getinfo(n).external_attr>>16)&0o111)==(p.stat().st_mode&0o111)
print(str(zpath));print('Security redirects:',len(edges))
