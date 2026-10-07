"""Optional user login persistence for the packaged Calendar helper (Python 2/3).
Only this package's marked LaunchAgent is written/removed. Never run on host.
"""
from __future__ import print_function
import os,sys,plistlib
import calendar_agent_control as c
MARKER='MLRestoredAppsManaged'

def read(path):
    if hasattr(plistlib,'load'):
        with open(path,'rb') as f:return plistlib.load(f)
    return plistlib.readPlist(path)

def owned(path):
    if os.path.islink(path):raise RuntimeError('Refusing a linked login configuration.')
    if not os.path.exists(path):return False
    value=read(path)
    if value.get(MARKER)!=1 or value.get('Label')!=c.LABEL:
        raise RuntimeError('An unrelated login configuration occupies this filename; left unchanged.')
    return True

def save(job,path):
    owned(path)
    folder=os.path.dirname(path)
    if not os.path.isdir(folder):os.makedirs(folder)
    # Unique temporary file, then atomic replacement; no partial login plist.
    import tempfile
    fd,tmp=tempfile.mkstemp(prefix='.ml-calendar-',dir=folder);os.close(fd)
    try:
        value=dict(job);value[MARKER]=1
        c.write_plist(value,tmp);os.chmod(tmp,0o600);os.rename(tmp,path)
    finally:
        if os.path.exists(tmp):os.remove(tmp)

def main():
    if len(sys.argv)!=2 or sys.argv[1] not in ('open','enable','disable'):
        print('Usage: calendar_login_control.py open|enable|disable');return 2
    mode=sys.argv[1]
    code,version=c.run(['/usr/bin/sw_vers','-productVersion'])
    if code or not c.re.match(r'^10\.9(?:\.|\s|$)',version) or os.geteuid()==0:
        print('Use the logged-in Mavericks user, without sudo.');return 2
    package=os.path.dirname(os.path.realpath(__file__));home=os.path.expanduser('~')
    job,args,p=c.make_job(package,home)
    login=os.path.join(home,'Library','LaunchAgents',c.LABEL+'.plist')
    managed=owned(login)
    if mode=='disable':
        if managed:os.remove(login)
        result=c.stop(p)
        print('Automatic Calendar alerts at login are disabled. Event data is retained.')
        return result
    # Reuse a verified, running helper only when its saved job matches this path.
    reusable=False
    if os.path.isfile(p['plist']):
        try:
            saved=read(p['plist'])
            code,out=c.run(['/bin/launchctl','list',c.LABEL])
            reusable=code==0 and c.process_pid(out) and saved==job
        except (IOError,ValueError):pass
    if reusable:
        for target in (p['app'],p['helper']):
            code,out=c.run(['/usr/bin/codesign','--verify','--deep',target])
            if code:print(out);return code
        print('The existing Calendar alert helper is running.')
    else:
        previous=sys.argv;sys.argv=[c.__file__,'start']
        try:result=c.main()
        finally:sys.argv=previous
        if result:return result
    if mode=='enable' or managed:
        save(job,login)
        print('Calendar alerts will start when this user logs in. Keep this package at: '+package)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (IOError,OSError,ValueError,RuntimeError) as e:
        print('Calendar setup could not complete: '+str(e));sys.exit(1)
