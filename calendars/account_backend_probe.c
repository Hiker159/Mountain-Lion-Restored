#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <mach-o/dyld.h>
int main(int argc,char **argv){
 int failed=0;
 puts("Private account backend load probe. No account API or calendar application is invoked.");
 for(int i=1;i<argc;i++){
  printf("LOAD %s\n",argv[i]);fflush(stdout);
  void *handle=dlopen(argv[i],RTLD_NOW|RTLD_LOCAL);
  if(!handle){printf("LOAD_FAILED %s\n",dlerror());failed=1;}
  else puts("LOAD_OK");
 }
 int mixed=0,accountMixed=0;
 for(uint32_t i=0;i<_dyld_image_count();i++){
  const char *path=_dyld_get_image_name(i);
  if(strstr(path,"/System/Library/PrivateFrameworks/CalendarPersistence.framework")||strstr(path,"/System/Library/Frameworks/CalendarStore.framework"))mixed++;
  if(strncmp(path,"/System/Library/",16)==0 && (strstr(path,"/InternetAccounts.framework/")||strstr(path,"/AOSKit.framework/")||strstr(path,"/ISSupport.framework/")))accountMixed++;
  printf("IMAGE %s\n",path);
 }
 printf("SYSTEM_CALENDAR_STACK_IMAGES=%d\n",mixed);
 printf("SYSTEM_ACCOUNT_STACK_IMAGES=%d\n",accountMixed);puts("BACKEND_LOAD_PROBE_COMPLETE");return failed?1:((mixed||accountMixed)?2:0);
}
