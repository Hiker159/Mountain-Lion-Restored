# -*- coding: utf-8 -*-
"""One-time setup in each Mavericks user's Aqua session; never run as root."""
from __future__ import print_function
import os,sys,subprocess,json,datetime
SUITE='/Applications/Mountain Lion Restored Apps'
def main():
 if os.geteuid()==0:return 2
 version=subprocess.check_output(['/usr/bin/sw_vers','-productVersion']).decode('ascii').strip()
 if version!='10.9' and not version.startswith('10.9.'):return 2
 state=os.path.expanduser('~/Library/Application Support/ML Restored Apps')
 if not os.path.isdir(state):os.makedirs(state,0o700)
 marker=os.path.join(state,'background-setup.json')
 # After first setup, the user's Enable/Disable choices take precedence.
 if os.path.isfile(marker):return 0
 results=[]
 with open(os.path.join(state,'BackgroundSetup.log'),'ab') as log:
  for folder,script in [('Calendar','calendar_login_control.py'),('Contacts','contacts_background_control.py')]:
   args=['/usr/bin/python',os.path.join(SUITE,folder,script),'enable']
   results.append(subprocess.call(args,stdout=log,stderr=subprocess.STDOUT))
 if any(results):return 1
 temp=marker+'.tmp'
 with open(temp,'w') as f:json.dump({'setup_complete':True,'helpers':['Calendar','Contacts'],'date':datetime.datetime.now().isoformat()},f)
 os.chmod(temp,0o600);os.rename(temp,marker)
 return 0
if __name__=='__main__':sys.exit(main())
