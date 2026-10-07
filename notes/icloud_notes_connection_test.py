# -*- coding: utf-8 -*-
from __future__ import print_function
import subprocess,getpass,json,os,datetime,re,sys

def quote(value):
    if '\n' in value or '\r' in value: raise ValueError('Invalid newline')
    return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'

def request(user,password,command):
    config='user = '+quote(user+':'+password)+'\n'
    args=['/usr/bin/curl','--config','-','--silent','--show-error','--connect-timeout','20','--max-time','45','--proto','=imaps','--url','imaps://imap.mail.me.com/','--request',command]
    p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err=p.communicate(config.encode('utf-8'))
    return p.returncode,out.decode('utf-8','replace')

def main():
    print('Read-only iCloud legacy Notes check. This does not change accounts or notes.')
    user=(raw_input('iCloud Mail email: ') if sys.version_info[0]==2 else input('iCloud Mail email: ')).strip()
    password=getpass.getpass('App-specific password (hidden): ')
    report={'test':'iCloud legacy Notes IMAP check 01','credentials_saved':False,'note_content_downloaded':False}
    try:
        code,listing=request(user,password,'LIST "" "*"')
        report['folder_list_curl_exit']=code
        # Folder names and server responses remain in memory and are never logged.
        found=any(re.search(r'(?:"Notes"|\bNotes)\s*$',line,re.I) for line in listing.splitlines()) if code==0 else False
        report['legacy_notes_folder_found']=found
        if found:
            code,response=request(user,password,'EXAMINE "Notes"')
            report['read_only_examine_curl_exit']=code
            match=re.search(r'^\*\s+(\d+)\s+EXISTS\b',response,re.M|re.I)
            report['message_count']=int(match.group(1)) if match else None
        listing=None
    except Exception as e:
        report['local_error_type']=type(e).__name__
    finally:
        password=None
    filename=os.path.expanduser('~/Desktop/iCloud-notes-connection-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
    with open(filename,'w') as f:json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2));print('Send this report: '+filename)
    print('Curl exit 0 means success; 67 indicates login rejection; 60 indicates certificate verification failure.')
if __name__=='__main__': main()
