"""Host-only lifecycle tests; subprocesses and waiting are mocked throughout."""
import contextlib,io,os,tempfile,unittest
from unittest.mock import patch
import calendar_agent_control as c

class LifecycleTests(unittest.TestCase):
    def exercise(self, pid_output):
        calls=[]
        with tempfile.TemporaryDirectory() as home:
            package=os.path.join(home,'Test Package')
            os.mkdir(package)
            def fake_run(args):
                calls.append(args)
                if args[0]=='/usr/bin/sw_vers':return 0,'10.9.5\n'
                if args[:3]==['/bin/launchctl','list',c.LABEL]:
                    # Before load there is no job; after load use the fixture.
                    if any(x[:2]==['/bin/launchctl','load'] for x in calls):
                        return 0,pid_output
                    return 1,'not loaded'
                return 0,''
            with patch.object(c,'__file__',os.path.join(package,'calendar_agent_control.py')), \
                 patch.object(c.sys,'argv',['control','start']), \
                 patch.object(c.os.path,'expanduser',return_value=home), \
                 patch.object(c.os,'geteuid',return_value=501), \
                 patch.object(c,'run',side_effect=fake_run), \
                 patch.object(c.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
                result=c.main()
        return result,calls

    def test_stable_background_process(self):
        result,calls=self.exercise('{ "PID" = 321; }')
        self.assertEqual(result,0)
        self.assertFalse(any(x[:2]==['/bin/launchctl','remove'] for x in calls))

    def test_failed_start_stops_crash_loop(self):
        result,calls=self.exercise('{ "LastExitStatus" = 9; }')
        self.assertEqual(result,1)
        self.assertIn(['/bin/launchctl','remove',c.LABEL],calls)

    def test_refuses_non_mavericks(self):
        with patch.object(c.sys,'argv',['control','start']), \
             patch.object(c,'run',return_value=(0,'15.7.9\n')) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(c.main(),2)
            self.assertEqual(run.call_count,1)

    def test_refuses_root(self):
        with patch.object(c.sys,'argv',['control','start']), \
             patch.object(c,'run',return_value=(0,'10.9.5\n')) as run, \
             patch.object(c.os,'geteuid',return_value=0), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(c.main(),2)
            self.assertEqual(run.call_count,1)

if __name__=='__main__':unittest.main()
