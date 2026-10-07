import tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
import calendar_login_control as l
class LoginTests(unittest.TestCase):
 def test_marked_atomic_save_and_update(self):
  with tempfile.TemporaryDirectory() as d:
   p=os.path.join(d,'LaunchAgents','test.plist');job={'Label':l.c.LABEL,'ProgramArguments':['path with spaces']}
   l.save(job,p);self.assertTrue(l.owned(p));self.assertEqual(l.read(p)['ProgramArguments'],job['ProgramArguments']);self.assertEqual(os.stat(p).st_mode&0o777,0o600)
   job['ProgramArguments']=['new path'];l.save(job,p);self.assertEqual(l.read(p)['ProgramArguments'],['new path'])
 def test_refuses_unowned_or_linked_file(self):
  with tempfile.TemporaryDirectory() as d:
   p=os.path.join(d,'test.plist');l.c.write_plist({'Label':l.c.LABEL},p);before=Path(p).read_bytes()
   with self.assertRaises(RuntimeError):l.save({'Label':l.c.LABEL},p)
   self.assertEqual(Path(p).read_bytes(),before)
   q=os.path.join(d,'link');os.symlink(p,q)
   with self.assertRaises(RuntimeError):l.owned(q)
 def test_refuses_host_before_mutation(self):
  with patch.object(l.sys,'argv',['test','enable']),patch.object(l.c,'run',return_value=(0,'15.7.9')),patch.object(l,'save') as save:
   self.assertEqual(l.main(),2);save.assert_not_called()

class LifecycleTests(unittest.TestCase):
 def exercise(self,mode,home,start_result=0):
  package=os.path.join(home,'Package With Spaces');os.makedirs(package,exist_ok=True)
  with patch.object(l,'__file__',os.path.join(package,'calendar_login_control.py')),patch.object(l.os.path,'expanduser',return_value=home),patch.object(l.os,'geteuid',return_value=501),patch.object(l.sys,'argv',['test',mode]),patch.object(l.c,'run',return_value=(0,'10.9.5')),patch.object(l.c,'main',return_value=start_result),patch.object(l.c,'stop',return_value=0) as stop:
   result=l.main()
   return result,stop.call_count
 def test_failed_start_does_not_enable_login(self):
  with tempfile.TemporaryDirectory() as d:
   result,_=self.exercise('enable',d,1);self.assertEqual(result,1)
   self.assertFalse(os.path.exists(os.path.join(d,'Library','LaunchAgents',l.c.LABEL+'.plist')))
 def test_enable_disable_retains_user_data(self):
  with tempfile.TemporaryDirectory() as d:
   data=Path(l.c.paths(os.path.join(d,'Package With Spaces'),d)['data']);data.mkdir(parents=True);(data/'keep').write_text('event fixture')
   result,_=self.exercise('enable',d);self.assertEqual(result,0)
   p=os.path.join(d,'Library','LaunchAgents',l.c.LABEL+'.plist');self.assertTrue(l.owned(p))
   job=l.read(p);self.assertEqual(job['MachServices'],{l.c.LABEL:True,l.c.LABEL+'.proxy':True})
   inserted=next(x.split('=',1)[1].split(':') for x in job['ProgramArguments'] if x.startswith('DYLD_INSERT_LIBRARIES='))
   self.assertIn(os.path.join(os.path.realpath(d),'Package With Spaces','Mountain Lion Calendar.app','Contents','Frameworks','MLCalendarWakeRecovery.dylib'),inserted)
   if l.c.LABEL=='org.authx.CalendarAgent':self.assertIn(os.path.join(os.path.realpath(d),'Package With Spaces','Mountain Lion Calendar.app','Contents','Frameworks','MLAccountBootstrap.dylib'),inserted)
   result,count=self.exercise('disable',d);self.assertEqual((result,count),(0,1));self.assertFalse(os.path.exists(p));self.assertEqual((data/'keep').read_text(),'event fixture')

if __name__=='__main__':unittest.main()
