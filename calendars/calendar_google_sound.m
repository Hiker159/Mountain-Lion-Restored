#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#import <objc/message.h>
#include <mach-o/dyld.h>
// Only exact Google hosts and raw single-event CalDAV bodies are transformed.
static BOOL MLGoogleHost(NSString *host){return [@[@"calendar.google.com",@"www.google.com",@"apidata.googleusercontent.com"] containsObject:[host lowercaseString]];}
static NSString *MLGoogleSoundBody(NSString *body){
 if(![body hasPrefix:@"BEGIN:VCALENDAR"]||[body rangeOfString:@"END:VCALENDAR"].location==NSNotFound)return body;
 NSMutableString *out=[NSMutableString string];BOOL alarm=NO,description=NO;
 NSArray *lines=[body componentsSeparatedByString:@"\r\n"];
 for(NSUInteger i=0;i<[lines count];i++){
  NSString *line=[lines objectAtIndex:i];
  if([line isEqual:@"BEGIN:VALARM"]){alarm=YES;description=NO;
   for(NSUInteger j=i+1;j<[lines count];j++){NSString *next=[lines objectAtIndex:j];if([next isEqual:@"END:VALARM"])break;if([next hasPrefix:@"DESCRIPTION:"]||[next hasPrefix:@"DESCRIPTION;"])description=YES;}
  }
  if(alarm&&[line isEqual:@"ACTION:AUDIO"]){[out appendString:@"ACTION:DISPLAY\r\nX-RESTORED-CALENDAR-AUDIO:1\r\n"];if(!description)[out appendString:@"DESCRIPTION:Reminder\r\n"];}
  else {[out appendString:line];[out appendString:@"\r\n"];}
  if([line isEqual:@"END:VALARM"])alarm=NO;
 }
 // Keep unmodified messages byte-identical and avoid adding a second terminal newline.
 if([out rangeOfString:@"X-RESTORED-CALENDAR-AUDIO:1"].location==NSNotFound)return body;
 if([body hasSuffix:@"\r\n"])[out deleteCharactersInRange:NSMakeRange([out length]-2,2)];
 return out;
}
#import "calendar_google_sound_local.m"
#ifndef ML_GOOGLE_SOUND_TEST
static IMP MLOriginalBody,MLOriginalAction,MLOriginalEventAlarms;
static unsigned MLActionTraceCount;
static id MLGoogleRequestBody(id self,SEL cmd){
 id data=((id(*)(id,SEL))MLOriginalBody)(self,cmd);
 if(![data isKindOfClass:[NSData class]]||![self respondsToSelector:NSSelectorFromString(@"url")])return data;
 NSURL *url=((id(*)(id,SEL))objc_msgSend)(self,NSSelectorFromString(@"url"));
 if(![url isKindOfClass:[NSURL class]]||!MLGoogleHost([url host])||![[url scheme] isEqual:@"https"])return data;
 NSString *text=[[[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding] autorelease];
 if(!text)return data;
 if([text hasPrefix:@"BEGIN:VCALENDAR"]){NSString *uid=nil;NSDictionary *entries=MLSoundEntries(text,&uid);MLSoundLocal(MLSoundEventKey(uid),entries);}
 NSString *changed=MLGoogleSoundBody(text);
 if([changed isEqual:text])return data;
 fputs("PRIVATE_ACCOUNT_GOOGLE_SOUND uploaded DISPLAY reminder with local audio marker\n",stderr);
 return [changed dataUsingEncoding:NSUTF8StringEncoding];
}
static int MLGoogleAlarmAction(id self,SEL cmd){
 int action=((int(*)(id,SEL))MLOriginalAction)(self,cmd);
 NSArray *props=((id(*)(id,SEL,id))objc_msgSend)(self,NSSelectorFromString(@"propertiesForName:"),@"X-RESTORED-CALENDAR-AUDIO");
 id value=((id(*)(id,SEL))objc_msgSend)([props lastObject],NSSelectorFromString(@"value"));
 BOOL marked=value&&[[value description] isEqual:@"1"];
 if(marked||MLActionTraceCount++<20){
  NSArray *attachments=((id(*)(id,SEL,id))objc_msgSend)(self,NSSelectorFromString(@"propertiesForName:"),@"ATTACH");
  fprintf(stderr,"PRIVATE_ACCOUNT_GOOGLE_SOUND read action=%d marker-properties=%lu marker-match=%d attachment-properties=%lu value-type=%s\n",action,(unsigned long)[props count],marked,(unsigned long)[attachments count],value?class_getName([value class]):"none");
 }
 if(marked){
  return ((int(*)(id,SEL,id))objc_msgSend)([self class],NSSelectorFromString(@"actionFromICSString:"),@"AUDIO");
 }
 return action;
}
static id MLGoogleEventAlarms(id self,SEL cmd,id event){
 id alarms=((id(*)(id,SEL,id))MLOriginalEventAlarms)(self,cmd,event);
 if(![alarms isKindOfClass:[NSArray class]]||![event respondsToSelector:NSSelectorFromString(@"uid")])return alarms;
 id uid=((id(*)(id,SEL))objc_msgSend)(event,NSSelectorFromString(@"uid"));
 NSDictionary *settings=MLSoundLocal(MLSoundEventKey([uid description]),nil);if(![settings count])return alarms;
 for(id alarm in alarms){
  NSArray *props=((id(*)(id,SEL,id))objc_msgSend)(alarm,NSSelectorFromString(@"propertiesForName:"),@"TRIGGER");
  id prop=[props lastObject];if(![prop respondsToSelector:NSSelectorFromString(@"ICSStringWithOptions:")])continue;
  NSString *trigger=((id(*)(id,SEL,NSUInteger))objc_msgSend)(prop,NSSelectorFromString(@"ICSStringWithOptions:"),0);
  trigger=[trigger stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
  NSString *sound=settings[trigger];if(![sound isKindOfClass:[NSString class]])continue;
  Class attachment=NSClassFromString(@"ICSAttachment");id object=((id(*)(id,SEL,id))objc_msgSend)([attachment alloc],NSSelectorFromString(@"initWithURL:"),[NSURL URLWithString:sound]);
  if(!object)continue;
  int audio=((int(*)(id,SEL,id))objc_msgSend)([alarm class],NSSelectorFromString(@"actionFromICSString:"),@"AUDIO");
  ((void(*)(id,SEL,int))objc_msgSend)(alarm,NSSelectorFromString(@"setAction:"),audio);
  ((void(*)(id,SEL,id))objc_msgSend)(alarm,NSSelectorFromString(@"setAttach:"),@[object]);[object release];
  fputs("PRIVATE_ACCOUNT_GOOGLE_SOUND restored local sound from settings\n",stderr);
 }
 return alarms;
}
static void MLGoogleSoundInstall(const struct mach_header *header,intptr_t slide){
 (void)header;(void)slide;
 Class event=NSClassFromString(@"CalManagedEvent");Method eventAlarms=class_getInstanceMethod(event,NSSelectorFromString(@"alarmsFromICSEventHelper:"));
 if(!MLOriginalEventAlarms&&eventAlarms){char *type=method_copyReturnType(eventAlarms);BOOL valid=type&&type[0]=='@'&&method_getNumberOfArguments(eventAlarms)==3;free(type);if(valid){MLOriginalEventAlarms=method_setImplementation(eventAlarms,(IMP)MLGoogleEventAlarms);fputs("PRIVATE_ACCOUNT_GOOGLE_SOUND local settings hook ready\n",stderr);}}
 Class task=NSClassFromString(@"CoreDAVPostOrPutTask");Method body=class_getInstanceMethod(task,NSSelectorFromString(@"requestBody"));
 Class alarm=NSClassFromString(@"ICSAlarm");Method action=class_getInstanceMethod(alarm,NSSelectorFromString(@"action"));
 if(!MLOriginalBody&&body){char *type=method_copyReturnType(body);BOOL valid=type&&type[0]=='@'&&method_getNumberOfArguments(body)==2;free(type);if(valid){MLOriginalBody=method_setImplementation(body,(IMP)MLGoogleRequestBody);fputs("PRIVATE_ACCOUNT_GOOGLE_SOUND upload hook ready\n",stderr);}}
 if(!MLOriginalAction&&action){char *type=method_copyReturnType(action);BOOL valid=type&&type[0]=='i'&&method_getNumberOfArguments(action)==2;free(type);if(valid){MLOriginalAction=method_setImplementation(action,(IMP)MLGoogleAlarmAction);fputs("PRIVATE_ACCOUNT_GOOGLE_SOUND local action hook ready\n",stderr);}}
}
__attribute__((constructor)) static void MLGoogleSoundInit(void){_dyld_register_func_for_add_image(MLGoogleSoundInstall);}
#endif
