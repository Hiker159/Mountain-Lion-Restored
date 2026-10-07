# -*- coding: utf-8 -*-
from __future__ import print_function
import subprocess,getpass,os,json,datetime,re,sys
import xml.etree.ElementTree as ET
try:
 from urllib.parse import urlparse,urljoin
except ImportError:
 from urlparse import urlparse,urljoin
try:prompt=raw_input
except NameError:prompt=input
DAV='{DAV:}';CARD='{urn:ietf:params:xml:ns:carddav}'
def allowed(url):
 p=urlparse(url);return p.scheme=='https' and (p.hostname=='icloud.com' or (p.hostname or '').endswith('.icloud.com')) and not p.username and p.port in (None,443)
def quote(x):
 if '\n' in x or '\r' in x:raise ValueError('Newlines not accepted')
 return '"'+x.replace('\\','\\\\').replace('"','\\"')+'"'
def main():
 user=prompt('Apple Account email: ').strip();secret=getpass.getpass('App-specific password (hidden): ');name=prompt('Exact name of the disposable photo contact: ')
 if sys.version_info[0]==2:name=name.decode('utf-8')
 results=[]
 def request(url,method,body='',depth='0',stage='discovery'):
  if not allowed(url):raise ValueError('Unexpected destination blocked')
  print('Checking '+stage+'...',flush=True) if sys.version_info[0]>=3 else print('Checking '+stage+'...')
  args=['/usr/bin/curl','--config','-','--silent','--show-error','--connect-timeout','20','--max-time','45','--proto','=https','--max-filesize','10485760','--request',method,'--include']
  if method!='GET':args+=['--header','Depth: '+depth,'--header','Content-Type: application/xml; charset=utf-8','--data-binary',body]
  args+=[url];p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  data,err=p.communicate(('user = '+quote(user+':'+secret)+'\n').encode('utf-8'))
  if p.returncode:results.append({'stage':stage,'curl_exit':p.returncode});raise ValueError('Connection failed; see report')
  head,sep,content=data.partition(b'\r\n\r\n')
  while content.startswith(b'HTTP/'):head,sep,content=content.partition(b'\r\n\r\n')
  status=int(head.splitlines()[0].split()[1]);results.append({'stage':stage,'http_status':status})
  if status in (301,302,303,307,308):
   for line in head.decode('utf-8','replace').splitlines():
    if line.lower().startswith('location:'):return request(urljoin(url,line.split(':',1)[1].strip()),method,body,depth,stage+' redirect')
  return content,status,url
 def propfind(url,depth='0',stage='discovery'):
  body='<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:carddav"><d:prop><d:current-user-principal/><c:addressbook-home-set/><d:resourcetype/></d:prop></d:propfind>'
  data,status,url=request(url,'PROPFIND',body,depth,stage)
  if status!=207:raise ValueError('Discovery did not succeed')
  return ET.fromstring(data),url
 try:
  root,url=propfind('https://contacts.icloud.com/')
  node=root.find('.//'+DAV+'current-user-principal/'+DAV+'href')
  if node is None:raise ValueError('Principal not discovered')
  root,url=propfind(urljoin(url,node.text),stage='principal')
  node=root.find('.//'+CARD+'addressbook-home-set/'+DAV+'href')
  if node is None:raise ValueError('Address book home not discovered')
  root,url=propfind(urljoin(url,node.text),'1','collections')
  collections=[]
  for response in root.findall(DAV+'response'):
   if response.find('.//'+CARD+'addressbook') is not None:
    href=response.find(DAV+'href');collections.append(urljoin(url,href.text))
  query=ET.Element(CARD+'addressbook-query');props=ET.SubElement(query,DAV+'prop');ET.SubElement(props,CARD+'address-data')
  filt=ET.SubElement(query,CARD+'filter');pf=ET.SubElement(filt,CARD+'prop-filter',{'name':'FN'});match=ET.SubElement(pf,CARD+'text-match',{'match-type':'equals','collation':'i;unicode-casemap'});match.text=name
  found=False
  for collection in collections[:10]:
   data,status,unused=request(collection,'REPORT',ET.tostring(query,encoding='utf-8').decode('utf-8'),'1','test contact')
   if status!=207:continue
   root=ET.fromstring(data)
   for card in root.iter(CARD+'address-data'):
    text=re.sub(r'\r?\n[ \t]','',card.text or '')
    for line in text.splitlines():
     if not line.upper().startswith('PHOTO'):continue
     found=True;header,value=line.split(':',1)
     if value.startswith(('https://','http://')):
      results.append({'stage':'photo format','format':'URL'})
      image,status,unused=request(value,'GET',stage='photo download')
      results[-1]['received_bytes']=len(image) if status==200 else 0
     else:results.append({'stage':'photo format','format':'inline','encoded_length':len(value)})
  results.append({'stage':'summary','photo_field_found':found})
 except Exception as e:
  # Omit exception details: server XML or URLs may contain personal values.
  results.append({'stage':'summary','completed':False})
 secret=None
 report={'test':'iCloud photo direct 01','results':results,'privacy':'No credentials, contact values, URLs or photo contents saved.'}
 path=os.path.expanduser('~/Desktop/iCloud-photo-connection-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
 with open(path,'w') as f:json.dump(report,f,indent=2)
 print(json.dumps(report,indent=2));print('Send this report: '+path)
if __name__=='__main__':main()
