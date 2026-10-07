#import "contacts_photo_trace.m"
static IMP legacyPhotoCallback;
static id photoAttribute(id value,NSString *name){
 SEL selector=NSSelectorFromString(name);
 Method method=value?class_getInstanceMethod([value class],selector):NULL;
 if(!signatureMatches(method,'@',2))return nil;
 return ((id(*)(id,SEL))[value methodForSelector:selector])(value,selector);
}
static void modernPhotoCallback(id self,SEL cmd,id view,id attributed){
 (void)cmd;
 id image=photoAttribute(attributed,@"image"),source=photoAttribute(attributed,@"source");
 if(source&&![source isKindOfClass:[NSString class]])source=nil;
 fputs("PRIVATE_CONTACTS_PHOTO callback_adapted\n",stderr);
 ((void(*)(id,SEL,id,id,id))legacyPhotoCallback)(self,NSSelectorFromString(@"profilePictureView:imageDidChange:source:"),view,image,source);
}
__attribute__((constructor)) static void installModernPhotoCallback(void){
 @autoreleasepool{
 Class cls=NSClassFromString(@"ABCardView");const char *path=cls?class_getImageName(cls):NULL;
 if(!path||!strstr(path,"/Mountain Lion Contacts.app/Contents/")||!strstr(path,"/AddressBook.framework/"))return;
 Method old=class_getInstanceMethod(cls,NSSelectorFromString(@"profilePictureView:imageDidChange:source:"));
 if(!signatureMatches(old,'v',5)){fputs("PRIVATE_CONTACTS_PHOTO callback_signature_unavailable\n",stderr);return;}
 legacyPhotoCallback=method_getImplementation(old);
 BOOL added=class_addMethod(cls,NSSelectorFromString(@"profilePictureView:attributedImageDidChange:"),(IMP)modernPhotoCallback,"v@:@@");
 fputs(added?"PRIVATE_CONTACTS_PHOTO callback_adapter_installed\n":"PRIVATE_CONTACTS_PHOTO callback_adapter_already_present\n",stderr);
 }
}
