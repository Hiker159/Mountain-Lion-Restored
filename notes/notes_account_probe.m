#import <Foundation/Foundation.h>
#import <objc/message.h>
#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv){@autoreleasepool{
 if(argc!=5)return 1;
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
  const char *ids[]={"com.apple.google.iaplugin","com.apple.mail.iaplugin","com.apple.Notes.iaplugin"};
  for(int i=0;i<3;i++){
   id plugin=((id(*)(id,SEL,id))objc_msgSend)(manager,NSSelectorFromString(@"pluginWithIdentifier:"),[NSString stringWithUTF8String:ids[i]]);
   printf("PLUGIN %s %s\n",ids[i],plugin?"FOUND":"MISSING");if(!plugin)status=2;
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
