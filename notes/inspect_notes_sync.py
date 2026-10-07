# -*- coding: utf-8 -*-
from __future__ import print_function
import os,subprocess,datetime,shutil,json

def main():
    here=os.path.dirname(os.path.abspath(__file__))
    out=os.path.expanduser('~/Desktop/Notes-sync-inspection-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
    os.mkdir(out)
    ps=subprocess.check_output(['/bin/ps','-axo','pid=,comm=']).decode('utf-8','replace')
    targets=[]
    for line in ps.splitlines():
        parts=line.strip().split(None,1)
        if len(parts)==2 and parts[1].endswith('/Mountain Lion Notes.app/Contents/MacOS/Notes'):
            targets.append(int(parts[0]))
    report={'test':'Notes sync stack inspection 01','restored_process_count':len(targets),'samples':[]}
    if not targets:print('Restored Notes is not running. Open it, reproduce the missing sync, then run this again.')
    for pid in targets:
        name='notes-stack-'+str(pid)+'.txt'
        code=subprocess.call(['/usr/bin/sample',str(pid),'5','10','-file',os.path.join(out,name)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        report['samples'].append({'pid':pid,'exit':code,'file':name})
    print('Optional: drag the NotesAccounts folder containing Collect Private Notes Log.command here, then press Return. Press Return alone to skip.')
    folder=(raw_input('NotesAccounts folder: ') if __import__('sys').version_info[0]==2 else input('NotesAccounts folder: ')).strip()
    # Finder drag paths are shell-escaped; parse without executing anything.
    if folder:
        import shlex
        paths=shlex.split(folder)
        if len(paths)==1:
            folder=paths[0]
            collector=os.path.join(folder,'collect_notes_private.py')
            if os.path.isfile(collector):
                with open(os.path.join(out,'notes.log'),'wb') as f:
                    subprocess.call(['/usr/bin/python',collector],stdout=f,stderr=subprocess.STDOUT)
            manifest=os.path.join(folder,'manifest.json')
            if os.path.isfile(manifest):shutil.copy2(manifest,out)
    with open(os.path.join(out,'inspection.json'),'w') as f:json.dump(report,f,indent=2)
    subprocess.check_call(['/usr/bin/ditto','-c','-k','--keepParent',out,out+'.zip'])
    print('Send: '+out+'.zip')
if __name__=='__main__':main()
