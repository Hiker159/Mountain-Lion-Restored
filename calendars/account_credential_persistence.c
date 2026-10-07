/* Laptop-only integration test. All password APIs target the disposable keychain. */
#include <Security/Security.h>
#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static void *native,*wrapper;static int failed;
#define FN(h,n,t) ((t)dlsym(h,n))
typedef OSStatus(*GenericAdd)(SecKeychainRef,UInt32,const char *,UInt32,const char *,UInt32,const void *,SecKeychainItemRef *);
typedef OSStatus(*GenericFind)(CFTypeRef,UInt32,const char *,UInt32,const char *,UInt32 *,void **,SecKeychainItemRef *);
typedef OSStatus(*Query)(CFDictionaryRef,CFTypeRef *);
typedef OSStatus(*Delete)(CFDictionaryRef);
typedef OSStatus(*Update)(CFDictionaryRef,CFDictionaryRef);
static int check(const char *label,OSStatus status){printf("%s=%d\n",label,(int)status);if(status)failed=1;return status==0;}
static CFMutableDictionaryRef internet(SecKeychainRef keychain,int query){
 CFMutableDictionaryRef q=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
 CFDictionarySetValue(q,kSecClass,kSecClassInternetPassword);
 if(query){CFArrayRef list=CFArrayCreate(NULL,(const void **)&keychain,1,&kCFTypeArrayCallBacks);CFDictionarySetValue(q,kSecMatchSearchList,list);CFRelease(list);}
 else CFDictionarySetValue(q,kSecUseKeychain,keychain);
 CFDictionarySetValue(q,kSecAttrServer,CFSTR("restored-apps.invalid"));CFDictionarySetValue(q,kSecAttrAccount,CFSTR("dummy-user"));
 CFDictionarySetValue(q,kSecAttrSecurityDomain,CFSTR("Dummy realm"));return q;
}
static int findGeneric(void *provider,SecKeychainRef keychain,const char *expected,SecKeychainItemRef *ref){
 UInt32 length=0;void *data=NULL;OSStatus s=FN(provider,"SecKeychainFindGenericPassword",GenericFind)(keychain,12,"dummy-google",10,"dummy-user",&length,&data,ref);
 int same=s==0&&length==strlen(expected)&&!memcmp(data,expected,length);
 if(data)SecKeychainItemFreeContent(NULL,data);return same;
}
static int findInternet(void *provider,SecKeychainRef keychain,const char *expected){
 CFMutableDictionaryRef q=internet(keychain,1);CFDictionarySetValue(q,kSecReturnData,kCFBooleanTrue);CFTypeRef data=NULL;
 OSStatus s=FN(provider,"SecItemCopyMatching",Query)(q,&data);
 int same=s==0&&data&&CFGetTypeID(data)==CFDataGetTypeID()&&CFDataGetLength((CFDataRef)data)==(CFIndex)strlen(expected)&&!memcmp(CFDataGetBytePtr((CFDataRef)data),expected,strlen(expected));
 if(data)CFRelease(data);CFRelease(q);return same;
}
static void boolean(const char *label,int ok){printf("%s=%s\n",label,ok?"PASS":"FAIL");if(!ok)failed=1;}
int main(int argc,char **argv){
 if(argc!=4)return 1; /* phase, scratch-keychain path, wrapper path */
 native=dlopen("/System/Library/Frameworks/Security.framework/Versions/A/Security",RTLD_NOW|RTLD_LOCAL);
 wrapper=dlopen(argv[3],RTLD_NOW|RTLD_LOCAL);if(!native||!wrapper){puts("PROVIDER_LOAD_FAILED");return 1;}
 SecKeychainSetUserInteractionAllowed(false);
 SecKeychainRef keychain=NULL;int create=!strcmp(argv[1],"create");
 if(create){
  CFArrayRef search=NULL;if(!check("SAVE_SEARCH_LIST",SecKeychainCopySearchList(&search)))return 1;
  const char *password="disposable-test-only";
  OSStatus status=SecKeychainCreate(argv[2],(UInt32)strlen(password),password,false,NULL,&keychain);
  int restored=check("RESTORE_SEARCH_LIST",SecKeychainSetSearchList(search));CFRelease(search);
  if(!check("CREATE_SCRATCH_KEYCHAIN",status)||!restored){if(keychain){SecKeychainDelete(keychain);CFRelease(keychain);}return 1;}
 }else{
  if(!check("OPEN_SCRATCH_KEYCHAIN",SecKeychainOpen(argv[2],&keychain)))return 1;
  const char *password="disposable-test-only";
  if(!check("UNLOCK_SCRATCH_KEYCHAIN",SecKeychainUnlock(keychain,(UInt32)strlen(password),password,true))){CFRelease(keychain);return 1;}
 }
 if(!strcmp(argv[1],"cleanup")){
  int ok=check("DELETE_SCRATCH_KEYCHAIN",SecKeychainDelete(keychain));CFRelease(keychain);return ok?0:1;
 }
 if(create){
  const char *ordinary="ordinary-dummy",*private="private-dummy";
  check("ADD_ORDINARY_GENERIC",FN(native,"SecKeychainAddGenericPassword",GenericAdd)(keychain,12,"dummy-google",10,"dummy-user",(UInt32)strlen(ordinary),ordinary,NULL));
  check("ADD_PRIVATE_GENERIC",FN(wrapper,"SecKeychainAddGenericPassword",GenericAdd)(keychain,12,"dummy-google",10,"dummy-user",(UInt32)strlen(private),private,NULL));
  SecKeychainItemRef item=NULL;boolean("PRIVATE_GENERIC_READ",findGeneric(wrapper,keychain,private,&item));
  if(item){
   typedef OSStatus(*Modify)(SecKeychainItemRef,const SecKeychainAttributeList *,UInt32,const void *);
   private="private-dummy-updated";check("UPDATE_PRIVATE_GENERIC",FN(wrapper,"SecKeychainItemModifyContent",Modify)(item,NULL,(UInt32)strlen(private),private));CFRelease(item);
  }
  CFMutableDictionaryRef q=internet(keychain,0);CFDataRef data=CFDataCreate(NULL,(const UInt8 *)ordinary,(CFIndex)strlen(ordinary));CFDictionarySetValue(q,kSecValueData,data);CFRelease(data);
  check("ADD_ORDINARY_INTERNET",FN(native,"SecItemAdd",Query)(q,NULL));
  private="private-internet";data=CFDataCreate(NULL,(const UInt8 *)private,(CFIndex)strlen(private));CFDictionarySetValue(q,kSecValueData,data);CFRelease(data);
  check("ADD_PRIVATE_INTERNET",FN(wrapper,"SecItemAdd",Query)(q,NULL));CFRelease(q);
  boolean("ORDINARY_GENERIC_UNCHANGED",findGeneric(native,keychain,ordinary,NULL));boolean("ORDINARY_INTERNET_UNCHANGED",findInternet(native,keychain,ordinary));
 }else{
  SecKeychainItemRef item=NULL,ordinaryItem=NULL;
  boolean("GENERIC_SURVIVED_NEW_PROCESS",findGeneric(wrapper,keychain,"private-dummy-updated",&item));
  boolean("INTERNET_SURVIVED_NEW_PROCESS",findInternet(wrapper,keychain,"private-internet"));
  boolean("ORDINARY_GENERIC_UNCHANGED",findGeneric(native,keychain,"ordinary-dummy",&ordinaryItem));
  if(ordinaryItem){
   typedef OSStatus(*ItemDelete)(SecKeychainItemRef);
   OSStatus s=FN(wrapper,"SecKeychainItemDelete",ItemDelete)(ordinaryItem);boolean("FOREIGN_REFERENCE_REJECTED",s==errSecItemNotFound);CFRelease(ordinaryItem);
  }
  if(item){
   typedef OSStatus(*MakeRef)(SecKeychainItemRef,CFDataRef *);typedef OSStatus(*ResolveRef)(CFDataRef,SecKeychainItemRef *);typedef OSStatus(*ItemDelete)(SecKeychainItemRef);
   CFDataRef ref=NULL;SecKeychainItemRef resolved=NULL;
   if(check("CREATE_PRIVATE_PERSISTENT_REFERENCE",FN(wrapper,"SecKeychainItemCreatePersistentReference",MakeRef)(item,&ref))){
    check("RESOLVE_PRIVATE_PERSISTENT_REFERENCE",FN(wrapper,"SecKeychainItemCopyFromPersistentReference",ResolveRef)(ref,&resolved));if(resolved)CFRelease(resolved);CFRelease(ref);
   }
   check("DELETE_PRIVATE_GENERIC",FN(wrapper,"SecKeychainItemDelete",ItemDelete)(item));CFRelease(item);
  }
  CFMutableDictionaryRef q=internet(keychain,1),attrs=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
  const char *updated="private-internet-updated";CFDataRef data=CFDataCreate(NULL,(const UInt8 *)updated,(CFIndex)strlen(updated));CFDictionarySetValue(attrs,kSecValueData,data);CFRelease(data);
  check("UPDATE_PRIVATE_INTERNET",FN(wrapper,"SecItemUpdate",Update)(q,attrs));CFRelease(attrs);
  boolean("PRIVATE_INTERNET_UPDATED",findInternet(wrapper,keychain,updated));check("DELETE_PRIVATE_INTERNET",FN(wrapper,"SecItemDelete",Delete)(q));CFRelease(q);
  boolean("ORDINARY_GENERIC_STILL_PRESENT",findGeneric(native,keychain,"ordinary-dummy",NULL));boolean("ORDINARY_INTERNET_STILL_PRESENT",findInternet(native,keychain,"ordinary-dummy"));
 }
 SecKeychainLock(keychain);CFRelease(keychain);
 puts(failed?"DUMMY_CREDENTIAL_PHASE_FAILED":"DUMMY_CREDENTIAL_PHASE_PASS");return failed?1:0;
}
