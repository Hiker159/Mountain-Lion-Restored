// Runs only new extension code, with fake notification and legacy classes.
#import <AppKit/AppKit.h>
#import <assert.h>
static int resets, scans;
@interface MLFakeCenter : NSObject
+ (id)defaultUserNotificationCenter;
- (NSArray *)scheduledNotifications;
- (NSArray *)deliveredNotifications;
@end
@implementation MLFakeCenter
+ (id)defaultUserNotificationCenter { static id c; if (!c) c=[self new]; return c; }
- (NSArray *)scheduledNotifications { return [NSArray array]; }
- (NSArray *)deliveredNotifications { return [NSArray array]; }
@end
#define NSUserNotificationCenter MLFakeCenter
#include "calendar_wake_recovery.m"
#undef NSUserNotificationCenter
@interface CalUserNotificationCenter : NSObject
@end
@implementation CalUserNotificationCenter
+ (id)defaultCenter { static id c; if (!c)c=[self new];return c; }
- (void)resetCaches { resets++; }
@end
@interface CalUserNotificationCenterHelper : NSObject
@end
@implementation CalUserNotificationCenterHelper
+ (id)defaultHelper { static id h; if(!h)h=[self new];return h; }
- (void)findAndScheduleUpcomingAlarms:(id)ids { assert(ids==nil);assert(resets==scans+1);scans++; }
@end
int main(void) {
 @autoreleasepool {
  MLCalendarWakeRecovery *test=[MLCalendarWakeRecovery new];
  [test queueRecovery];[test queueRecovery];
  [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:2.3]];
  assert(scans==1 && resets==1); // Repeated wake messages coalesce.
  [test recover];assert(scans==2 && resets==2);
  [NSObject cancelPreviousPerformRequestsWithTarget:test];
  [test release];
  NSLog(@"Wake recovery tests passed; no legacy code or real notification center used.");
 }
 return 0;
}
