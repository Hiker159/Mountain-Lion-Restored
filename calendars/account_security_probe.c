#include <Security/Security.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
int main(int argc,char **argv){
 if(argc!=2)return 1;
 void *h=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
 if(!h){printf("SECURITY_WRAPPER_LOAD_FAILED %s\n",dlerror());return 1;}
 const char *symbols[]={"SecKeychainFindGenericPassword","SecKeychainAddGenericPassword","SecItemAdd","SecItemCopyMatching","SecItemDelete","SecItemUpdate","SecKeychainFindInternetPassword","SecKeychainItemCopyFromPersistentReference","SecKeychainItemDelete","SecKeychainItemModifyContent","SecKeychainItemCopyContent","SecKeychainItemModifyAttributesAndData","SecKeychainItemSetAccess","SecKeychainItemCopyAccess","SecKeychainItemCreatePersistentReference"};
 for(unsigned i=0;i<sizeof(symbols)/sizeof(symbols[0]);i++){
  void *fn=dlsym(h,symbols[i]);Dl_info info;
  if(!fn||!dladdr(fn,&info)||!strstr(info.dli_fname,"MLAccountSecurity.dylib")){printf("WRAPPER_EXPORT_FAILED %s\n",symbols[i]);return 2;}
 }
 puts("PRIVATE_CREDENTIAL_WRAPPER_EXPORTS=15");
 typedef OSStatus(*Query)(CFDictionaryRef,CFTypeRef *);
 Query query=(Query)dlsym(h,"SecItemCopyMatching");
 CFDictionaryRef empty=CFDictionaryCreate(NULL,NULL,NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
 OSStatus status=query(empty,NULL);CFRelease(empty);
 printf("EMPTY_QUERY_REJECTION=%d\n",(int)status);if(status!=errSecParam)return 3;
 typedef OSStatus(*Find)(CFTypeRef,UInt32,const char *,UInt32,const char *,UInt32 *,void **,SecKeychainItemRef *);
 Find find=(Find)dlsym(h,"SecKeychainFindGenericPassword");
 status=find(NULL,UINT32_MAX,"x",0,NULL,NULL,NULL,NULL);
 printf("OVERSIZED_SERVICE_REJECTION=%d\n",(int)status);if(status!=errSecParam)return 4;
 puts("CREDENTIAL_WRAPPER_CHECK_PASS");
 puts("Only invalid queries tested; no native Keychain operation requested.");return 0;
}
