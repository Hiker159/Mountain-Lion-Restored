// App-local Mavericks helper extension. No system hooks or database access.
#import <AppKit/AppKit.h>
#import <dispatch/dispatch.h>

@interface NSObject (MLCalendarPrivateMethods)
+ (id)defaultCenter;
+ (id)defaultHelper;
- (void)resetCaches;
- (void)findAndScheduleUpcomingAlarms:(id)calendarIDs;
@end

@interface MLCalendarWakeRecovery : NSObject
@end

static void snapshot(NSString *phase) {
    NSUserNotificationCenter *center = [NSUserNotificationCenter defaultUserNotificationCenter];
    NSUInteger overdue = 0;
    NSDate *now = [NSDate date];
    NSArray *scheduled = [center scheduledNotifications];
    for (NSUserNotification *note in scheduled) {
        if (note.deliveryDate && [note.deliveryDate compare:now] != NSOrderedDescending)
            overdue++;
    }
    NSLog(@"MLWake %@: scheduled=%lu overdue=%lu delivered=%lu", phase,
          (unsigned long)[scheduled count], (unsigned long)overdue,
          (unsigned long)[[center deliveredNotifications] count]);
}

@implementation MLCalendarWakeRecovery
- (void)sleep:(NSNotification *)note {
    // Do not block sleep or retain notifications/Calendar objects across sleep.
    snapshot(@"will-sleep");
}
- (void)wake:(NSNotification *)note {
    // Coalesce repeated workspace wake messages; all work runs on main thread.
    [self performSelectorOnMainThread:@selector(queueRecovery) withObject:nil waitUntilDone:NO];
}
- (void)queueRecovery {
    NSLog(@"MLWake did-wake received");
    [NSObject cancelPreviousPerformRequestsWithTarget:self];
    [self performSelector:@selector(recover) withObject:nil afterDelay:2.0];
}
- (void)recover {
    @try {
        snapshot(@"before-rescan");
        Class centerClass = NSClassFromString(@"CalUserNotificationCenter");
        Class helperClass = NSClassFromString(@"CalUserNotificationCenterHelper");
        if (![centerClass respondsToSelector:@selector(defaultCenter)] ||
            ![helperClass respondsToSelector:@selector(defaultHelper)]) {
            NSLog(@"MLWake unavailable: expected legacy classes are missing");
            return;
        }
        id center = [centerClass defaultCenter];
        id helper = [helperClass defaultHelper];
        if (![center respondsToSelector:@selector(resetCaches)] ||
            ![helper respondsToSelector:@selector(findAndScheduleUpcomingAlarms:)]) {
            NSLog(@"MLWake unavailable: expected legacy methods are missing");
            return;
        }
        [center resetCaches];
        // Original public entry queues scans on its own context/operation queue.
        // Nil selects all local calendars. Keep delivered/acknowledged checks.
        [helper findAndScheduleUpcomingAlarms:nil];
        NSLog(@"MLWake requested original alarm rescan");
        [self performSelector:@selector(afterScan) withObject:nil afterDelay:8.0];
    } @catch (NSException *exception) {
        NSLog(@"MLWake recovery exception: %@", [exception name]);
    }
}
- (void)afterScan { snapshot(@"after-rescan"); }
@end

#include "calendar_notification_click.m"

static MLCalendarWakeRecovery *observer;
__attribute__((constructor)) static void installWakeRecovery(void) {
    dispatch_async(dispatch_get_main_queue(), ^{
        @autoreleasepool {
            if (![[[NSProcessInfo processInfo] processName] isEqualToString:@"CalendarAgent"])
                return;
            MLInstallClick();
            observer = [[MLCalendarWakeRecovery alloc] init];
            NSNotificationCenter *center = [[NSWorkspace sharedWorkspace] notificationCenter];
            [center addObserver:observer selector:@selector(sleep:) name:NSWorkspaceWillSleepNotification object:nil];
            [center addObserver:observer selector:@selector(wake:) name:NSWorkspaceDidWakeNotification object:nil];
            NSLog(@"MLWake installed v1; wake rescans retain original duplicate checks");
        }
    });
}
