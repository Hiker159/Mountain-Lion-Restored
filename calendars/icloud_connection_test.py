# -*- coding: utf-8 -*-
from __future__ import print_function
import subprocess,getpass,json,os,datetime
try:
 from urllib.parse import urlparse,urljoin
except ImportError:
 from urlparse import urlparse,urljoin
import xml.etree.ElementTree as ET
QUERY='''<?xml version="1.0" encoding="utf-8"?><d:propfind xmlns:d="DAV:"><d:prop><d:current-user-principal/><d:resourcetype/></d:prop></d:propfind>'''
def quote(value):
 if '\n' in value or '\r' in value:raise ValueError('Invalid newline')
 return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'
def allowed(url):
 p=urlparse(url)
 return p.scheme=='https' and (p.hostname=='icloud.com' or (p.hostname or '').endswith('.icloud.com')) and not p.username and p.port in (None,443)
def request(url,user,password):
 assert allowed(url),'Unexpected destination'
 config='user = '+quote(user+':'+password)+'\n'
 cmd=['/usr/bin/curl','--config','-','--silent','--show-error','--connect-timeout','20','--max-time','45','--proto','=https','--request','PROPFIND','--header','Depth: 0','--header','Content-Type: application/xml; charset=utf-8','--data-binary',QUERY,'--include',url]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 out,err=p.communicate(config.encode('utf-8'))
 if p.returncode:return {'curl_exit':p.returncode},None,None
 text=out.decode('utf-8','replace');headers,sep,body=text.partition('\r\n\r\n')
 # Curl can include a proxy CONNECT response before the actual response.
 while body.startswith('HTTP/'):
  headers,sep,body=body.partition('\r\n\r\n')
 status=int(headers.splitlines()[0].split()[1]);location=None
 for line in headers.splitlines()[1:]:
  if line.lower().startswith('location:'):location=urljoin(url,line.split(':',1)[1].strip())
 principal=None
 try:
  root=ET.fromstring(body)
  node=root.find('.//{DAV:}current-user-principal/{DAV:}href')
  if node is not None and node.text:principal=urljoin(url,node.text)
 except ET.ParseError:pass
 return {'http_status':status,'principal_discovered':bool(principal)},location,principal
def main():
 print('iCloud connection test - no account or calendar data will be changed.')
 user=raw_input('Apple Account email: ') if 'raw_input' in globals() or __import__('sys').version_info[0]==2 else input('Apple Account email: ')
 password=getpass.getpass('Apple app-specific password (hidden): ')
 results=[];url='https://caldav.icloud.com/'
 for attempt in range(4):
  result,redirect,principal=request(url,user.strip(),password);result['stage']='discovery';results.append(result)
  if redirect and result.get('http_status') in (301,302,303,307,308):
   if not allowed(redirect):results.append({'redirect':'blocked unexpected host'});break
   url=redirect;continue
  if principal and allowed(principal):
   print('Discovered CalDAV server: '+urlparse(principal).hostname)
   print('Discovered server path: '+(urlparse(principal).path or '/'))
   print('These account-specific settings are displayed only, not saved in the report.')
   result,unused,unused2=request(principal,user.strip(),password);result['stage']='principal';results.append(result)
  break
 password=None
 report={'test':'iCloud direct CalDAV 01','results':results,'note':'No credentials, response bodies, account identifiers or calendar contents saved.'}
 filename=os.path.expanduser('~/Desktop/iCloud-connection-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
 with open(filename,'w') as f:json.dump(report,f,indent=2)
 print(json.dumps(report,indent=2));print('Send this report: '+filename)
if __name__=='__main__':main()
