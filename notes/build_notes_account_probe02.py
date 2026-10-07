"""Permit Notes plugin initialization with an isolated, empty fixture store."""
from pathlib import Path
import subprocess,shutil,os,json,hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/notes-account-probe-02/NotesAccounts';A=R/'deliverables/Notes-Account-Probe-02.zip';V=R/'work/notes-account-probe02-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*a):return subprocess.check_output([str(x) for x in a],text=True,stderr=subprocess.STDOUT)
shutil.copytree(R/'builds/notes-account-probe-01/NotesAccounts',D,symlinks=True)
s=(R/'notes_account_probe.m').read_text().replace('#import <objc/message.h>','#import <objc/message.h>\n#import <objc/runtime.h>')
s=s.replace('int main(int argc,char **argv)', '''static NSURL *fixtureLibrary;
static id isolatedLibrary(id self,SEL cmd){(void)self;(void)cmd;return fixtureLibrary;}
int main(int argc,char **argv)''').replace('argc!=5','argc!=6')
s=s.replace('puts("NOTES_FRAMEWORK_LOADED");','''puts("NOTES_FRAMEWORK_LOADED");
  fixtureLibrary=[[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[5]] isDirectory:YES] retain];
  Class persistence=NSClassFromString(@"NFPersistenceManager");
  Method library=class_getClassMethod(persistence,NSSelectorFromString(@"libraryURL"));
  char *returnType=library?method_copyReturnType(library):NULL;
  BOOL valid=library&&returnType&&returnType[0]=='@'&&method_getNumberOfArguments(library)==2;
  free(returnType);if(!valid){puts("NOTES_STORAGE_METHOD_MISMATCH");return 6;}
  method_setImplementation(library,(IMP)isolatedLibrary);
  puts("NOTES_FIXTURE_STORAGE_ROUTED");fflush(stdout);''')
s=s.replace('printf("PLUGIN %s %s\\n",ids[i],plugin?"FOUND":"MISSING");','printf("PLUGIN %s %s\\n",ids[i],plugin?"FOUND":"MISSING");fflush(stdout);')
s=s.replace(' }@catch(NSException *e)', '''  id coordinator=((id(*)(id,SEL))objc_msgSend)(persistence,NSSelectorFromString(@"persistentStoreCoordinator"));
  NSArray *stores=((id(*)(id,SEL))objc_msgSend)(coordinator,NSSelectorFromString(@"persistentStores"));
  NSString *prefix=[[fixtureLibrary path] stringByAppendingString:@"/"];
  if(![stores count]){puts("NOTES_FIXTURE_STORE_MISSING");status=7;}
  for(id store in stores){
   NSURL *url=((id(*)(id,SEL))objc_msgSend)(store,NSSelectorFromString(@"URL"));
   BOOL isolated=[[url path] hasPrefix:prefix];
   printf("NOTES_STORE_ISOLATED=%d\\n",isolated?1:0);if(!isolated)status=8;
  }
 }@catch(NSException *e)''')
(R/'notes_account_probe02.m').write_text(s)
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Foundation','-o',D/'NotesAccountProbe',R/'notes_account_probe02.m')
run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1',D/'NotesAccountProbe')
p=D/'Check Notes Accounts.command';s=p.read_text().replace('/bin/mkdir "$OUT"','/bin/mkdir "$OUT"\nFIXTURE="$HERE/Notes-fixture-$(/bin/date +%Y%m%d-%H%M%S)-$$"\n/bin/mkdir "$FIXTURE"')
s=s.replace('"$F/Notes.framework/Versions/A/Notes" >','"$F/Notes.framework/Versions/A/Notes" "$FIXTURE" >')
s=s.replace("echo 'This is a load test; no sign-in or note synchronization was requested.'", "echo 'This is an isolated storage test; no sign-in or note synchronization was requested.'\necho \"Empty fixture database stays at: $FIXTURE (excluded from diagnostics).\"")
p.write_text(s);run('bash','-n',p)
(D/'READ ME FIRST.txt').write_text('''NOTES ACCOUNT STORAGE TEST 02 — MAVERICKS

Extract this new NotesAccounts folder separately and run Check Notes
Accounts.command. Send the diagnostic ZIP. No app window or password
entry is expected; working restored apps can remain as they are.

Probe 01 loaded Notes, Google and Mail but exited while Notes.iaplugin
initialized its database. This revision redirects NFPersistenceManager's
libraryURL to a new empty Notes-fixture folder alongside the test package.
The original Notes database remains blocked by the sandbox. It requests no
account creation, sign-in, sync, or import. Network and Keychain file access
remain blocked. No login job/helper is installed or stock setting changed.

Expected: all three plugins FOUND, NOTES_STORE_ISOLATED=1,
SYSTEM_ACCOUNT_OR_PLUGIN_IMAGES=0 and Probe exit status: 0.
Send the ZIP even if it fails. The ZIP includes only probe.log and manifest;
the empty fixture database is excluded. Fixture folders may be deleted after
testing. Existing Notes data is neither copied nor migrated.
''')
def inventory(root):return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_symlink() or p.is_file()}
(D/'manifest.json').unlink();(D/'manifest.json').write_text(json.dumps({'build':'Notes account storage probe 02','runtime':'pending Mavericks test','change':'Redirect persistence libraryURL to empty fixture; validate actual store URL','account_operations_requested':False,'network':'denied','files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name)
run('codesign','--verify','--strict',V/D.name/'NotesAccountProbe')
for root in [V/D.name/'Contents/Frameworks',V/D.name/'Contents/AccountPlugins']:
 for b in root.iterdir():
  if b.suffix in ['.framework','.iaplugin']:run('codesign','--verify','--deep','--strict',b)
(R/'reports/notes-account-probe02-validation.json').write_text(json.dumps({'archive':str(A),'signatures':'passed after extraction','roundtrip':'hashes, symlinks, executable flags match','shell_syntax':'passed','legacy_execution_on_host':False,'runtime':'pending'},indent=2)+'\n')
print(A)
