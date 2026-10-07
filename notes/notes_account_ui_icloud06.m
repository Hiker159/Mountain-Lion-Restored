#import <Cocoa/Cocoa.h>
#import <objc/message.h>
#include <stdio.h>
#import <objc/runtime.h>
#include <dlfcn.h>
static id pane;
static NSWindow *accountWindow;
@interface MLNotesAccountsUI:NSObject
-(void)install:(NSNotification *)notification;
-(void)openAccounts:(id)sender;
-(void)addICloudNotes:(id)sender;
@end
@implementation MLNotesAccountsUI
-(void)install:(NSNotification *)notification{
 (void)notification;
 NSMenu *menu=[[[NSApp mainMenu] itemAtIndex:0] submenu];
 if(!menu){fputs("PRIVATE_NOTES_ACCOUNT_MENU_MISSING\n",stderr);return;}
 // Remove the stock System Preferences command and any earlier injected entry.
 for(NSMenuItem *old in [[[menu itemArray] copy] autorelease]){
  NSString *title=[[old title] lowercaseString];
  NSString *action=[NSStringFromSelector([old action]) lowercaseString];
  if([title rangeOfString:@"accounts"].location!=NSNotFound || (action&&[action rangeOfString:@"account"].location!=NSNotFound)) [menu removeItem:old];
 }
 NSMenuItem *item=[[[NSMenuItem alloc] initWithTitle:@"Accounts…" action:@selector(openAccounts:) keyEquivalent:@""] autorelease];
 [item setTarget:self];[menu insertItem:item atIndex:MIN(2,[menu numberOfItems])];
 NSMenuItem *cloud=[[[NSMenuItem alloc] initWithTitle:@"Add iCloud Notes Account…" action:@selector(addICloudNotes:) keyEquivalent:@""] autorelease];
 [cloud setTarget:self];[menu insertItem:cloud atIndex:MIN(3,[menu numberOfItems])];
 fputs("PRIVATE_NOTES_ACCOUNT_MENU_READY\n",stderr);fflush(stderr);
}
-(void)addICloudNotes:(id)sender{
 [self openAccounts:sender];if(!pane||!accountWindow)return;
 NSAlert *guide=[[[NSAlert alloc] init] autorelease];
 [guide setMessageText:@"Set up legacy iCloud Notes"];
 [guide setInformativeText:@"Use your iCloud Mail address and an app-specific password. In the private Notes setup wizard, choose IMAP: imap.mail.me.com, SSL, port 993. The receiving server uses your full iCloud Mail address as the username.\n\nThis tests the older iCloud Notes connection. Upgraded iCloud notes are not supported by the original Mountain Lion Notes engine."];
 [guide addButtonWithTitle:@"Continue"];[guide addButtonWithTitle:@"Cancel"];
 if([guide runModal]!=NSAlertFirstButtonReturn)return;
 SEL sel=NSSelectorFromString(@"addAccountUsingPluginID:service:");
 Method m=class_getInstanceMethod(object_getClass(pane),sel);char *type=m?method_copyReturnType(m):NULL;
 BOOL valid=type&&type[0]=='v'&&method_getNumberOfArguments(m)==4;free(type);
 // This private identifier selects the dedicated Notes setup controller.
 NSString *mail=@"org.ntest.Notes.iaplugin";
 if(!valid){fputs("PRIVATE_NOTES_ICLOUD_SETUP_UNAVAILABLE\n",stderr);return;}
 ((void(*)(id,SEL,id,id))objc_msgSend)(pane,sel,mail,nil);
 fputs("PRIVATE_NOTES_ICLOUD_IMAP_SETUP_OPENED\n",stderr);
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
