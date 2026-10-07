#import <Cocoa/Cocoa.h>
#import <objc/message.h>
#include <stdio.h>
#import <objc/runtime.h>
#include <dlfcn.h>
static id pane;
static NSWindow *accountWindow,*cloudWindow;
static NSTextField *cloudEmail,*cloudStatus;
static NSSecureTextField *cloudPassword;
static IMP originalAosEmail;
static BOOL directICloudEmail(id self,SEL cmd,id email){
 if([email isKindOfClass:[NSString class]]){
  NSString *domain=[[[email componentsSeparatedByString:@"@"] lastObject] lowercaseString];
  if([@[@"icloud.com",@"me.com",@"mac.com"] containsObject:domain]){fputs("PRIVATE_NOTES_ICLOUD ordinary_imap_selected\n",stderr);return NO;}
 }
 return ((BOOL(*)(id,SEL,id))originalAosEmail)(self,cmd,email);
}
static BOOL installDirectICloudIMAP(void){
 if(originalAosEmail)return YES;
 Class cls=NSClassFromString(@"NFAosImapAccountProxy");const char *image=cls?class_getImageName(cls):NULL;
 if(!image||!strstr(image,"/Mountain Lion Notes.app/Contents/Frameworks/Notes.framework/"))return NO;
 Method m=class_getClassMethod(cls,sel_registerName("isAOSEmailAddress:"));char *type=m?method_copyReturnType(m):NULL;
 BOOL valid=type&&type[0]=='c'&&method_getNumberOfArguments(m)==3;free(type);if(!valid)return NO;
 originalAosEmail=method_setImplementation(m,(IMP)directICloudEmail);return YES;
}
static id callObject(id obj,const char *name,id arg){return ((id(*)(id,SEL,id))objc_msgSend)(obj,sel_registerName(name),arg);}
static id privateConstant(void *handle,const char *name){id *p=(id *)dlsym(handle,name);return p?*p:nil;}
@interface MLNotesFixedIMAP:NSObject {NSDictionary *info;NSString *login,*secret;}
-(id)initWithInfo:(NSDictionary *)value user:(NSString *)user password:(NSString *)password;
-(id)userName;-(id)emailAddress;-(id)password;-(id)fullName;-(id)receivingAccountInfo;-(id)sendingAccountInfo;-(void)cancel;
@end
@implementation MLNotesFixedIMAP
-(id)initWithInfo:(NSDictionary *)value user:(NSString *)user password:(NSString *)password{if((self=[super init])){info=[value copy];login=[user copy];secret=[password copy];}return self;}
-(id)userName{return login;}-(id)emailAddress{return login;}-(id)password{return secret;}-(id)fullName{return @"iCloud Notes";}
-(id)receivingAccountInfo{return info;}-(id)sendingAccountInfo{return nil;}-(void)cancel{}
-(void)dealloc{[info release];[login release];[secret release];[super dealloc];}
@end
@interface MLNotesAccountsUI:NSObject
-(void)install:(NSNotification *)notification;
-(void)openAccounts:(id)sender;
-(void)addICloudNotes:(id)sender;
-(void)beginICloudSetup;
-(void)createICloud:(id)sender;
-(void)cancelICloud:(id)sender;
@end
@implementation MLNotesAccountsUI
-(void)install:(NSNotification *)notification{
 (void)notification;
 installDirectICloudIMAP();
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
 if([accountWindow attachedSheet]){NSBeep();return;}
 [accountWindow makeKeyAndOrderFront:nil];[accountWindow makeMainWindow];
 [self performSelector:@selector(beginICloudSetup) withObject:nil afterDelay:0];
}
-(void)beginICloudSetup{
 if(cloudWindow){[cloudWindow makeKeyAndOrderFront:nil];return;}
 cloudWindow=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,480,250) styleMask:NSTitledWindowMask|NSClosableWindowMask backing:NSBackingStoreBuffered defer:NO];
 [cloudWindow setReleasedWhenClosed:NO];[cloudWindow setTitle:@"Add iCloud Notes Account"];
 NSView *view=[cloudWindow contentView];
 NSArray *labels=@[@"iCloud Mail address",@"App-specific password"];
 for(unsigned i=0;i<2;i++){
  NSTextField *label=[[[NSTextField alloc] initWithFrame:NSMakeRect(20,180-i*55,170,24)] autorelease];[label setStringValue:labels[i]];[label setEditable:NO];[label setBordered:NO];[label setDrawsBackground:NO];[view addSubview:label];
 }
 cloudEmail=[[NSTextField alloc] initWithFrame:NSMakeRect(195,180,265,24)];[view addSubview:cloudEmail];
 cloudPassword=[[NSSecureTextField alloc] initWithFrame:NSMakeRect(195,125,265,24)];[view addSubview:cloudPassword];
 cloudStatus=[[NSTextField alloc] initWithFrame:NSMakeRect(20,60,440,48)];[cloudStatus setStringValue:@"Tests legacy iCloud Notes using a secure IMAP connection. Upgraded iCloud notes are not supported."];[cloudStatus setEditable:NO];[cloudStatus setBordered:NO];[cloudStatus setDrawsBackground:NO];[view addSubview:cloudStatus];
 for(unsigned i=0;i<2;i++){
  NSButton *button=[[[NSButton alloc] initWithFrame:NSMakeRect(260+i*100,15,95,30)] autorelease];[button setTitle:i?@"Add Account":@"Cancel"];[button setBezelStyle:NSRoundedBezelStyle];[button setTarget:self];[button setAction:i?@selector(createICloud:):@selector(cancelICloud:)];[view addSubview:button];
 }
 [cloudWindow center];[cloudWindow makeKeyAndOrderFront:nil];
 fputs("PRIVATE_NOTES_ICLOUD_FORM_READY\n",stderr);
}
-(void)cancelICloud:(id)sender{(void)sender;[cloudPassword setStringValue:@""];[cloudWindow orderOut:nil];}
-(void)createICloud:(id)sender{(void)sender;const char *stage="input";@try{
 NSString *email=[[cloudEmail stringValue] stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
 if([email rangeOfString:@"@"].location==NSNotFound||![[cloudPassword stringValue] length]){[cloudStatus setStringValue:@"Enter your full iCloud Mail address and app-specific password."];return;}
 stage="framework_constants";
 if(!installDirectICloudIMAP()){[cloudStatus setStringValue:@"Private IMAP routing could not be installed. Please collect the log."];fputs("PRIVATE_NOTES_ICLOUD_DIRECT_ROUTING_UNAVAILABLE\n",stderr);return;}
 NSString *frameworks=[[[NSBundle mainBundle] bundlePath] stringByAppendingPathComponent:@"Contents/Frameworks"];
 void *ia=dlopen([[frameworks stringByAppendingPathComponent:@"InternetAccounts.framework/Versions/A/InternetAccounts"] fileSystemRepresentation],RTLD_NOW|RTLD_LOCAL);
 void *message=dlopen([[frameworks stringByAppendingPathComponent:@"Message.framework/Versions/B/Message"] fileSystemRepresentation],RTLD_NOW|RTLD_LOCAL);
 id type=privateConstant(ia,"kIAServiceIMAP"),ssl=privateConstant(message,"MailAccountSSLEnabled"),port=privateConstant(message,"MailAccountPortNumber"),host=privateConstant(message,"MailAccountHostname"),auth=privateConstant(message,"MailAccountAuthenticationScheme"),scheme=privateConstant(message,"AuthSchemeClearText");
 if(!type||!ssl||!port||!host||!auth||!scheme){[cloudStatus setStringValue:@"Private IMAP settings could not be loaded. Please collect the log."];fputs("PRIVATE_NOTES_ICLOUD_CONSTANTS_UNAVAILABLE\n",stderr);return;}
 stage="provider_lookup";
 id manager=((id(*)(id,SEL))objc_msgSend)(NSClassFromString(@"IAPluginManager"),sel_registerName("shared"));
 id plugin=callObject(manager,"pluginWithIdentifier:",@"org.ntest.Notes.iaplugin");
 Class cls=NSClassFromString(@"IANotesAccountSetupInput");
 Method create=class_getInstanceMethod(object_getClass(plugin),sel_registerName("createAccountForInput:discoveredResult:error:"));
 char *ret=create?method_copyReturnType(create):NULL;BOOL valid=ret&&ret[0]=='@'&&method_getNumberOfArguments(create)==5;free(ret);
 if(!cls||!valid){[cloudStatus setStringValue:@"Private Notes provider is unavailable. Please collect the log."];return;}
 stage="input_settings";
 id input=[[cls alloc] init];
 for(NSArray *setting in @[@[@"setEmailAddress:",email],@[@"setUserName:",email],@[@"setFullName:",@"iCloud Notes IMAP Trial"],@[@"setAccountDescription:",@"iCloud Notes IMAP Trial"],@[@"setHostname:",@"imap.mail.me.com"],@[@"setAccountType:",type],@[@"setPassword:",[cloudPassword stringValue]]])callObject(input,[setting[0] UTF8String],setting[1]);
 stage="fixed_configurator";
 MLNotesFixedIMAP *fixed=[[[MLNotesFixedIMAP alloc] initWithInfo:@{host:@"imap.mail.me.com",ssl:@YES,port:@993,auth:scheme} user:email password:[cloudPassword stringValue]] autorelease];
 id old=((id(*)(id,SEL))objc_msgSend)(plugin,sel_registerName("accountAutoconfigurator"));[old retain];
 stage="install_configurator";
 callObject(plugin,"setAccountAutoconfigurator:",fixed);
 NSError *error=nil;id uid=nil;
 stage="native_create";
 @try{uid=((id(*)(id,SEL,id,id,NSError **))objc_msgSend)(plugin,sel_registerName("createAccountForInput:discoveredResult:error:"),input,nil,&error);}
 @finally{callObject(plugin,"setAccountAutoconfigurator:",old);[old release];callObject(input,"setPassword:",@"");[input release];[cloudPassword setStringValue:@""];}
 fprintf(stderr,"PRIVATE_NOTES_ICLOUD_ACCOUNT_CREATE success=%d error_present=%d\n",uid!=nil,error!=nil);
 [cloudStatus setStringValue:uid?@"Account created. Check the Notes sidebar after two minutes, then collect the log.":@"Account creation failed. Please collect the log."];
 }@catch(NSException *e){
 NSString *reason=[e reason]?:@"";
 NSRegularExpression *pattern=[NSRegularExpression regularExpressionWithPattern:@"^[-+]\\[([A-Za-z_][A-Za-z0-9_]* [A-Za-z_][A-Za-z0-9_:]*)\\]" options:0 error:NULL];
 NSTextCheckingResult *match=[pattern firstMatchInString:reason options:0 range:NSMakeRange(0,[reason length])];
 if(match)fprintf(stderr,"PRIVATE_NOTES_ICLOUD_MISSING_METHOD %s\n",[[reason substringWithRange:[match rangeAtIndex:1]] UTF8String]);
 fprintf(stderr,"PRIVATE_NOTES_ICLOUD_EXCEPTION_FLAGS unrecognized=%d nil_argument=%d\n",[reason rangeOfString:@"unrecognized selector"].location!=NSNotFound,[reason rangeOfString:@"nil"].location!=NSNotFound);
 [cloudPassword setStringValue:@""];[cloudStatus setStringValue:@"Setup failed. Please collect the log."];fprintf(stderr,"PRIVATE_NOTES_ICLOUD_FORM_EXCEPTION %s stage=%s\n",[[e name] UTF8String],stage);}
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
 installDirectICloudIMAP();
 ui=[[MLNotesAccountsUI alloc] init];
 [[NSNotificationCenter defaultCenter] addObserver:ui selector:@selector(install:) name:NSApplicationDidFinishLaunchingNotification object:nil];
}}
