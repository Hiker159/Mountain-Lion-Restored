"""Extract only selected installer assets from the odc cpio stream."""
from pathlib import Path,PurePosixPath
import bz2,os,stat,json,subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"calendars"))
from project_layout import project_root
R=project_root();dest=R/'work/contacts-account-assets'
prefixes=('System/Library/InternetAccounts/AddressBook.iaplugin/','System/Library/Address Book Plug-Ins/CardDAVPlugin.sourcebundle/')
dest.mkdir(parents=True,exist_ok=True);selected=[]
expected={name.removeprefix('./') for name in subprocess.check_output(['lsbom','-s',str(R/'work/Essentials/Bom')],text=True).splitlines() if any(name.removeprefix('./').startswith(x) or name.removeprefix('./')==x.rstrip('/') for x in prefixes)}
assert expected
remaining=set(expected)
def read_exact(f,n):
 b=f.read(n)
 if len(b)!=n:raise RuntimeError('Truncated payload')
 return b
with bz2.open(R/'work/Essentials/Payload','rb') as f:
 while True:
  h=read_exact(f,76);assert h[:6]==b'070707'
  mode=int(h[18:24],8);ns=int(h[59:65],8);size=int(h[65:76],8)
  name=read_exact(f,ns).rstrip(b'\0').decode();name=name.removeprefix('./')
  if name=='TRAILER!!!':break
  keep=any(name.startswith(x) or name==x.rstrip('/') for x in prefixes)
  if keep:
   rel=PurePosixPath(name);assert not rel.is_absolute() and '..' not in rel.parts
   p=dest/str(rel);p.parent.mkdir(parents=True,exist_ok=True)
   data=read_exact(f,size)
   if stat.S_ISDIR(mode):p.mkdir(exist_ok=True)
   elif stat.S_ISLNK(mode):
    target=data.decode();assert not target.startswith('/') and '..' not in PurePosixPath(target).parts
    if not p.exists() and not p.is_symlink():p.symlink_to(target)
   elif stat.S_ISREG(mode):p.write_bytes(data);p.chmod(mode&0o777)
   else:raise RuntimeError('Unexpected selected file type')
   selected.append(name);remaining.discard(name)
   if not remaining:break
  else:
   while size:
    chunk=read_exact(f,min(size,1024*1024));size-=len(chunk)
assert not remaining, sorted(remaining)
(R/'reports/contacts-plugin-extraction.json').write_text(json.dumps({'selected_files':len(selected),'prefixes':prefixes,'source':'Mountain Lion Essentials payload','destination':str(dest)},indent=2)+'\n')
print('Selected assets extracted:',len(selected),flush=True)
