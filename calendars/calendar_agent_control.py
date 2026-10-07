"""Start/stop only the session-scoped Mavericks Calendar test agent.
Compatible with Mavericks' system Python 2.7 and Python 3 for offline tests.
No login item, LaunchAgents-directory entry, or privileged service is installed.
"""
from __future__ import print_function
import json, os, plistlib, re, subprocess, sys, time
LABEL='org.local.CalendarAgent'

def run(args):
    p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    out=p.communicate()[0].decode('utf-8','replace')
    return p.returncode,out

def paths(package,home):
    app=os.path.join(package,'Mountain Lion Calendar.app')
    state=os.path.join(home,'Library','Application Support','ML-Calendar','Agent')
    return {'app':app,'helper':os.path.join(app,'Contents','Helpers','Mountain Lion Calendar Alerts.app'),
            'state':state,'plist':os.path.join(state,LABEL+'.plist'),
            'log':os.path.join(state,'CalendarAgent.log'),
            'data':os.path.join(home,'Library','MLCalData'),
            'support':os.path.join(home,'Library','Application Support','ML-Calendar')}

def make_job(package,home):
    p=paths(package,home)
    args=['/usr/bin/sandbox-exec',
      '-D','STOCK_CALENDARS='+os.path.join(home,'Library','Calendars'),
      '-D','STOCK_ICAL_SUPPORT='+os.path.join(home,'Library','Application Support','iCal'),
      '-D','STOCK_CONTACTS='+os.path.join(home,'Library','Application Support','AddressBook'),
      '-D','STOCK_ICAL_PREFS='+os.path.join(home,'Library','Preferences','com.apple.iCal.plist'),
      '-f',os.path.join(package,'calendar-agent-trial.sb')]
    executable=os.path.join(p['helper'],'Contents','MacOS','CalendarAgent')
    wake_library=os.path.join(p['app'],'Contents','Frameworks','MLCalendarWakeRecovery.dylib')
    job={'Label':LABEL,'ProgramArguments':args+['/usr/bin/env',
         'DYLD_INSERT_LIBRARIES='+wake_library,executable,
         '-MLCalDataDirectory',p['data'],'-iCalApplicationSupportDirectory',p['support']],
         'MachServices':{LABEL:True,LABEL+'.proxy':True},
         'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':30,'ExitTimeOut':5,
         'LimitLoadToSessionType':'Aqua',
         'EnvironmentVariables':{'NSRunningFromLaunchd':'1','DYLD_PRINT_LIBRARIES':'1'},
         'StandardOutPath':p['log'],'StandardErrorPath':p['log']}
    return job,args,p

def write_plist(value,path):
    if hasattr(plistlib,'dump'):
        with open(path,'wb') as f:plistlib.dump(value,f)
    else:plistlib.writePlist(value,path)

def process_pid(output):
    match=re.search(r'"?PID"?\s*=\s*(\d+)',output)
    return int(match.group(1)) if match else None

def stop(p):
    code,out=run(['/bin/launchctl','list',LABEL])
    if code:
        print('The Calendar test helper is not loaded.')
        return 0
    code,out=run(['/bin/launchctl','remove',LABEL])
    print(out)
    if code:return code
    print('Stopped the Calendar test helper. Calendar data is retained.')
    print('Notifications already queued with macOS may still appear.')
    return 0

def main():
    if len(sys.argv)!=2 or sys.argv[1] not in ('start','stop','status'):
        print('Usage: calendar_agent_control.py start|stop|status');return 2
    code,version=run(['/usr/bin/sw_vers','-productVersion'])
    if code or not re.match(r'^10\.9(?:\.|\s|$)',version):
        print('This helper is for the Mavericks laptop only.');return 2
    if os.geteuid()==0:
        print('Run as the temporary logged-in user, without sudo.');return 2
    package=os.path.dirname(os.path.realpath(__file__))
    home=os.path.expanduser('~')
    job,args,p=make_job(package,home)
    mode=sys.argv[1]
    if mode=='status':
        code,out=run(['/bin/launchctl','list',LABEL]);print(out);return code
    if mode=='stop':return stop(p)
    for target in (p['app'],p['helper']):
        code,out=run(['/usr/bin/codesign','--verify','--deep',target])
        if code:print(out);return code
    # Refresh only this helper's app registration; never clear global icon caches.
    register='/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister'
    code,out=run([register,'-f',p['helper']])
    if code:print('Helper icon registration failed; continuing with existing registration.\n'+out)
    code,out=run(args+['/usr/bin/true'])
    if code:print('Protective profile failed; helper was not started.\n'+out);return code
    for folder in (p['state'],p['data']):
        if not os.path.isdir(folder):os.makedirs(folder)
    # Replace only our own test job; never touch com.apple.CalendarAgent.
    if stop(p):return 1
    if os.path.isfile(p['log']):
        previous=p['log']+'.previous'
        if os.path.exists(previous):os.remove(previous)
        os.rename(p['log'],previous)
    write_plist(job,p['plist'])
    os.chmod(p['plist'],0o600)
    code,out=run(['/bin/launchctl','load',p['plist']])
    print(out)
    if code:return code
    prior=None;stable=0
    for _ in range(20):
        time.sleep(0.5)
        code,out=run(['/bin/launchctl','list',LABEL])
        pid=process_pid(out) if code==0 else None
        stable=stable+1 if pid and pid==prior else 0
        prior=pid
        if stable>=5:
            print('Calendar test helper is running (PID %s). This is a process check, not an alert-delivery test.'%pid)
            print('It remains active after Calendar quits, until stopped or logout.')
            return 0
    print('Helper did not remain running. Its log is: '+p['log'])
    print(out)
    # Stop crash loops while preserving logs for diagnosis.
    stop(p)
    return 1

if __name__=='__main__':sys.exit(main())
