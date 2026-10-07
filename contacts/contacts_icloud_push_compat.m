#import "contacts_account_bootstrap.m"
static void skipLegacyPushConfiguration(id self,SEL cmd,id service,id user,id secret){
 (void)self;(void)cmd;(void)service;(void)user;(void)secret;
 fputs("PRIVATE_CONTACTS_PUSH configuration_skipped polling_fallback\n",stderr);
}
static id skipLegacyPushCenter(id self,SEL cmd,id info,id port){
 (void)cmd;(void)info;(void)port;
 [self release];
 fputs("PRIVATE_CONTACTS_PUSH center_skipped polling_fallback\n",stderr);return nil;
}
__attribute__((constructor)) static void installPrivatePushFallback(void){
 @autoreleasepool{
 Class cls=NSClassFromString(@"ABPushNotificationCenter");const char *path=cls?class_getImageName(cls):NULL;
 if(!path||!strstr(path,"/Mountain Lion Contacts.app/Contents/")||!strstr(path,"/AddressBook.framework/")){
  fputs("PRIVATE_CONTACTS_PUSH invalid_private_class\n",stderr);_exit(78);
 }
 Method config=class_getClassMethod(cls,NSSelectorFromString(@"configureService:userName:password:"));
 Method center=class_getInstanceMethod(cls,NSSelectorFromString(@"initWithNotificationInfo:sourceUID:"));
 char *ct=config?method_copyReturnType(config):NULL,*rt=center?method_copyReturnType(center):NULL;
 BOOL valid=ct&&ct[0]=='v'&&rt&&rt[0]=='@'&&method_getNumberOfArguments(config)==5&&method_getNumberOfArguments(center)==4;
 free(ct);free(rt);if(!valid){fputs("PRIVATE_CONTACTS_PUSH incompatible_methods\n",stderr);_exit(78);}
 method_setImplementation(config,(IMP)skipLegacyPushConfiguration);
 method_setImplementation(center,(IMP)skipLegacyPushCenter);
 fputs("PRIVATE_CONTACTS_PUSH polling_fallback_installed\n",stderr);
 }
}
