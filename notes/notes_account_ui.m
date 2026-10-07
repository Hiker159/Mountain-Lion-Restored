#import <Cocoa/Cocoa.h>
#import <objc/message.h>
#include <stdio.h>
static id pane;
static NSWindow *accountWindow;
@interface MLNotesAccountsUI:NSObject
-(void)install:(NSNotification *)notification;
-(void)openAccounts:(id)sender;
@end
@implementation MLNotesAccountsUI
-(void)install:(NSNotification *)notification{
 (void)notification;
 NSMenu *menu=[[[NSApp mainMenu] itemAtIndex:0] submenu];
 if(!menu){fputs("PRIVATE_NOTES_ACCOUNT_MENU_MISSING\n",stderr);return;}
 NSMenuItem *item=[[[NSMenuItem alloc] initWithTitle:@"Accounts…" action:@selector(openAccounts:) keyEquivalent:@""] autorelease];
 [item setTarget:self];[menu insertItem:item atIndex:MIN(2,[menu numberOfItems])];
 fputs("PRIVATE_NOTES_ACCOUNT_MENU_READY\n",stderr);fflush(stderr);
}
-(void)openAccounts:(id)sender{(void)sender;@try{
 if(accountWindow){[accountWindow makeKeyAndOrderFront:nil];return;}
 NSString *path=[[[NSBundle mainBundle] bundlePath] stringByAppendingPathComponent:@"Contents/PrivatePanes/InternetAccounts.prefPane"];
 NSBundle *bundle=[NSBundle bundleWithPath:path];
 if(![bundle load]){fputs("PRIVATE_NOTES_ACCOUNT_PANEL_LOAD_FAILED\n",stderr);return;}
 Class cls=[bundle principalClass];
 pane=((id(*)(id,SEL,id))objc_msgSend)([cls alloc],NSSelectorFromString(@"initWithBundle:"),bundle);
 NSView *view=((id(*)(id,SEL))objc_msgSend)(pane,NSSelectorFromString(@"loadMainView"));
 if(!view){fputs("PRIVATE_NOTES_ACCOUNT_PANEL_VIEW_MISSING\n",stderr);return;}
 accountWindow=[[NSWindow alloc] initWithContentRect:[view frame] styleMask:NSTitledWindowMask|NSClosableWindowMask|NSMiniaturizableWindowMask backing:NSBackingStoreBuffered defer:NO];
 [accountWindow setReleasedWhenClosed:NO];[accountWindow setTitle:@"Restored Notes Accounts"];
 [accountWindow setContentView:view];
 for(NSString *name in @[@"willSelect",@"didSelect"]){SEL sel=NSSelectorFromString(name);if([pane respondsToSelector:sel])((void(*)(id,SEL))objc_msgSend)(pane,sel);}
 [accountWindow center];[accountWindow makeKeyAndOrderFront:nil];
 fputs("PRIVATE_NOTES_ACCOUNT_PANEL_READY\n",stderr);fflush(stderr);
 }@catch(NSException *e){fprintf(stderr,"PRIVATE_NOTES_ACCOUNT_PANEL_EXCEPTION %s\n",[[e name] UTF8String]);fflush(stderr);}
}
@end
static MLNotesAccountsUI *ui;
__attribute__((constructor)) static void installAccountsUI(void){@autoreleasepool{
 ui=[[MLNotesAccountsUI alloc] init];
 [[NSNotificationCenter defaultCenter] addObserver:ui selector:@selector(install:) name:NSApplicationDidFinishLaunchingNotification object:nil];
}}
