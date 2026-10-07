/* Reexport Security with private generic service and Internet realm names.
 * Reference operations inspect namespace attributes before accessing content.
 * This covers the observed imports, not all future authentication mechanisms.
 */
#include <Security/Security.h>
#include <dlfcn.h>
#include <dispatch/dispatch.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>
#include <pwd.h>
#include <unistd.h>
#include <limits.h>
static void *securityHandle;
static dispatch_once_t once;
static void *original(const char *name){
#ifdef ML_ACCOUNT_SECURITY_TEST
 extern void *MLTestSecurityFunction(const char *);
 return MLTestSecurityFunction(name);
#else
 dispatch_once(&once,^{securityHandle=dlopen("/System/Library/Frameworks/Security.framework/Versions/A/Security",RTLD_NOW|RTLD_LOCAL);});
 return securityHandle?dlsym(securityHandle,name):NULL;
#endif
}
static OSStatus privateService(UInt32 length,const char *service,char **out,UInt32 *outLength){
 static const char prefix[]="org.local.RestoredApps/";
 const size_t n=sizeof(prefix)-1;
 if((length&&!service)||length>UINT32_MAX-n)return errSecParam;
 char *buffer=malloc(n+length);
 if(!buffer)return errSecAllocate;
 memcpy(buffer,prefix,n);if(length)memcpy(buffer+n,service,length);
 *out=buffer;*outLength=(UInt32)(n+length);return errSecSuccess;
}
OSStatus SecKeychainFindGenericPassword(CFTypeRef keychainOrArray,UInt32 serviceLength,const char *service,UInt32 accountLength,const char *account,UInt32 *passwordLength,void **passwordData,SecKeychainItemRef *item){
 typedef OSStatus(*Fn)(CFTypeRef,UInt32,const char *,UInt32,const char *,UInt32 *,void **,SecKeychainItemRef *);
 Fn fn=(Fn)original("SecKeychainFindGenericPassword");
 if(!fn)return errSecUnimplemented;
 char *name=NULL;UInt32 length=0;OSStatus result=privateService(serviceLength,service,&name,&length);
 if(result)return result;
 result=fn(keychainOrArray,length,name,accountLength,account,passwordLength,passwordData,item);
 fprintf(stderr,"PRIVATE_KEYSTORE_STATUS generic-find status=%d\n",(int)result);
 free(name);return result;
}
OSStatus SecKeychainAddGenericPassword(SecKeychainRef keychain,UInt32 serviceLength,const char *service,UInt32 accountLength,const char *account,UInt32 passwordLength,const void *passwordData,SecKeychainItemRef *item){
 typedef OSStatus(*Fn)(SecKeychainRef,UInt32,const char *,UInt32,const char *,UInt32,const void *,SecKeychainItemRef *);
 Fn fn=(Fn)original("SecKeychainAddGenericPassword");
 if(!fn)return errSecUnimplemented;
 char *name=NULL;UInt32 length=0;OSStatus result=privateService(serviceLength,service,&name,&length);
 if(result)return result;
 result=fn(keychain,length,name,accountLength,account,passwordLength,passwordData,item);
 fprintf(stderr,"PRIVATE_KEYSTORE_STATUS generic-add status=%d\n",(int)result);
 free(name);return result;
}
/* CalendarStore uses dictionary APIs and legacy Internet-password searches. */
static CFStringRef namespacedString(CFStringRef value){
 if(value&&CFGetTypeID(value)!=CFStringGetTypeID())return NULL;
 return CFStringCreateWithFormat(NULL,NULL,CFSTR("org.local.RestoredApps/%@"),value?value:CFSTR(""));
}
static Boolean ownsItem(SecKeychainItemRef item){
 typedef OSStatus(*Copy)(SecKeychainItemRef,SecKeychainAttributeInfo *,SecItemClass *,SecKeychainAttributeList **,UInt32 *,void **);
 typedef OSStatus(*Free)(SecKeychainAttributeList *,void *);
 Copy copy=(Copy)original("SecKeychainItemCopyAttributesAndData");Free release=(Free)original("SecKeychainItemFreeAttributesAndData");
 if(!item||!copy||!release)return false;
 SecItemClass cls=0;SecKeychainAttributeList *attrs=NULL;
 /* NULL info requests no attributes. First obtain class, then request
  * exactly the namespace attribute. Password outputs remain NULL. */
 if(copy(item,NULL,&cls,NULL,NULL,NULL)!=errSecSuccess)return false;
 UInt32 tag;
 if(cls==kSecGenericPasswordItemClass)tag=kSecServiceItemAttr;
 else if(cls==kSecInternetPasswordItemClass)tag=kSecSecurityDomainItemAttr;
 else return false;
 UInt32 format=CSSM_DB_ATTRIBUTE_FORMAT_STRING;
 SecKeychainAttributeInfo info={1,&tag,&format};
 if(copy(item,&info,NULL,&attrs,NULL,NULL)!=errSecSuccess)return false;
 Boolean owned=false;static const char prefix[]="org.local.RestoredApps/";
 if(attrs)for(UInt32 i=0;i<attrs->count;i++){
  SecKeychainAttribute a=attrs->attr[i];
  Boolean right=(cls==kSecGenericPasswordItemClass&&a.tag==kSecServiceItemAttr)||(cls==kSecInternetPasswordItemClass&&a.tag==kSecSecurityDomainItemAttr);
  if(right&&a.length>=sizeof(prefix)-1&&!memcmp(a.data,prefix,sizeof(prefix)-1))owned=true;
 }
 if(attrs)release(attrs,NULL);return owned;
}
static CFMutableDictionaryRef privateQuery(CFDictionaryRef input,Boolean attributesOnly,Boolean adding){
 if(!input||CFGetTypeID(input)!=CFDictionaryGetTypeID())return NULL;
 CFMutableDictionaryRef q=CFDictionaryCreateMutableCopy(NULL,0,input);if(!q)return NULL;
 CFTypeRef ref=CFDictionaryGetValue(q,kSecValueRef);
 if(ref&&!ownsItem((SecKeychainItemRef)ref))goto reject;
 CFTypeRef persistent=CFDictionaryGetValue(q,kSecValuePersistentRef);
 if(persistent){
  typedef OSStatus(*Fn)(CFDataRef,SecKeychainItemRef *);Fn fn=(Fn)original("SecKeychainItemCopyFromPersistentReference");
  SecKeychainItemRef item=NULL;
  if(CFGetTypeID(persistent)!=CFDataGetTypeID()||!fn||fn((CFDataRef)persistent,&item)!=errSecSuccess)goto reject;
  Boolean owned=ownsItem(item);if(item)CFRelease(item);if(!owned)goto reject;
 }
 CFTypeRef list=CFDictionaryGetValue(q,kSecMatchItemList);
 if(list){
  if(CFGetTypeID(list)!=CFArrayGetTypeID()||!CFArrayGetCount((CFArrayRef)list))goto reject;
  for(CFIndex i=0;i<CFArrayGetCount((CFArrayRef)list);i++)if(!ownsItem((SecKeychainItemRef)CFArrayGetValueAtIndex((CFArrayRef)list,i)))goto reject;
 }
 CFTypeRef cls=CFDictionaryGetValue(q,kSecClass);CFStringRef key=NULL;
 if(cls&&CFEqual(cls,kSecClassGenericPassword))key=kSecAttrService;
 else if(cls&&CFEqual(cls,kSecClassInternetPassword))key=kSecAttrSecurityDomain;
 else if(!attributesOnly){if(ref||persistent||list)return q;goto reject;}
 if(attributesOnly){
  if(CFDictionaryContainsKey(q,kSecAttrService)&&CFDictionaryContainsKey(q,kSecAttrSecurityDomain))goto reject;
  if(CFDictionaryContainsKey(q,kSecAttrService))key=kSecAttrService;
  if(CFDictionaryContainsKey(q,kSecAttrSecurityDomain))key=kSecAttrSecurityDomain;
 }
 if(key){
  CFStringRef old=(CFStringRef)CFDictionaryGetValue(q,key);CFStringRef value=namespacedString(old);
  if(!value)goto reject;
  CFDictionarySetValue(q,key,value);CFRelease(value);
 }
 /* Keep private credentials in the desktop Keychain, without Apple-only
  * access groups or the synchronizable/iOS-style keychain path. */
 CFDictionaryRemoveValue(q,kSecAttrAccessGroup);
 CFDictionaryRemoveValue(q,kSecAttrSynchronizable);
 if(!attributesOnly&&!CFDictionaryContainsKey(q,kSecUseKeychain)&&!CFDictionaryContainsKey(q,kSecMatchSearchList)){
  typedef OSStatus(*Default)(SecPreferencesDomain,SecKeychainRef *);
  Default getDefault=(Default)original("SecKeychainCopyDomainDefault");SecKeychainRef keychain=NULL;
  OSStatus defaultStatus=getDefault?getDefault(kSecPreferencesDomainUser,&keychain):errSecUnimplemented;
  fprintf(stderr,"PRIVATE_KEYSTORE_STATUS domain-default status=%d available=%d\n",(int)defaultStatus,keychain!=NULL);
  if(defaultStatus!=errSecSuccess||!keychain){
   if(keychain){CFRelease(keychain);keychain=NULL;}
   typedef OSStatus(*Fallback)(SecKeychainRef *);
   Fallback fallback=(Fallback)original("SecKeychainCopyDefault");
   defaultStatus=fallback?fallback(&keychain):errSecUnimplemented;
   fprintf(stderr,"PRIVATE_KEYSTORE_STATUS default-keychain status=%d available=%d\n",(int)defaultStatus,keychain!=NULL);
   if(defaultStatus!=errSecSuccess||!keychain){
    if(keychain){CFRelease(keychain);keychain=NULL;}
    /* Open the existing login keychain without changing the default or
     * search list. All item queries still require the private namespace. */
    typedef OSStatus(*Open)(const char *,SecKeychainRef *);
    Open openKeychain=(Open)original("SecKeychainOpen");
    struct passwd *user=getpwuid(getuid());char path[PATH_MAX];
    if(!user||!user->pw_dir||snprintf(path,sizeof(path),"%s/Library/Keychains/login.keychain",user->pw_dir)>=(int)sizeof(path))goto reject;
    defaultStatus=openKeychain?openKeychain(path,&keychain):errSecUnimplemented;
    fprintf(stderr,"PRIVATE_KEYSTORE_STATUS login-open status=%d available=%d\n",(int)defaultStatus,keychain!=NULL);
    if(defaultStatus!=errSecSuccess||!keychain){if(keychain)CFRelease(keychain);goto reject;}
   }
  }
  if(adding)CFDictionarySetValue(q,kSecUseKeychain,keychain);
  else {CFArrayRef list=CFArrayCreate(NULL,(const void **)&keychain,1,&kCFTypeArrayCallBacks);CFDictionarySetValue(q,kSecMatchSearchList,list);CFRelease(list);}
  CFRelease(keychain);
 }
 return q;
reject:CFRelease(q);return NULL;
}
OSStatus SecItemAdd(CFDictionaryRef attributes,CFTypeRef *result){
 typedef OSStatus(*Fn)(CFDictionaryRef,CFTypeRef *);Fn fn=(Fn)original("SecItemAdd");
 CFMutableDictionaryRef q=privateQuery(attributes,false,true);if(!q){fprintf(stderr,"PRIVATE_KEYSTORE_STATUS item-add query-rejected\n");return errSecParam;}
 OSStatus status=fn?fn(q,result):errSecUnimplemented;fprintf(stderr,"PRIVATE_KEYSTORE_STATUS item-add status=%d\n",(int)status);CFRelease(q);return status;
}
OSStatus SecItemCopyMatching(CFDictionaryRef query,CFTypeRef *result){
 typedef OSStatus(*Fn)(CFDictionaryRef,CFTypeRef *);Fn fn=(Fn)original("SecItemCopyMatching");
 CFMutableDictionaryRef q=privateQuery(query,false,false);if(!q){fprintf(stderr,"PRIVATE_KEYSTORE_STATUS item-find query-rejected\n");return errSecParam;}
 OSStatus status=fn?fn(q,result):errSecUnimplemented;fprintf(stderr,"PRIVATE_KEYSTORE_STATUS item-find status=%d\n",(int)status);CFRelease(q);return status;
}
OSStatus SecItemDelete(CFDictionaryRef query){
 typedef OSStatus(*Fn)(CFDictionaryRef);Fn fn=(Fn)original("SecItemDelete");
 CFMutableDictionaryRef q=privateQuery(query,false,false);if(!q){fprintf(stderr,"PRIVATE_KEYSTORE_STATUS item-delete query-rejected\n");return errSecParam;}
 OSStatus status=fn?fn(q):errSecUnimplemented;fprintf(stderr,"PRIVATE_KEYSTORE_STATUS item-delete status=%d\n",(int)status);CFRelease(q);return status;
}
OSStatus SecItemUpdate(CFDictionaryRef query,CFDictionaryRef attributes){
 typedef OSStatus(*Fn)(CFDictionaryRef,CFDictionaryRef);Fn fn=(Fn)original("SecItemUpdate");
 CFMutableDictionaryRef q=privateQuery(query,false,false),a=privateQuery(attributes,true,false);
 if(!q||!a){if(q)CFRelease(q);if(a)CFRelease(a);return errSecParam;}
 OSStatus status=fn?fn(q,a):errSecUnimplemented;fprintf(stderr,"PRIVATE_KEYSTORE_STATUS item-update status=%d\n",(int)status);CFRelease(q);CFRelease(a);return status;
}
OSStatus SecKeychainFindInternetPassword(CFTypeRef keychain,UInt32 serverLength,const char *server,UInt32 domainLength,const char *domain,UInt32 accountLength,const char *account,UInt32 pathLength,const char *path,UInt16 port,SecProtocolType protocol,SecAuthenticationType authentication,UInt32 *passwordLength,void **passwordData,SecKeychainItemRef *item){
 typedef OSStatus(*Fn)(CFTypeRef,UInt32,const char *,UInt32,const char *,UInt32,const char *,UInt32,const char *,UInt16,SecProtocolType,SecAuthenticationType,UInt32 *,void **,SecKeychainItemRef *);
 Fn fn=(Fn)original("SecKeychainFindInternetPassword");if(!fn)return errSecUnimplemented;
 char *name=NULL;UInt32 length=0;OSStatus status=privateService(domainLength,domain,&name,&length);if(status)return status;
 status=fn(keychain,serverLength,server,length,name,accountLength,account,pathLength,path,port,protocol,authentication,passwordLength,passwordData,item);
 fprintf(stderr,"PRIVATE_KEYSTORE_STATUS internet-find status=%d\n",(int)status);
 free(name);return status;
}
OSStatus SecKeychainItemCopyFromPersistentReference(CFDataRef reference,SecKeychainItemRef *item){
 typedef OSStatus(*Fn)(CFDataRef,SecKeychainItemRef *);Fn fn=(Fn)original("SecKeychainItemCopyFromPersistentReference");
 if(!item||!fn)return errSecParam;*item=NULL;OSStatus status=fn(reference,item);
 if(status==errSecSuccess&&!ownsItem(*item)){if(*item)CFRelease(*item);*item=NULL;fputs("PRIVATE_KEYSTORE_STATUS reference-resolve namespace-rejected\n",stderr);return errSecItemNotFound;}fprintf(stderr,"PRIVATE_KEYSTORE_STATUS reference-resolve status=%d\n",(int)status);return status;
}
OSStatus SecKeychainItemDelete(SecKeychainItemRef item){
 typedef OSStatus(*Fn)(SecKeychainItemRef);Fn fn=(Fn)original("SecKeychainItemDelete");
 if(!ownsItem(item))return errSecItemNotFound;return fn?fn(item):errSecUnimplemented;
}
OSStatus SecKeychainItemModifyContent(SecKeychainItemRef item,const SecKeychainAttributeList *attrs,UInt32 length,const void *data){
 typedef OSStatus(*Fn)(SecKeychainItemRef,const SecKeychainAttributeList *,UInt32,const void *);Fn fn=(Fn)original("SecKeychainItemModifyContent");
 /* Prevent callers from removing/changing namespace-bearing attributes. */
 if(!ownsItem(item))return errSecItemNotFound;
 if(attrs)for(UInt32 i=0;i<attrs->count;i++)if(attrs->attr[i].tag==kSecServiceItemAttr||attrs->attr[i].tag==kSecSecurityDomainItemAttr)return errSecParam;
 return fn?fn(item,attrs,length,data):errSecUnimplemented;
}
OSStatus SecKeychainItemCopyContent(SecKeychainItemRef item,SecItemClass *cls,SecKeychainAttributeList *attrs,UInt32 *length,void **data){
 typedef OSStatus(*Fn)(SecKeychainItemRef,SecItemClass *,SecKeychainAttributeList *,UInt32 *,void **);Fn fn=(Fn)original("SecKeychainItemCopyContent");
 if(!ownsItem(item)){fputs("PRIVATE_KEYSTORE_STATUS reference-read namespace-rejected\n",stderr);return errSecItemNotFound;}
 OSStatus status=fn?fn(item,cls,attrs,length,data):errSecUnimplemented;
 fprintf(stderr,"PRIVATE_KEYSTORE_STATUS reference-read status=%d\n",(int)status);return status;
}
OSStatus SecKeychainItemModifyAttributesAndData(SecKeychainItemRef item,const SecKeychainAttributeList *attrs,UInt32 length,const void *data){
 typedef OSStatus(*Fn)(SecKeychainItemRef,const SecKeychainAttributeList *,UInt32,const void *);Fn fn=(Fn)original("SecKeychainItemModifyAttributesAndData");
 if(!ownsItem(item))return errSecItemNotFound;
 if(attrs)for(UInt32 i=0;i<attrs->count;i++)if(attrs->attr[i].tag==kSecServiceItemAttr||attrs->attr[i].tag==kSecSecurityDomainItemAttr)return errSecParam;
 return fn?fn(item,attrs,length,data):errSecUnimplemented;
}
OSStatus SecKeychainItemSetAccess(SecKeychainItemRef item,SecAccessRef access){
 typedef OSStatus(*Fn)(SecKeychainItemRef,SecAccessRef);Fn fn=(Fn)original("SecKeychainItemSetAccess");
 if(!ownsItem(item))return errSecItemNotFound;return fn?fn(item,access):errSecUnimplemented;
}
OSStatus SecKeychainItemCopyAccess(SecKeychainItemRef item,SecAccessRef *access){
 typedef OSStatus(*Fn)(SecKeychainItemRef,SecAccessRef *);Fn fn=(Fn)original("SecKeychainItemCopyAccess");
 if(!ownsItem(item))return errSecItemNotFound;return fn?fn(item,access):errSecUnimplemented;
}
OSStatus SecKeychainItemCreatePersistentReference(SecKeychainItemRef item,CFDataRef *reference){
 typedef OSStatus(*Fn)(SecKeychainItemRef,CFDataRef *);Fn fn=(Fn)original("SecKeychainItemCreatePersistentReference");
 if(!ownsItem(item))return errSecItemNotFound;return fn?fn(item,reference):errSecUnimplemented;
}
