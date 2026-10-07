// Included in the helper's app-local extension; never changes URL defaults.
#import <objc/runtime.h>
#import <Carbon/Carbon.h>

static NSString *MLClickAppPathForExecutable(NSString *p) {
    // helper.app/Contents/MacOS/CalendarAgent is inside Calendar.app/Contents/Helpers.
    p=[p stringByResolvingSymlinksInPath];
    for (int i=0;i<6;i++) p=[p stringByDeletingLastPathComponent];
    return [p stringByStandardizingPath];
}
static NSRunningApplication *MLClickRunning(NSString *path) {
    for (NSRunningApplication *app in [[NSWorkspace sharedWorkspace] runningApplications])
        if ([[[[app bundleURL] path] stringByResolvingSymlinksInPath] isEqualToString:path]) return app;
    return nil;
}
@interface MLCalendarClick : NSObject
@property(copy) NSString *path;
@property(copy) NSString *url;
@property int attempts;
- (void)deliver;
@end
@implementation MLCalendarClick
@synthesize path,url,attempts;
- (void)deliver {
    NSRunningApplication *app=MLClickRunning(self.path);
    if (!app || ![app isFinishedLaunching]) {
        if (++self.attempts<60) { [self performSelector:@selector(deliver) withObject:nil afterDelay:0.5]; return; }
        NSLog(@"MLClick failed: restored Calendar did not become ready"); [self release]; return;
    }
    pid_t pid=[app processIdentifier];
    FSRef appRef;
    OSStatus status=FSPathMakeRef((const UInt8 *)[self.path fileSystemRepresentation],&appRef,NULL);
    NSURL *eventURL=[NSURL URLWithString:self.url];
    if (!eventURL) status=paramErr;
    if (!status) {
        // Use the original CalendarStore URL-opening mechanism, but bind it
        // to this already-running process instead of the system URL handler.
        LSApplicationParameters params={0};
        params.application=&appRef;
        params.flags=kLSLaunchDefaults;
        status=LSOpenURLsWithRole((CFArrayRef)@[eventURL],kLSRolesAll,NULL,&params,NULL,0);
    }
    BOOL activated=NO;
    if (!status) activated=[app activateWithOptions:NSApplicationActivateIgnoringOtherApps | NSApplicationActivateAllWindows];
    NSLog(@"MLClick URL dispatch restored pid=%d status=%d activated=%d",pid,(int)status,(int)activated);
    [self release];
}
- (void)dealloc { [path release];[url release];[super dealloc]; }
@end
static void MLClickOpenMain(id info) {
    @try {
        if (![info isKindOfClass:[NSDictionary class]]) return;
        NSString *source=[info objectForKey:@"app"];
        NSString *occ=[info objectForKey:@"occid"];
        if (!([source isEqual:@"org.local.iCal"] || [source isEqual:@"com.apple.iCal"]) ||
            ![occ isKindOfClass:[NSString class]] || ![occ length]) {
            NSLog(@"MLClick ignored unsupported notification payload");return;
        }
        NSString *appPath=MLClickAppPathForExecutable([[[NSProcessInfo processInfo] arguments] objectAtIndex:0]);
        NSString *exe=[appPath stringByAppendingPathComponent:@"Contents/MacOS/Calendar"];
        NSString *folder=[appPath stringByDeletingLastPathComponent];
        NSString *profile=[folder stringByAppendingPathComponent:@"calendar-trial.sb"];
        if (![[NSFileManager defaultManager] isExecutableFileAtPath:exe] ||
            ![[NSFileManager defaultManager] fileExistsAtPath:profile]) {
            NSLog(@"MLClick failed: package path/profile missing");return;
        }
        if (!MLClickRunning(appPath)) {
            NSString *home=NSHomeDirectory();
            // Children inherit the helper's sandbox. Mavericks rejects a
            // second sandbox_apply_container, so do not run sandbox-exec here.
            NSArray *args=@[@"-MLCalDataDirectory",[home stringByAppendingPathComponent:@"Library/MLCalData"],@"-iCalApplicationSupportDirectory",[home stringByAppendingPathComponent:@"Library/Application Support/ML-Calendar"]];
            NSTask *task=[[[NSTask alloc] init] autorelease];
            [task setLaunchPath:exe];[task setArguments:args];
            NSMutableDictionary *env=[[[NSProcessInfo processInfo] environment] mutableCopy];
            [env removeObjectForKey:@"DYLD_INSERT_LIBRARIES"];
            [env removeObjectForKey:@"NSRunningFromLaunchd"];
            [env removeObjectForKey:@"DYLD_PRINT_LIBRARIES"];[task setEnvironment:env];[env release];
            [task setStandardInput:[NSFileHandle fileHandleWithNullDevice]];
            [task launch];
            NSLog(@"MLClick launched restored Calendar inheriting helper sandbox");
        }
        MLCalendarClick *delivery=[[MLCalendarClick alloc] init];
        delivery.path=appPath;
        delivery.url=[NSString stringWithFormat:@"ical://occurrence/%@?method=show&options=more",occ];
        [delivery performSelector:@selector(deliver) withObject:nil afterDelay:1.0];
    } @catch (NSException *e) { NSLog(@"MLClick exception: %@",[e name]); }
}
static void MLClickOpen(id self,SEL selector,id info) {
    dispatch_async(dispatch_get_main_queue(), ^{ MLClickOpenMain(info); });
}
static void MLInstallClick(void) {
    Class cls=NSClassFromString(@"CalUserNotificationCenterListener");
    Method method=class_getInstanceMethod(cls,NSSelectorFromString(@"openURLForInfo:"));
    if (!method || method_getNumberOfArguments(method)!=3) {NSLog(@"MLClick hook unavailable");return;}
    method_setImplementation(method,(IMP)MLClickOpen);
    NSLog(@"MLClick installed v3; routes occurrence links to exact restored process");
}
