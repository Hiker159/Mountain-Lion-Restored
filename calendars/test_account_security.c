/* In-memory Security provider: tests never call native Keychain functions. */
#define ML_ACCOUNT_SECURITY_TEST 1
#include "account_security_compat.c"
#include <assert.h>
static int calls;
static CFDictionaryRef last;
static OSStatus dictionaryCall(CFDictionaryRef q,CFTypeRef *out){
 (void)out;calls++;if(last)CFRelease(last);last=CFDictionaryCreateCopy(NULL,q);return 43;
}
static OSStatus deleteCall(CFDictionaryRef q){return dictionaryCall(q,NULL);}
static OSStatus updateCall(CFDictionaryRef q,CFDictionaryRef attrs){
 assert(CFEqual(CFDictionaryGetValue(attrs,kSecValueData),CFSTR("synthetic-test")));return dictionaryCall(q,NULL);
}
static OSStatus copyAttrs(SecKeychainItemRef ref,SecKeychainAttributeInfo *info,SecItemClass *cls,SecKeychainAttributeList **out,UInt32 *length,void **data){
 assert(!length&&!data);
 if(!info){assert(cls&&!out);*cls=kSecGenericPasswordItemClass;return 0;}
 assert(!cls&&out&&info->count==1&&info->tag[0]==kSecServiceItemAttr&&info->format[0]==CSSM_DB_ATTRIBUTE_FORMAT_STRING);
 const char *s=CFEqual((CFTypeRef)ref,CFSTR("private-item"))?"org.local.RestoredApps/calendar.google.com":"calendar.google.com";
 *out=calloc(1,sizeof(**out));(*out)->count=1;(*out)->attr=calloc(1,sizeof(SecKeychainAttribute));
 (*out)->attr[0]=(SecKeychainAttribute){kSecServiceItemAttr,(UInt32)strlen(s),strdup(s)};return 0;
}
static OSStatus freeAttrs(SecKeychainAttributeList *attrs,void *data){
 assert(!data);free(attrs->attr[0].data);free(attrs->attr);free(attrs);return 0;
}
static OSStatus itemCall(SecKeychainItemRef ref){assert(CFEqual((CFTypeRef)ref,CFSTR("private-item")));calls++;return 43;}
static Boolean failDomain,failFallback,failOpen;
static OSStatus fakeFallback(SecKeychainRef *keychain){if(failFallback){*keychain=NULL;return errSecNoDefaultKeychain;}*keychain=(SecKeychainRef)CFRetain(CFSTR("fallback-keychain"));return 0;}
static OSStatus fakeDefault(SecPreferencesDomain domain,SecKeychainRef *keychain){
 assert(domain==kSecPreferencesDomainUser);if(failDomain){*keychain=NULL;return errSecNoDefaultKeychain;}*keychain=(SecKeychainRef)CFRetain(CFSTR("fake-keychain"));return 0;
}
static OSStatus fakeOpen(const char *path,SecKeychainRef *keychain){
 assert(strstr(path,"/Library/Keychains/login.keychain"));
 if(failOpen){*keychain=NULL;return errSecNoSuchKeychain;}
 *keychain=(SecKeychainRef)CFRetain(CFSTR("login-test-keychain"));return 0;
}
void *MLTestSecurityFunction(const char *name){
 if(!strcmp(name,"SecKeychainOpen"))return fakeOpen;
 if(!strcmp(name,"SecKeychainCopyDefault"))return fakeFallback;
 if(!strcmp(name,"SecKeychainCopyDomainDefault"))return fakeDefault;
 if(!strcmp(name,"SecItemAdd")||!strcmp(name,"SecItemCopyMatching"))return dictionaryCall;
 if(!strcmp(name,"SecItemDelete"))return deleteCall;
 if(!strcmp(name,"SecItemUpdate"))return updateCall;
 if(!strcmp(name,"SecKeychainItemCopyAttributesAndData"))return copyAttrs;
 if(!strcmp(name,"SecKeychainItemFreeAttributesAndData"))return freeAttrs;
 if(!strcmp(name,"SecKeychainItemDelete"))return itemCall;
 return NULL;
}
int main(void){
 CFMutableDictionaryRef q=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
 CFDictionarySetValue(q,kSecClass,kSecClassInternetPassword);
 CFDictionarySetValue(q,kSecAttrServer,CFSTR("calendar.google.com"));
 CFDictionarySetValue(q,kSecAttrAccount,CFSTR("same-user"));
 CFDictionarySetValue(q,kSecAttrSecurityDomain,CFSTR("Google APIs"));
 CFDictionarySetValue(q,kSecValueData,CFSTR("synthetic-test"));
 CFDictionarySetValue(q,kSecAttrSynchronizable,kCFBooleanTrue);
 CFDictionarySetValue(q,kSecAttrAccessGroup,CFSTR("apple-only-test-group"));
 assert(SecItemAdd(q,NULL)==43);
 assert(!CFDictionaryContainsKey(last,kSecAttrSynchronizable)&&!CFDictionaryContainsKey(last,kSecAttrAccessGroup));
 assert(CFDictionaryContainsKey(last,kSecUseKeychain));
 assert(CFEqual(CFDictionaryGetValue(last,kSecAttrSecurityDomain),CFSTR("org.local.RestoredApps/Google APIs")));
 assert(CFEqual(CFDictionaryGetValue(last,kSecAttrServer),CFSTR("calendar.google.com")));
 assert(CFEqual(CFDictionaryGetValue(last,kSecAttrAccount),CFSTR("same-user")));
 assert(CFEqual(CFDictionaryGetValue(last,kSecValueData),CFSTR("synthetic-test")));
 assert(CFEqual(CFDictionaryGetValue(q,kSecAttrSecurityDomain),CFSTR("Google APIs")));
 assert(SecItemCopyMatching(q,NULL)==43);assert(CFDictionaryContainsKey(last,kSecMatchSearchList));assert(SecItemDelete(q)==43);
 CFMutableDictionaryRef attrs=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
 CFDictionarySetValue(attrs,kSecValueData,CFSTR("synthetic-test"));assert(SecItemUpdate(q,attrs)==43);
 CFDictionarySetValue(q,kSecClass,kSecClassGenericPassword);CFDictionaryRemoveValue(q,kSecAttrSecurityDomain);
 CFDictionarySetValue(q,kSecAttrService,CFSTR("Google"));assert(SecItemCopyMatching(q,NULL)==43);
 assert(CFEqual(CFDictionaryGetValue(last,kSecAttrService),CFSTR("org.local.RestoredApps/Google")));
 failDomain=true;assert(SecItemAdd(q,NULL)==43);
 assert(CFEqual(CFDictionaryGetValue(last,kSecUseKeychain),CFSTR("fallback-keychain")));
 assert(SecItemCopyMatching(q,NULL)==43);
 assert(CFEqual(CFArrayGetValueAtIndex(CFDictionaryGetValue(last,kSecMatchSearchList),0),CFSTR("fallback-keychain")));
 failFallback=true;assert(SecItemAdd(q,NULL)==43);
 assert(CFEqual(CFDictionaryGetValue(last,kSecUseKeychain),CFSTR("login-test-keychain")));
 failOpen=true;int rejectedCalls=calls;assert(SecItemAdd(q,NULL)==errSecParam);assert(calls==rejectedCalls);
 failDomain=false;failFallback=false;failOpen=false;
 int before=calls;assert(SecKeychainItemDelete((SecKeychainItemRef)CFSTR("stock-item"))==errSecItemNotFound);assert(calls==before);
 assert(SecKeychainItemDelete((SecKeychainItemRef)CFSTR("private-item"))==43);
 CFDictionaryRemoveAllValues(q);before=calls;assert(SecItemDelete(q)==errSecParam);assert(calls==before);
 CFDictionarySetValue(q,kSecClass,kSecClassCertificate);assert(SecItemCopyMatching(q,NULL)==errSecParam);
 CFDictionarySetValue(q,kSecClass,kSecClassGenericPassword);CFDictionarySetValue(q,kSecAttrService,kCFBooleanTrue);assert(SecItemAdd(q,NULL)==errSecParam);
 char *name=NULL;UInt32 size=0;assert(privateService(UINT32_MAX,"x",&name,&size)==errSecParam);
 CFRelease(q);CFRelease(attrs);CFRelease(last);
 puts("PASS: Internet and generic namespaces; CRUD routing; caller input preservation; foreign-reference rejection; malformed-query rejection. Native Keychain untouched.");return 0;
}
