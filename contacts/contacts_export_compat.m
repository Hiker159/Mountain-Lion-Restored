#import "contacts_photo_callback_compat.m"
static BOOL noLegacyExportTags(id self,SEL cmd){(void)self;(void)cmd;return NO;}
static void skipTagWrite(id self,SEL cmd,id url,id tags){(void)self;(void)cmd;(void)url;(void)tags;}
static void skipNamedTagWrite(id self,SEL cmd,id url,id name,id tags){(void)self;(void)cmd;(void)url;(void)name;(void)tags;}
__attribute__((constructor)) static void installPrivateExportPanel(void){
 @autoreleasepool{
 if(![[[NSProcessInfo processInfo] processName] isEqualToString:@"Contacts"])return;
 Class cls=NSClassFromString(@"NSSavePanel");
 Method wait=class_getClassMethod(cls,NSSelectorFromString(@"_waitForURL:thenSetTags:"));
 Method named=class_getClassMethod(cls,NSSelectorFromString(@"_waitForURL:withNameFieldString:thenSetTags:"));
 Method client=class_getInstanceMethod(cls,NSSelectorFromString(@"_shouldSetTagsForClient"));
 if(signatureMatches(wait,'v',4))method_setImplementation(wait,(IMP)skipTagWrite);
 if(signatureMatches(named,'v',5))method_setImplementation(named,(IMP)skipNamedTagWrite);
 if(signatureMatches(client,'c',2))method_setImplementation(client,(IMP)noLegacyExportTags);
 fputs("PRIVATE_CONTACTS_EXPORT deferred_tags_disabled\n",stderr);
 Method browser=class_getClassMethod(cls,NSSelectorFromString(@"_useFinderKit"));
 if(signatureMatches(browser,'c',2)){
  method_setImplementation(browser,(IMP)noLegacyExportTags);
  fputs("PRIVATE_CONTACTS_EXPORT finder_browser_disabled\n",stderr);
 }else fputs("PRIVATE_CONTACTS_EXPORT browser_signature_unavailable\n",stderr);
 Method method=class_getClassMethod(cls,NSSelectorFromString(@"_allowTagsFieldInPanel"));
 if(!signatureMatches(method,'c',2)){fputs("PRIVATE_CONTACTS_EXPORT tags_signature_unavailable\n",stderr);return;}
 method_setImplementation(method,(IMP)noLegacyExportTags);
 fputs("PRIVATE_CONTACTS_EXPORT tags_disabled\n",stderr);
 }
}
