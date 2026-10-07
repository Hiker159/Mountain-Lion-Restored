#import "contacts_export_compat.m"
#import <dispatch/dispatch.h>
// Mountain Lion's photo GETs opt into MobileMe token preauthentication.
// Preserve ordinary DAV authentication and alter only private CardDAV photo GETs.
static IMP originalPhotoProperties,originalPhotoSend,originalPhotoRequestLog;
static id photoObjectGetter(id obj,const char *name){
 SEL sel=sel_registerName(name);Method m=class_getInstanceMethod(object_getClass(obj),sel);
 if(!signatureMatches(m,'@',2))return nil;
 return ((id(*)(id,SEL))method_getImplementation(m))(obj,sel);
}
static BOOL isPrivateCardDAVPhoto(id task){
 Class get=NSClassFromString(@"CoreDAVGetTask");
 if(!get||![task isKindOfClass:get])return NO;
 id delegate=photoObjectGetter(task,"delegate");
 Class controller=NSClassFromString(@"CDXController");
 const char *image=controller?class_getImageName(controller):NULL;
 if(!controller||!image||!strstr(image,"/Mountain Lion Contacts.app/Contents/PlugIns/ContactSources/CardDAVPlugin.sourcebundle/")||![delegate isKindOfClass:controller])return NO;
 id url=photoObjectGetter(task,"url");
 if(![url isKindOfClass:[NSURL class]])return NO;
 NSString *host=[[url host] lowercaseString];
 return [[url scheme] caseInsensitiveCompare:@"https"]==NSOrderedSame&&([host isEqualToString:@"icloud.com"]||[host hasSuffix:@".icloud.com"]);
}
static void photoProperties(id self,SEL cmd,id properties){
 id replacement=properties;
 Class get=NSClassFromString(@"CoreDAVGetTask");
 if(get&&[self isKindOfClass:get]){
  id delegate=photoObjectGetter(self,"delegate");
  const char *image=delegate?class_getImageName(object_getClass(delegate)):NULL;
  fprintf(stderr,"PRIVATE_CONTACTS_PHOTO_AUTH get_properties delegate=%s private_plugin=%d eligible=%d\n",delegate?class_getName(object_getClass(delegate)):"none",image&&strstr(image,"/CardDAVPlugin.sourcebundle/")!=NULL,isPrivateCardDAVPhoto(self));
 }

 if([properties isKindOfClass:[NSDictionary class]]&&isPrivateCardDAVPhoto(self)){
  CFStringRef *symbol=(CFStringRef *)dlsym(RTLD_DEFAULT,"kCFURLRequestPreAuthXMMeAuthToken");
  id key=symbol?(id)*symbol:nil;
  if(key&&[properties objectForKey:key]){
   NSMutableDictionary *copy=[[properties mutableCopy] autorelease];[copy removeObjectForKey:key];replacement=copy;
   fputs("PRIVATE_CONTACTS_PHOTO_AUTH legacy_token_preauth_removed\n",stderr);
  }else fputs("PRIVATE_CONTACTS_PHOTO_AUTH token_property_unavailable\n",stderr);
 }
 ((void(*)(id,SEL,id))originalPhotoProperties)(self,cmd,replacement);
}
static BOOL photoAppleURL(id url){
 if(![url isKindOfClass:[NSURL class]])return NO;
 NSString *host=[[url host] lowercaseString];NSNumber *port=[(NSURL *)url port];
 return [[[url scheme] lowercaseString] isEqualToString:@"https"]&&(!port||[port integerValue]==443)&&([host isEqualToString:@"icloud.com"]||[host hasSuffix:@".icloud.com"]);
}
static id photoSend(id self,SEL cmd,id connection,id request,id response){
 id outgoing=((id(*)(id,SEL,id,id,id))originalPhotoSend)(self,cmd,connection,request,response);
 Class get=NSClassFromString(@"CoreDAVGetTask");
 if(get&&[self isKindOfClass:get])fprintf(stderr,"PRIVATE_CONTACTS_PHOTO_AUTH send_get eligible=%d\n",isPrivateCardDAVPhoto(self));
 if(!isPrivateCardDAVPhoto(self))return outgoing;
 BOOL requestPresent=[outgoing isKindOfClass:[NSURLRequest class]];
 fprintf(stderr,"PRIVATE_CONTACTS_PHOTO_AUTH outgoing_request=%d apple_https=%d get_method=%d\n",requestPresent,requestPresent&&photoAppleURL([outgoing URL]),requestPresent&&[[outgoing HTTPMethod] isEqualToString:@"GET"]);
 if(!requestPresent)return outgoing;
 NSMutableURLRequest *copy=[[outgoing mutableCopy] autorelease];
 // Do not carry the added credential to redirects outside Apple's HTTPS hosts.
 if(!photoAppleURL([copy URL])){
  [copy setValue:nil forHTTPHeaderField:@"Authorization"];return copy;
 }
 if(![[copy HTTPMethod] isEqualToString:@"GET"])return outgoing;
 // Legacy redirects add URL user information. Authenticate through the header
 // instead, keeping credentials out of the request URL and URL-based logs.
 NSURLComponents *components=[NSURLComponents componentsWithURL:[copy URL] resolvingAgainstBaseURL:NO];
 if(!components)return outgoing;
 BOOL embedded=[components user]!=nil||[components password]!=nil;
 [components setUser:nil];[components setPassword:nil];
 NSURL *clean=[components URL];if(!clean||!photoAppleURL(clean))return outgoing;
 [copy setURL:clean];
 fprintf(stderr,"PRIVATE_CONTACTS_PHOTO_AUTH url_login_removed=%d\n",embedded);
 id provider=photoObjectGetter(self,"accountInfoProvider");
 id user=photoObjectGetter(provider,"user"),password=photoObjectGetter(provider,"password");
 if(![user isKindOfClass:[NSString class]]||![password isKindOfClass:[NSString class]]||![user length]||![password length]){
  fprintf(stderr,"PRIVATE_CONTACTS_PHOTO_AUTH password_unavailable user_present=%d password_present=%d\n",[user isKindOfClass:[NSString class]]&&[user length]>0,[password isKindOfClass:[NSString class]]&&[password length]>0);return outgoing;
 }
 NSString *pair=[NSString stringWithFormat:@"%@:%@",user,password];
 NSString *encoded=[[pair dataUsingEncoding:NSUTF8StringEncoding] base64EncodedStringWithOptions:0];
 [copy setValue:[@"Basic " stringByAppendingString:encoded] forHTTPHeaderField:@"Authorization"];
 fputs("PRIVATE_CONTACTS_PHOTO_AUTH password_header_applied\n",stderr);return copy;
}
static void photoRequestLog(id self,SEL cmd,id request){
 if([request isKindOfClass:[NSURLRequest class]]&&[request valueForHTTPHeaderField:@"Authorization"]){
  NSMutableURLRequest *copy=[[request mutableCopy] autorelease];[copy setValue:@"[redacted]" forHTTPHeaderField:@"Authorization"];
  ((void(*)(id,SEL,id))originalPhotoRequestLog)(self,cmd,copy);return;
 }
 ((void(*)(id,SEL,id))originalPhotoRequestLog)(self,cmd,request);
}
static BOOL tryInstallPhotoAuthentication(void){
 if(originalPhotoProperties&&originalPhotoSend)return YES;
 Class cls=NSClassFromString(@"CoreDAVTask");const char *image=cls?class_getImageName(cls):NULL;
 if(!image||!strstr(image,"/Mountain Lion Contacts.app/Contents/Frameworks/CoreDAV.framework/"))return NO;
 Method m=class_getInstanceMethod(cls,sel_registerName("setRequestProperties:"));
 if(!signatureMatches(m,'v',3))return NO;
 Method send=class_getInstanceMethod(cls,sel_registerName("connection:willSendRequest:redirectResponse:"));
 Class logger=NSClassFromString(@"CoreDAVRequestLogger");const char *loggerImage=logger?class_getImageName(logger):NULL;
 Method log=class_getInstanceMethod(logger,sel_registerName("logCoreDAVRequest:"));
 if(!signatureMatches(send,'@',5)||!signatureMatches(log,'v',3)||!loggerImage||!strstr(loggerImage,"/Mountain Lion Contacts.app/Contents/Frameworks/CoreDAV.framework/"))return NO;
 originalPhotoRequestLog=method_setImplementation(log,(IMP)photoRequestLog);
 originalPhotoSend=method_setImplementation(send,(IMP)photoSend);
 originalPhotoProperties=method_setImplementation(m,(IMP)photoProperties);
 fputs("PRIVATE_CONTACTS_PHOTO_AUTH installed\n",stderr);return YES;
}
__attribute__((constructor)) static void installPhotoAuthentication(void){
 @autoreleasepool{
  [[NSNotificationCenter defaultCenter] addObserverForName:NSBundleDidLoadNotification object:nil queue:nil usingBlock:^(NSNotification *note){
   (void)note;@autoreleasepool{tryInstallPhotoAuthentication();}
  }];
  if(tryInstallPhotoAuthentication())return;
  fputs("PRIVATE_CONTACTS_PHOTO_AUTH waiting_for_private_framework\n",stderr);
  // The CardDAV source loads CoreDAV after bootstrap constructors have run.
  // Retry on the main run loop until Objective-C classes are registered.
  dispatch_source_t timer=dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER,0,0,dispatch_get_main_queue());
  dispatch_source_set_timer(timer,dispatch_time(DISPATCH_TIME_NOW,0),NSEC_PER_SEC,NSEC_PER_SEC/10);
  dispatch_source_set_event_handler(timer,^{@autoreleasepool{if(tryInstallPhotoAuthentication())dispatch_source_cancel(timer);}});
  dispatch_resume(timer);
 }
}
