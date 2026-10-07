#import <Cocoa/Cocoa.h>
#import <objc/message.h>
#include <stdio.h>
#import <objc/runtime.h>
#include <dlfcn.h>
static id pane;
static NSWindow *accountWindow,*cloudWindow;
static NSTextField *cloudEmail,*cloudStatus;
static NSSecureTextField *cloudPassword;
static IMP oldConnect,oldRefresh,oldFolders,oldAdd,oldUpdate,oldDelete;
static BOOL isPrivateCloudProxy(id proxy){return [((id(*)(id,SEL))objc_msgSend)(proxy,sel_registerName("hostname")) isEqual:@"imap.mail.me.com"];}
static BOOL traceConnect(id self,SEL cmd,id connection){
 BOOL cloud=isPrivateCloudProxy(self);if(cloud)fputs("PRIVATE_NOTES_ICLOUD_CONNECT begin\n",stderr);
 BOOL result=((BOOL(*)(id,SEL,id))oldConnect)(self,cmd,connection);
 if(cloud)fprintf(stderr,"PRIVATE_NOTES_ICLOUD_CONNECT success=%d\n",result);return result;
}
static void traceRefresh(id self,SEL cmd){
 BOOL cloud=isPrivateCloudProxy(self);if(cloud)fprintf(stderr,"PRIVATE_NOTES_ICLOUD_REFRESH state=%ld main_thread=%d\n",(long)((NSInteger(*)(id,SEL))objc_msgSend)(self,sel_registerName("accountState")),[NSThread isMainThread]);
 ((void(*)(id,SEL))oldRefresh)(self,cmd);
 if(cloud)fputs("PRIVATE_NOTES_ICLOUD_REFRESH returned\n",stderr);
}
static void traceFolders(id self,SEL cmd){
 BOOL cloud=isPrivateCloudProxy(self);if(cloud)fputs("PRIVATE_NOTES_ICLOUD_FOLDERS begin\n",stderr);
 ((void(*)(id,SEL))oldFolders)(self,cmd);
 if(cloud)fputs("PRIVATE_NOTES_ICLOUD_FOLDERS returned\n",stderr);
}
static BOOL tracePush(IMP original,const char *operation,id self,SEL cmd,id note,id folder,id proxy,BOOL *fatal){
 BOOL cloud=isPrivateCloudProxy(proxy);if(cloud)fprintf(stderr,"PRIVATE_NOTES_ICLOUD_UPLOAD operation=%s begin\n",operation);
 BOOL result=((BOOL(*)(id,SEL,id,id,id,BOOL *))original)(self,cmd,note,folder,proxy,fatal);
 if(cloud)fprintf(stderr,"PRIVATE_NOTES_ICLOUD_UPLOAD operation=%s success=%d\n",operation,result);return result;
}
static BOOL traceAdd(id s,SEL c,id n,id f,id p,BOOL *e){return tracePush(oldAdd,"add",s,c,n,f,p,e);}
static BOOL traceUpdate(id s,SEL c,id n,id f,id p,BOOL *e){return tracePush(oldUpdate,"update",s,c,n,f,p,e);}
static BOOL traceDelete(id s,SEL c,id n,id f,id p,BOOL *e){return tracePush(oldDelete,"delete",s,c,n,f,p,e);}
static BOOL installTraceMethod(Class cls,const char *name,char result,unsigned args,IMP hook,IMP *old){
 if(*old)return YES;const char *image=cls?class_getImageName(cls):NULL;
 if(!image||!strstr(image,"/Mountain Lion Notes.app/Contents/Frameworks/Notes.framework/"))return NO;
 Method m=class_getInstanceMethod(cls,sel_registerName(name));char *type=m?method_copyReturnType(m):NULL;
 BOOL valid=type&&type[0]==result&&method_getNumberOfArguments(m)==args;free(type);if(!valid)return NO;
 *old=method_setImplementation(m,hook);return YES;
}
static void installCloudTrace(void){
 Class p=NSClassFromString(@"NFIMAPAccountProxy"),u=NSClassFromString(@"NFLocalToIMAPPusher");
 BOOL good=installTraceMethod(p,"connectAndAuthenticate:",'c',3,(IMP)traceConnect,&oldConnect);
 good=installTraceMethod(p,"synchronizeAllFolders",'v',2,(IMP)traceRefresh,&oldRefresh)&&good;
 good=installTraceMethod(p,"synchronizeFolderList",'v',2,(IMP)traceFolders,&oldFolders)&&good;
 good=installTraceMethod(u,"addNoteToRemote:inFolder:accountProxy:errorIsFatal:",'c',6,(IMP)traceAdd,&oldAdd)&&good;
 good=installTraceMethod(u,"updateNoteOnRemote:inFolder:accountProxy:errorIsFatal:",'c',6,(IMP)traceUpdate,&oldUpdate)&&good;
 good=installTraceMethod(u,"deleteNoteFromRemoteWithID:fromFolder:accountProxy:errorIsFatal:",'c',6,(IMP)traceDelete,&oldDelete)&&good;
 fprintf(stderr,"PRIVATE_NOTES_ICLOUD_TRACE ready=%d\n",good);
}
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
static IMP originalIMAPFactory;
static __thread BOOL creatingPrivateICloud;
static id privateIMAPFactory(id self,SEL cmd,id input,id config){
 id proxy=((id(*)(id,SEL,id,id))originalIMAPFactory)(self,cmd,input,config);
 if(creatingPrivateICloud&&proxy){
  id host=((id(*)(id,SEL))objc_msgSend)(proxy,sel_registerName("hostname"));
  BOOL ssl=((BOOL(*)(id,SEL))objc_msgSend)(proxy,sel_registerName("usesSSL"));
  unsigned short port=((unsigned short(*)(id,SEL))objc_msgSend)(proxy,sel_registerName("portNumber"));
  id password=((id(*)(id,SEL))objc_msgSend)(input,sel_registerName("password"));
  if([host isEqual:@"imap.mail.me.com"]&&ssl&&port==993&&[password isKindOfClass:[NSString class]]&&[password length]){
   ((void(*)(id,SEL,id))objc_msgSend)(proxy,sel_registerName("setPassword:"),password);
   id stored=((id(*)(id,SEL))objc_msgSend)(proxy,sel_registerName("password"));
   fprintf(stderr,"PRIVATE_NOTES_ICLOUD_PASSWORD saved_retrievable=%d\n",[stored isKindOfClass:[NSString class]]&&[stored length]>0);
  }else fputs("PRIVATE_NOTES_ICLOUD_PASSWORD settings_guard_failed\n",stderr);
 }
 return proxy;
}
static BOOL installIMAPPassword(id plugin){
 if(originalIMAPFactory)return YES;
 Class cls=object_getClass(plugin);const char *image=cls?class_getImageName(cls):NULL;
 if(!image||!strstr(image,"/Mountain Lion Notes.app/Contents/AccountPlugins/Notes.iaplugin/"))return NO;
 Method m=class_getInstanceMethod(cls,sel_registerName("_newIMAPAccountProxyFromSetupInput:autoconfigurator:"));
 char *type=m?method_copyReturnType(m):NULL;BOOL valid=type&&type[0]=='@'&&method_getNumberOfArguments(m)==4;free(type);
 if(!valid)return NO;
 originalIMAPFactory=method_setImplementation(m,(IMP)privateIMAPFactory);return YES;
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
 installCloudTrace();
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
 id type=privateConstant(ia,"kIAServiceIMAP"),ssl=privateConstant(message,"MailAccountSSLEnabled"),port=privateConstant(message,"MailAccountPortNumber"),host=privateConstant(message,"MailAccountServerName"),auth=privateConstant(message,"MailAccountAuthenticationScheme"),scheme=privateConstant(message,"AuthSchemeClearText");
 if(!type||!ssl||!port||!host||!auth||!scheme){[cloudStatus setStringValue:@"Private IMAP settings could not be loaded. Please collect the log."];fputs("PRIVATE_NOTES_ICLOUD_CONSTANTS_UNAVAILABLE\n",stderr);return;}
 stage="provider_lookup";
 id manager=((id(*)(id,SEL))objc_msgSend)(NSClassFromString(@"IAPluginManager"),sel_registerName("shared"));
 id plugin=callObject(manager,"pluginWithIdentifier:",@"org.ntest.Notes.iaplugin");
 if(!installIMAPPassword(plugin)){[cloudStatus setStringValue:@"Private password setup is unavailable. Please collect the log."];return;}
 Class cls=NSClassFromString(@"IANotesAccountSetupInput");
 Method create=class_getInstanceMethod(object_getClass(plugin),sel_registerName("createAccountForInput:discoveredResult:error:"));
 char *ret=create?method_copyReturnType(create):NULL;BOOL valid=ret&&ret[0]=='@'&&method_getNumberOfArguments(create)==5;free(ret);
 if(!cls||!valid){[cloudStatus setStringValue:@"Private Notes provider is unavailable. Please collect the log."];return;}
 stage="input_settings";
 id input=[[cls alloc] init];
 for(NSArray *setting in @[@[@"setEmailAddress:",email],@[@"setUserName:",email],@[@"setFullName:",@"iCloud Notes Auth Trial"],@[@"setAccountDescription:",@"iCloud Notes Auth Trial"],@[@"setHostname:",@"imap.mail.me.com"],@[@"setAccountType:",type],@[@"setPassword:",[cloudPassword stringValue]]])callObject(input,[setting[0] UTF8String],setting[1]);
 stage="fixed_configurator";
 MLNotesFixedIMAP *fixed=[[[MLNotesFixedIMAP alloc] initWithInfo:@{host:@"imap.mail.me.com",ssl:@YES,port:@993,auth:scheme} user:email password:[cloudPassword stringValue]] autorelease];
 id old=((id(*)(id,SEL))objc_msgSend)(plugin,sel_registerName("accountAutoconfigurator"));[old retain];
 stage="install_configurator";
 callObject(plugin,"setAccountAutoconfigurator:",fixed);
 NSError *error=nil;id uid=nil;
 stage="native_create";
 @try{creatingPrivateICloud=YES;uid=((id(*)(id,SEL,id,id,NSError **))objc_msgSend)(plugin,sel_registerName("createAccountForInput:discoveredResult:error:"),input,nil,&error);}
 @finally{creatingPrivateICloud=NO;callObject(plugin,"setAccountAutoconfigurator:",old);[old release];callObject(input,"setPassword:",@"");[input release];[cloudPassword setStringValue:@""];}
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
 installCloudTrace();
 ui=[[MLNotesAccountsUI alloc] init];
 [[NSNotificationCenter defaultCenter] addObserver:ui selector:@selector(install:) name:NSApplicationDidFinishLaunchingNotification object:nil];
}}
