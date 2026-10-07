// Included by the sound extension. Only event UID hashes, trigger and sound URL
// are stored locally; no title, notes, account credential or event body.
#include <CommonCrypto/CommonDigest.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
static NSString *MLSoundEventKey(NSString *uid){
 if(![uid length])return nil;NSData *d=[uid dataUsingEncoding:NSUTF8StringEncoding];unsigned char digest[CC_SHA256_DIGEST_LENGTH];CC_SHA256([d bytes],(CC_LONG)[d length],digest);NSMutableString *key=[NSMutableString string];for(unsigned i=0;i<sizeof(digest);i++)[key appendFormat:@"%02x",digest[i]];return key;
}
static NSDictionary *MLSoundEntries(NSString *body,NSString **uidOut){
 NSMutableDictionary *entries=[NSMutableDictionary dictionary];NSString *uid=nil,*trigger=nil,*sound=nil;BOOL alarm=NO,audio=NO;
 for(NSString *line in [body componentsSeparatedByString:@"\r\n"]){
  if([line isEqual:@"BEGIN:VALARM"]){alarm=YES;audio=NO;trigger=nil;sound=nil;}
  else if([line isEqual:@"END:VALARM"]){if(audio&&trigger&&sound)entries[trigger]=sound;alarm=NO;}
  else if(!alarm&&[line hasPrefix:@"UID:"])uid=[line substringFromIndex:4];
  else if(alarm&&[line isEqual:@"ACTION:AUDIO"])audio=YES;
  else if(alarm&&[line hasPrefix:@"TRIGGER:"])trigger=line;
  else if(alarm&&([line hasPrefix:@"ATTACH:"]||[line hasPrefix:@"ATTACH;"])){
   NSRange colon=[line rangeOfString:@":"];if(colon.location!=NSNotFound&&[line rangeOfString:@"ENCODING=BASE64"].location==NSNotFound)sound=[line substringFromIndex:colon.location+1];
  }
 }
 if(uidOut)*uidOut=uid;return entries;
}
static NSDictionary *MLSoundLocal(NSString *key,NSDictionary *replace){
 if(!key)return nil;
#ifdef ML_GOOGLE_SOUND_LOCAL_TEST
 extern NSDictionary *MLTestSoundLocal(NSString *,NSDictionary *);
 return MLTestSoundLocal(key,replace);
#endif
 NSString *folder=[NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/ML-CalAuthx/GoogleSounds"];
 [[NSFileManager defaultManager] createDirectoryAtPath:folder withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:NULL];
 NSString *lock=[folder stringByAppendingPathComponent:@"settings.lock"],*path=[folder stringByAppendingPathComponent:@"settings.plist"];
 int fd=open([lock fileSystemRepresentation],O_CREAT|O_RDWR|O_NOFOLLOW,0600);if(fd<0||flock(fd,LOCK_EX)){if(fd>=0)close(fd);return nil;}
 struct stat st;if(lstat([path fileSystemRepresentation],&st)==0&&(!S_ISREG(st.st_mode)||st.st_uid!=getuid())){flock(fd,LOCK_UN);close(fd);return nil;}
 NSMutableDictionary *all=[NSMutableDictionary dictionaryWithContentsOfFile:path];if(!all)all=[NSMutableDictionary dictionary];
 if(replace){if([replace count])all[key]=replace;else [all removeObjectForKey:key];if(![all writeToFile:path atomically:YES])fputs("PRIVATE_ACCOUNT_GOOGLE_SOUND local settings write failed\n",stderr);chmod([path fileSystemRepresentation],0600);}
 NSDictionary *result=[[all[key] retain] autorelease];flock(fd,LOCK_UN);close(fd);return result;
}
