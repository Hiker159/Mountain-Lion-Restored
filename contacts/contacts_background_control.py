"""Optional isolated Contacts sync job. Actual launchctl runs only on Mavericks."""
from __future__ import print_function
import os,sys,plistlib,subprocess,re,tempfile
LABEL='org.ctest.AddressBook.SourceSync';MARKER='MLRestoredContactsManaged'
def read(path):
 if hasattr(plistlib,'load'):
  with open(path,'rb') as f:return plistlib.load(f)
 return plistlib.readPlist(path)
def owned(path):
 if os.path.islink(path):raise RuntimeError('Refusing linked login configuration')
 if not os.path.exists(path):return False
 v=read(path)
 if v.get('Label')!=LABEL or v.get(MARKER)!=1:raise RuntimeError('Unrelated login configuration left unchanged')
 return True
def job(package,home):
 app=os.path.join(package,'Mountain Lion Contacts.app');frameworks=os.path.join(app,'Contents','Frameworks')
 helper=os.path.join(frameworks,'AddressBook.framework','Versions','A','Resources','AddressBookSourceSync.app','Contents','MacOS','AddressBookSourceSync')
 args=['/usr/bin/sandbox-exec']
 for name,path in [('STOCK_CONTACTS','Library/Application Support/AddressBook'),('STOCK_ACCOUNTS','Library/Accounts'),('STOCK_INET','Library/Internet Accounts'),('STOCK_CALENDARS','Library/Calendars'),('STOCK_CONTACT_PREFS','Library/Preferences/com.apple.AddressBook.plist')]:args+=['-D',name+'='+os.path.join(home,path)]
 args+=['-f',os.path.join(package,'contacts-accounts.sb'),'/usr/bin/env','DYLD_INSERT_LIBRARIES='+os.path.join(frameworks,'MLAccountBootstrap.dylib'),helper,'--force-sync','-MLAlternateDataStoreDirectory',os.path.join(home,'Library','Application Support','ML-GContact')]
 log=os.path.join(home,'Library','Logs','ML Contacts Accounts','BackgroundSync.log')
 return {'Label':LABEL,MARKER:1,'ProgramArguments':args,'RunAtLoad':True,'StartInterval':120,'ThrottleInterval':30,'LimitLoadToSessionType':'Aqua','MachServices':{LABEL:True},'StandardOutPath':log,'StandardErrorPath':log}
def run(args):
 p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);out=p.communicate()[0].decode('utf8','replace');return p.returncode,out
def save(value,path):
 owned(path);folder=os.path.dirname(path)
 if not os.path.isdir(folder):os.makedirs(folder)
 fd,tmp=tempfile.mkstemp(prefix='.ml-contacts-',dir=folder);os.close(fd)
 try:
  if hasattr(plistlib,'dump'):
   with open(tmp,'wb') as f:plistlib.dump(value,f)
  else:plistlib.writePlist(value,tmp)
  os.chmod(tmp,0o600);os.rename(tmp,path)
 finally:
  if os.path.exists(tmp):os.remove(tmp)
def main():
 if len(sys.argv)!=2 or sys.argv[1] not in ('enable','disable','status'):return 2
 code,version=run(['/usr/bin/sw_vers','-productVersion'])
 if code or not re.match(r'^10\.9(?:\.|$)',version.strip()) or os.geteuid()==0:raise RuntimeError('Use Mavericks as the logged-in user without sudo')
 mode=sys.argv[1];home=os.path.expanduser('~');package=os.path.dirname(os.path.realpath(__file__));path=os.path.join(home,'Library','LaunchAgents',LABEL+'.plist')
 managed=owned(path)
 if mode=='status':
  print('Managed login job installed: '+str(managed));code,out=run(['/bin/launchctl','list',LABEL]);print(out);return 0
 if mode=='disable':
  if managed:run(['/bin/launchctl','unload',path]);os.remove(path)
  print('Restored Contacts background sync disabled. Contacts/account data retained.');return 0
 app=os.path.join(package,'Mountain Lion Contacts.app');code,out=run(['/usr/bin/codesign','--verify','--deep',app])
 if code:raise RuntimeError(out)
 logdir=os.path.join(home,'Library','Logs','ML Contacts Accounts')
 if not os.path.isdir(logdir):os.makedirs(logdir)
 if managed:run(['/bin/launchctl','unload',path])
 save(job(package,home),path);code,out=run(['/bin/launchctl','load',path])
 print(out)
 if code:raise RuntimeError('Could not load helper; saved job retained for diagnosis/disable')
 print('Background Contacts sync enabled at login and approximately every two minutes.')
 print('Keep this package at: '+package);return 0
if __name__=='__main__':
 try:sys.exit(main())
 except (IOError,OSError,ValueError,RuntimeError) as e:print('Contacts sync setup failed: '+str(e));sys.exit(1)
