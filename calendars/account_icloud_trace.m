#import "account_provider_bootstrap.m"
static IMP managedGet,accountGet,headerSet;
static id traceManaged(id self,SEL cmd){
 id value=((id(*)(id,SEL))managedGet)(self,cmd);
 fprintf(stderr,"PRIVATE_ACCOUNT_AUTH_TRACE managed_get secret_present=%d\n",[value isKindOfClass:[NSString class]]&&[value length]>0);return value;
}
static id traceAccount(id self,SEL cmd){
 id value=((id(*)(id,SEL))accountGet)(self,cmd);
 fprintf(stderr,"PRIVATE_ACCOUNT_AUTH_TRACE account_get secret_present=%d\n",[value isKindOfClass:[NSString class]]&&[value length]>0);return value;
}
static void traceHeader(id self,SEL cmd,NSString *value,NSString *field){
 if([field caseInsensitiveCompare:@"Authorization"]==NSOrderedSame){
  NSString *host=[[(NSURLRequest *)self URL] host];BOOL icloud=[host isEqualToString:@"icloud.com"]||[host hasSuffix:@".icloud.com"];
  fprintf(stderr,"PRIVATE_ACCOUNT_AUTH_TRACE request icloud=%d header_present=%d basic=%d\n",icloud,[value length]>0,[value hasPrefix:@"Basic "]);
 }
 ((void(*)(id,SEL,id,id))headerSet)(self,cmd,value,field);
}
static BOOL returnsObject(Method m,unsigned count){
 if(!m||method_getNumberOfArguments(m)!=count)return NO;
 char *type=method_copyReturnType(m);BOOL valid=type&&type[0]=='@';free(type);return valid;
}
__attribute__((constructor)) static void installICloudTrace(void){
 @autoreleasepool{
 Method managed=class_getInstanceMethod(NSClassFromString(@"CalManagedCalDAVAccount"),NSSelectorFromString(@"password"));
 Method account=class_getInstanceMethod(NSClassFromString(@"CalDAVAccount"),NSSelectorFromString(@"password"));
 if(returnsObject(managed,2)&&returnsObject(account,2)&&managed!=account){
  managedGet=method_setImplementation(managed,(IMP)traceManaged);
  accountGet=method_setImplementation(account,(IMP)traceAccount);
  fputs("PRIVATE_ACCOUNT_AUTH_TRACE getters_installed\n",stderr);
 }else fputs("PRIVATE_ACCOUNT_AUTH_TRACE getters_unavailable\n",stderr);
 Method header=class_getInstanceMethod([NSMutableURLRequest class],@selector(setValue:forHTTPHeaderField:));
 char *type=header?method_copyReturnType(header):NULL;
 if(type&&type[0]=='v'&&method_getNumberOfArguments(header)==4){headerSet=method_setImplementation(header,(IMP)traceHeader);fputs("PRIVATE_ACCOUNT_AUTH_TRACE header_installed\n",stderr);}free(type);
 }
}
