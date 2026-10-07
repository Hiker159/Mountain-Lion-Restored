#import <Foundation/Foundation.h>
#define ML_GOOGLE_SOUND_LOCAL_TEST 1
static NSMutableDictionary *MLTestSettings;
NSDictionary *MLTestSoundLocal(NSString *key,NSDictionary *replace){
 if(!MLTestSettings)MLTestSettings=[[NSMutableDictionary alloc]init];
 if(replace){if([replace count])MLTestSettings[key]=replace;else [MLTestSettings removeObjectForKey:key];}
 return MLTestSettings[key];
}
@interface CoreDAVPostOrPutTask:NSObject
@property(retain) NSData *payload;
@property(retain) NSURL *endpoint;
-(id)requestBody;-(id)url;
@end
@implementation CoreDAVPostOrPutTask
@synthesize payload,endpoint;
-(id)requestBody{return payload;}-(id)url{return endpoint;}
@end
@interface MLTestAlarmProperty:NSObject
-(id)value;
@end
@implementation MLTestAlarmProperty
-(id)value{return @"1";}
@end
@interface MLTestTrigger:NSObject
-(id)ICSStringWithOptions:(NSUInteger)o;
@end
@implementation MLTestTrigger
-(id)ICSStringWithOptions:(NSUInteger)o{return @"TRIGGER:-PT5M\r\n";}
@end
@interface ICSAttachment:NSObject
-(id)initWithURL:(NSURL *)url;
@end
@implementation ICSAttachment
-(id)initWithURL:(NSURL *)url{return [super init];}
@end
@interface ICSAlarm:NSObject
@property BOOL marked;
@property int actionValue;
@property BOOL attached;
-(void)setAction:(int)v;-(void)setAttach:(id)v;
-(int)action;-(id)propertiesForName:(id)name;+(int)actionFromICSString:(id)s;
@end
@implementation ICSAlarm
@synthesize marked,actionValue,attached;
-(id)init{if((self=[super init]))actionValue=2;return self;}
-(int)action{return actionValue;}
-(void)setAction:(int)v{actionValue=v;}
-(void)setAttach:(id)v{attached=[v count]>0;}
-(id)propertiesForName:(id)name{if([name isEqual:@"TRIGGER"])return @[[[[MLTestTrigger alloc]init]autorelease]];return marked&&[name isEqual:@"X-RESTORED-CALENDAR-AUDIO"]?@[[[[MLTestAlarmProperty alloc]init]autorelease]]:@[];}
+(int)actionFromICSString:(id)s{return [s isEqual:@"AUDIO"]?3:2;}
@end
@interface MLTestEvent:NSObject
-(id)uid;
@end
@implementation MLTestEvent
-(id)uid{return @"test-event";}
@end
@interface CalManagedEvent:NSObject
@property(retain) NSArray *alarms;
-(id)alarmsFromICSEventHelper:(id)e;
@end
@implementation CalManagedEvent
@synthesize alarms;
-(id)alarmsFromICSEventHelper:(id)e{return alarms;}
@end
#import "calendar_google_sound.m"
#include <assert.h>
int main(){@autoreleasepool{
 MLGoogleSoundInstall(NULL,0);
 ICSAlarm *a=[[[ICSAlarm alloc]init]autorelease];assert([a action]==2);a.marked=YES;assert([a action]==3);
 CoreDAVPostOrPutTask *t=[[[CoreDAVPostOrPutTask alloc]init]autorelease];t.endpoint=[NSURL URLWithString:@"https://calendar.google.com/calendar/dav/test/events/1"];
 t.payload=[@"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:test-event\r\nBEGIN:VALARM\r\nACTION:AUDIO\r\nTRIGGER:-PT5M\r\nATTACH:Basso\r\nEND:VALARM\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n" dataUsingEncoding:NSUTF8StringEncoding];
 NSString *body=[[[NSString alloc]initWithData:[t requestBody] encoding:NSUTF8StringEncoding]autorelease];assert([body rangeOfString:@"ACTION:DISPLAY"].location!=NSNotFound);assert([body rangeOfString:@"DESCRIPTION:Reminder"].location!=NSNotFound);
 CalManagedEvent *managed=[[[CalManagedEvent alloc]init]autorelease];ICSAlarm *incoming=[[[ICSAlarm alloc]init]autorelease];managed.alarms=@[incoming];
 [managed alarmsFromICSEventHelper:[[[MLTestEvent alloc]init]autorelease]];assert(incoming.actionValue==3);assert(incoming.attached);
 NSString *silent=[[[[NSString alloc]initWithData:t.payload encoding:NSUTF8StringEncoding]autorelease] stringByReplacingOccurrencesOfString:@"ACTION:AUDIO" withString:@"ACTION:DISPLAY"];
 t.payload=[silent dataUsingEncoding:NSUTF8StringEncoding];[t requestBody];assert([MLTestSettings count]==0);
 t.endpoint=[NSURL URLWithString:@"https://example.org/calendar/events/1"];assert([t requestBody]==t.payload);
 puts("PASS: mock upload/action hooks; marked audio restored; unmarked display unchanged; non-Google passthrough. No network or legacy code executed.");
}return 0;}
