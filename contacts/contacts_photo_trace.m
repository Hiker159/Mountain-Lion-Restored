#import "contacts_icloud_push_compat.m"
static IMP imageSave,imageWrite,personSet,editorSet,mapperSet;
static BOOL tracePersonSet(id self,SEL cmd,id data){
 BOOL result=((BOOL(*)(id,SEL,id))personSet)(self,cmd,data);
 fprintf(stderr,"PRIVATE_CONTACTS_PHOTO person_set data_present=%d success=%d\n",[data isKindOfClass:[NSData class]]&&[data length]>0,result);return result;
}
static void traceEditorSet(id self,SEL cmd,id image){
 fputs(image?"PRIVATE_CONTACTS_PHOTO editor_set image_present=1\n":"PRIVATE_CONTACTS_PHOTO editor_set image_present=0\n",stderr);
 ((void(*)(id,SEL,id))editorSet)(self,cmd,image);
}
static BOOL traceMapperSet(id self,SEL cmd,id data,id person,id book,NSError **error){
 BOOL result=((BOOL(*)(id,SEL,id,id,id,NSError **))mapperSet)(self,cmd,data,person,book,error);
 fprintf(stderr,"PRIVATE_CONTACTS_PHOTO mapper_set data_present=%d person_present=%d book_present=%d success=%d\n",[data isKindOfClass:[NSData class]]&&[data length]>0,person!=nil,book!=nil,result);return result;
}
static BOOL signatureMatches(Method m,char type,unsigned count){
 char *r=m?method_copyReturnType(m):NULL;BOOL good=r&&r[0]==type&&method_getNumberOfArguments(m)==count;free(r);return good;
}
static BOOL traceImageSave(id self,SEL cmd,id data,id kind){
 BOOL result=((BOOL(*)(id,SEL,id,id))imageSave)(self,cmd,data,kind);
 fprintf(stderr,"PRIVATE_CONTACTS_PHOTO save data_present=%d success=%d\n",[data isKindOfClass:[NSData class]]&&[data length]>0,result);return result;
}
static BOOL traceImageWrite(id self,SEL cmd,id data,id url){
 NSString *path=[url isKindOfClass:[NSURL class]]?[url path]:nil;
 NSString *privateRoot=[NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/ML-GContact"];
 NSString *stockRoot=[NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/AddressBook"];
 BOOL privatePath=[path hasPrefix:[privateRoot stringByAppendingString:@"/"]],stockPath=[path hasPrefix:[stockRoot stringByAppendingString:@"/"]];
 BOOL result=((BOOL(*)(id,SEL,id,id))imageWrite)(self,cmd,data,url);
 fprintf(stderr,"PRIVATE_CONTACTS_PHOTO write private_path=%d stock_path=%d success=%d\n",privatePath,stockPath,result);return result;
}
__attribute__((constructor)) static void installPhotoTrace(void){
 @autoreleasepool{
 Class cls=NSClassFromString(@"ABPerson");const char *path=cls?class_getImageName(cls):NULL;
 if(!path||!strstr(path,"/Mountain Lion Contacts.app/Contents/")||!strstr(path,"/AddressBook.framework/"))return;
 Method ps=class_getInstanceMethod(cls,NSSelectorFromString(@"setImageData:"));
 Method es=class_getInstanceMethod(NSClassFromString(@"ABCardViewUndoableDataSource"),NSSelectorFromString(@"setImage:"));
 Method ms=class_getClassMethod(NSClassFromString(@"AK"),NSSelectorFromString(@"setImageData:onPerson:inAddressBook:error:"));
 if(signatureMatches(ps,'c',3))personSet=method_setImplementation(ps,(IMP)tracePersonSet);
 if(signatureMatches(es,'v',3))editorSet=method_setImplementation(es,(IMP)traceEditorSet);
 if(signatureMatches(ms,'c',6))mapperSet=method_setImplementation(ms,(IMP)traceMapperSet);
 fprintf(stderr,"PRIVATE_CONTACTS_PHOTO handoff_trace person=%d editor=%d mapper=%d\n",personSet!=NULL,editorSet!=NULL,mapperSet!=NULL);
 Method save=class_getInstanceMethod(cls,NSSelectorFromString(@"_saveImageDataToDisk:kind:"));
 Method write=class_getInstanceMethod(cls,NSSelectorFromString(@"_writeImageData:toURL:"));
 char *s=save?method_copyReturnType(save):NULL,*w=write?method_copyReturnType(write):NULL;
 if(s&&w&&s[0]=='c'&&w[0]=='c'&&method_getNumberOfArguments(save)==4&&method_getNumberOfArguments(write)==4){
 imageSave=method_setImplementation(save,(IMP)traceImageSave);imageWrite=method_setImplementation(write,(IMP)traceImageWrite);
 fputs("PRIVATE_CONTACTS_PHOTO trace_installed\n",stderr);
 }else fputs("PRIVATE_CONTACTS_PHOTO unavailable_signatures\n",stderr);
 free(s);free(w);
 }
}
