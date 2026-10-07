#import <Foundation/Foundation.h>
#import <objc/message.h>
#import <objc/runtime.h>
#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <string.h>
static NSURL *fixtureLibrary;
static id isolatedLibrary(id self,SEL cmd){(void)self;(void)cmd;return fixtureLibrary;}
int main(int argc,char **argv){@autoreleasepool{
 if(argc!=6)return 1;
 void *backend=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
 if(!backend){printf("BACKEND_LOAD_FAILED %s\n",dlerror());return 1;}
 void *routing=dlopen(argv[2],RTLD_NOW|RTLD_LOCAL);
 if(!routing){printf("ROUTING_LOAD_FAILED %s\n",dlerror());return 1;}
 int(*install)(const char *)=(int(*)(const char *))dlsym(routing,"MLInstallPrivateAccountPluginRouting");
 int status=install?install(argv[3]):9;
 printf("ROUTING_INSTALL_STATUS=%d\n",status);if(status)return status;
 @try{
  id manager=((id(*)(id,SEL))objc_msgSend)(NSClassFromString(@"IAPluginManager"),NSSelectorFromString(@"shared"));
  void *notes=dlopen(argv[4],RTLD_NOW|RTLD_LOCAL);
  if(!notes){printf("NOTES_LOAD_FAILED %s\n",dlerror());return 5;}
  puts("NOTES_FRAMEWORK_LOADED");
  fixtureLibrary=[[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[5]] isDirectory:YES] retain];
  Class persistence=NSClassFromString(@"NFPersistenceManager");
  Method library=class_getClassMethod(persistence,NSSelectorFromString(@"libraryURL"));
  char *returnType=library?method_copyReturnType(library):NULL;
  BOOL valid=library&&returnType&&returnType[0]=='@'&&method_getNumberOfArguments(library)==2;
  free(returnType);if(!valid){puts("NOTES_STORAGE_METHOD_MISMATCH");return 6;}
  method_setImplementation(library,(IMP)isolatedLibrary);
  puts("NOTES_FIXTURE_STORAGE_ROUTED");fflush(stdout);
  const char *ids[]={"com.apple.google.iaplugin","com.apple.mail.iaplugin","com.apple.Notes.iaplugin"};
  for(int i=0;i<3;i++){
   id plugin=((id(*)(id,SEL,id))objc_msgSend)(manager,NSSelectorFromString(@"pluginWithIdentifier:"),[NSString stringWithUTF8String:ids[i]]);
   printf("PLUGIN %s %s\n",ids[i],plugin?"FOUND":"MISSING");fflush(stdout);if(!plugin)status=2;
  }
  id coordinator=((id(*)(id,SEL))objc_msgSend)(persistence,NSSelectorFromString(@"persistentStoreCoordinator"));
  NSArray *stores=((id(*)(id,SEL))objc_msgSend)(coordinator,NSSelectorFromString(@"persistentStores"));
  NSString *prefix=[[fixtureLibrary path] stringByAppendingString:@"/"];
  if(![stores count]){puts("NOTES_FIXTURE_STORE_MISSING");status=7;}
  for(id store in stores){
   NSURL *url=((id(*)(id,SEL))objc_msgSend)(store,NSSelectorFromString(@"URL"));
   BOOL isolated=[[url path] hasPrefix:prefix];
   printf("NOTES_STORE_ISOLATED=%d\n",isolated?1:0);if(!isolated)status=8;
  }
 }@catch(NSException *e){printf("PLUGIN_EXCEPTION %s\n",[[e name] UTF8String]);status=3;}
 int mixed=0;
 for(uint32_t i=0;i<_dyld_image_count();i++){
  const char *p=_dyld_get_image_name(i);printf("PLUGIN_IMAGE %s\n",p);
  if(!strncmp(p,"/System/Library/InternetAccounts/",32))mixed++;
  if(!strncmp(p,"/System/Library/",16)&&(strstr(p,"/InternetAccounts.framework/")||strstr(p,"/AOSKit.framework/")||strstr(p,"/ISSupport.framework/")||strstr(p,"/CalendarStore.framework/")||strstr(p,"/CalendarPersistence.framework/")||strstr(p,"/AddressBook.framework/")))mixed++;
 }
 printf("SYSTEM_ACCOUNT_OR_PLUGIN_IMAGES=%d\n",mixed);
 puts("No sign-in, account creation, sync, or password operation requested.");
 return mixed?4:status;
}}
