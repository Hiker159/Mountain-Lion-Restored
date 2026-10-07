#import <AppKit/AppKit.h>
#import <dispatch/dispatch.h>
#include "calendar_notification_click.m"
#include <assert.h>
@interface CalUserNotificationCenterListener : NSObject
- (void)openURLForInfo:(id)info;
@end
@implementation CalUserNotificationCenterListener
- (void)openURLForInfo:(id)info {}
@end
int main(void) { @autoreleasepool {
 NSString *p=@"/private/tmp/Package With Spaces/Calendar/Mountain Lion Calendar.app/Contents/Helpers/Mountain Lion Calendar Alerts.app/Contents/MacOS/CalendarAgent";
 assert([MLClickAppPathForExecutable(p) isEqual:@"/private/tmp/Package With Spaces/Calendar/Mountain Lion Calendar.app"]);
 Method m=class_getInstanceMethod([CalUserNotificationCenterListener class],@selector(openURLForInfo:));
 IMP before=method_getImplementation(m);MLInstallClick();
 assert(method_getImplementation(m)!=before);
 assert(method_getImplementation(m)==(IMP)MLClickOpen);
 MLClickOpenMain(@{});MLClickOpenMain(@{@"app":@"com.apple.reminders",@"occid":@"ignored"});
 MLClickOpenMain(@{@"app":@"org.local.iCal",@"occid":@123});
 NSLog(@"Click tests passed: path derivation, hook installation, malformed/unsupported payloads");
 }return 0; }
