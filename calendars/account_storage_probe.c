#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <mach-o/dyld.h>
/* Only reads the library's computed storage URL. Does not enumerate accounts. */
int main(int argc,char **argv){
 if(argc!=3){puts("Expected private framework and expected private path.");return 1;}
 void *h=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
 if(!h){printf("LOAD_FAILED %s\n",dlerror());return 1;}
 CFURLRef (*copyURL)(void)=(CFURLRef(*)(void))dlsym(h,"_CSInternetAccountCopyBaseURL");
 if(!copyURL){puts("STORAGE_SYMBOL_MISSING");return 1;}
 CFURLRef url=copyURL();
 if(!url){puts("STORAGE_URL_MISSING");return 1;}
 CFURLRef absolute=CFURLCopyAbsoluteURL(url);
 CFStringRef path=absolute?CFURLCopyFileSystemPath(absolute,kCFURLPOSIXPathStyle):NULL;
 char text[4096];int ok=path&&CFStringGetCString(path,text,sizeof(text),kCFStringEncodingUTF8);
 if(path)CFRelease(path);if(absolute)CFRelease(absolute);CFRelease(url);
 if(!ok){puts("STORAGE_PATH_ENCODING_FAILED");return 1;}
 printf("ACCOUNT_STORAGE_PATH=%s\n",text);
 if(strcmp(text,argv[2])){puts("PRIVATE_STORAGE_PATH_MISMATCH");return 2;}
 puts("PRIVATE_STORAGE_PATH_MATCH");
 int mixed=0;
 for(uint32_t i=0;i<_dyld_image_count();i++){
  const char *p=_dyld_get_image_name(i);
  if(!strncmp(p,"/System/Library/",16)&&(strstr(p,"/InternetAccounts.framework/")||strstr(p,"/AOSKit.framework/")||strstr(p,"/ISSupport.framework/")))mixed++;
 }
 printf("SYSTEM_ACCOUNT_STACK_IMAGES=%d\n",mixed);
 puts("No account enumeration, creation, password access, or networking requested.");
 return mixed?2:0;
}
