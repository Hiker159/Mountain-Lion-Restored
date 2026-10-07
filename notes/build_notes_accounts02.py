"""Close IMCore's indirect stock AddressBook import and replace stock Accounts menu."""
from pathlib import Path
import subprocess,shutil,os,json,hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();D=R/'builds/notes-private-accounts-02/NotesAccounts';A=R/'deliverables/Notes-Private-Accounts-Test-02.zip';V=R/'work/notes-private-accounts02-verification'
if any(p.exists() for p in (D,A,V)):raise SystemExit('Existing artifacts preserved')
def run(*a):return subprocess.check_output([str(x) for x in a],text=True,stderr=subprocess.STDOUT)
shutil.copytree(R/'builds/notes-private-accounts-01/NotesAccounts',D,symlinks=True)
APP=D/'Mountain Lion Notes.app';F=APP/'Contents/Frameworks'
frame=F/'IMCore.framework';shutil.copytree(R/'mavericks-originals/System/Library/PrivateFrameworks/IMCore.framework',frame,symlinks=True)
# Do not bundle or launch the unrelated system messaging daemon.
shutil.rmtree(frame/'imagent.app')
b=frame/'Versions/A/IMCore'
if run('lipo','-archs',b).split()!=['x86_64']:
 tmp=b.with_name(b.name+'.thin');run('lipo',b,'-thin','x86_64','-output',tmp);os.replace(tmp,b)
old='/System/Library/Frameworks/AddressBook.framework/Versions/A/AddressBook';new='@loader_path/../../../AddressBook.framework/Versions/A/AddressBook'
assert old in run('otool','-L',b)
# Check the private AB exports requested by this exact Mavericks IMCore before routing.
imports=set(l.split()[-1] for l in run('nm','-u',b).splitlines() if l.split())
exports=set(l.split()[-1] for l in run('nm','-gU',F/'AddressBook.framework/Versions/A/AddressBook').splitlines() if l.split())
needed={x for x in imports if x.startswith(('_AB','_kAB','_OBJC_CLASS_$_AB','_OBJC_METACLASS_$_AB'))}
assert not needed-exports,sorted(needed-exports)
run('install_name_tool','-change',old,new,'-id','@rpath/IMCore.framework/Versions/A/IMCore',b)
main=APP/'Contents/PrivatePanes/InternetAccounts.prefPane/Contents/MacOS/InternetAccounts'
run('install_name_tool','-change','/System/Library/PrivateFrameworks/IMCore.framework/Versions/A/IMCore','@loader_path/../../../../Frameworks/IMCore.framework/Versions/A/IMCore',main)
s=(R/'notes_account_ui.m').read_text()
s=s.replace('NSMenuItem *item=[[[NSMenuItem alloc]', '''// Remove the stock System Preferences command and any earlier injected entry.
 for(NSMenuItem *old in [[[menu itemArray] copy] autorelease]){
  NSString *title=[[old title] lowercaseString];
  NSString *action=[NSStringFromSelector([old action]) lowercaseString];
  if([title rangeOfString:@"accounts"].location!=NSNotFound || (action&&[action rangeOfString:@"account"].location!=NSNotFound)) [menu removeItem:old];
 }
 NSMenuItem *item=[[[NSMenuItem alloc]''')
(R/'notes_account_ui02.m').write_text(s)
lib=F/'MLNotesAccountsUI.dylib'
run('xcrun','clang','-arch','x86_64','-mmacosx-version-min=10.9','-dynamiclib','-fno-objc-arc','-Werror','-Wno-deprecated-declarations','-Wl,-no_fixup_chains','-framework','Cocoa','-Wl,-install_name,@rpath/MLNotesAccountsUI.dylib','-o',lib,R/'notes_account_ui02.m')
for t in [frame,main.parent.parent.parent,lib,APP]:run('codesign','--force','--sign','-','--timestamp=none','--digest-algorithm=sha1','--requirements','=library => true',t)
run('codesign','--verify','--deep','--strict',APP)
p=D/'READ ME FIRST.txt';s=p.read_text().replace('ACCOUNTS TEST 01','ACCOUNTS TEST 02');s+='\nTEST 02 FIXES\nThe app menu should now contain one Accounts entry, opening the private panel.\nMavericks IMCore is bundled with its AddressBook import redirected privately;\nthe stock framework isolation guard remains enabled. Repeat the Test 01\nsteps and send the collected ZIP even if panel loading fails.\n';p.write_text(s)
for p in D.glob('*.command'):run('bash','-n',p)
assert (b.parent/new[13:]).exists()
def inventory(root):return {str(p.relative_to(root)):({'link':os.readlink(p)} if p.is_symlink() else {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'executable':bool(p.stat().st_mode&0o111)}) for p in root.rglob('*') if p.is_symlink() or p.is_file()}
(D/'manifest.json').unlink();(D/'manifest.json').write_text(json.dumps({'build':'Notes private accounts 02','runtime':'pending Mavericks test','change':'Replace Accounts menu; private Mavericks IMCore closes stock AddressBook reentry','IMCore_required_AddressBook_exports':sorted(needed),'files':inventory(D)},indent=2)+'\n')
run('ditto','-c','-k','--keepParent',D,A);run('ditto','-x','-k',A,V);assert inventory(D)==inventory(V/D.name);run('codesign','--verify','--deep','--strict',V/D.name/APP.name)
(R/'reports/notes-accounts02-validation.json').write_text(json.dumps({'archive':str(A),'signatures':'passed after extraction','roundtrip':'hashes, links, modes match','IMCore_required_AB_symbols':'all available in private AB','runtime':'pending','legacy_execution_on_host':False},indent=2)+'\n');print(A)
