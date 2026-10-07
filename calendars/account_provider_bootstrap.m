#import "account_provider_plugin_routing.m"
#import <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <unistd.h>
#include <execinfo.h>
static void accountTrace(void){
 void *frames[24];int count=backtrace(frames,24);char **symbols=backtrace_symbols(frames,count);
 if(symbols){for(int i=0;i<count;i++)fprintf(stderr,"PRIVATE_ACCOUNT_LOAD_STACK %s\n",symbols[i]);free(symbols);}
}
static char privateFrameworkRoot[4096];
static void *(*nativeDlopen)(const char *,int);
static void *privateDlopen(const char *name,int mode){
 if(!nativeDlopen){
  nativeDlopen=dlopen;
  if(!nativeDlopen||nativeDlopen==privateDlopen){fputs("PRIVATE_ACCOUNT_DLOPEN_RESOLUTION_FAILED\n",stderr);_exit(78);}
 }
 if(name&&privateFrameworkRoot[0]&&!strncmp(name,"/System/Library/",16)){
  fprintf(stderr,"PRIVATE_ACCOUNT_DYNAMIC_REQUEST %s\n",name);
  const char *names[]={"AOSKit","AOSAccounts","InternetAccounts","AddressBook","CalDAV","CoreDAV","DataDetectors","ExchangeWebServices"};
  for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++){
   char match[128];snprintf(match,sizeof(match),"/%s.framework/",names[i]);
   const char *last=strrchr(name,'/');
   if(strstr(name,match)&&last&&!strcmp(last+1,names[i])){
    char path[4096];int n=snprintf(path,sizeof(path),"%s/%s.framework/Versions/A/%s",privateFrameworkRoot,names[i],names[i]);
    if(n<0||n>=(int)sizeof(path))return NULL;
    fprintf(stderr,"PRIVATE_ACCOUNT_DYNAMIC_REDIRECT %s\n",names[i]);
    return nativeDlopen(path,mode);
   }
  }
 }
 return nativeDlopen(name,mode);
}
__attribute__((used)) static struct {const void *replacement;const void *replacee;} accountInterpose
 __attribute__((section("__DATA,__interpose")))={(const void *)privateDlopen,(const void *)dlopen};
static int prohibited(const char *path){
 if(!strncmp(path,"/System/Library/InternetAccounts/",32))return 1;
 if(strncmp(path,"/System/Library/",16))return 0;
 const char *names[]={"/InternetAccounts.framework/","/AOSKit.framework/","/ISSupport.framework/","/AddressBook.framework/","/CalendarStore.framework/","/CalendarPersistence.framework/","/CalDAV.framework/","/CoreDAV.framework/","/ExchangeWebServices.framework/"};
 for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++)if(strstr(path,names[i]))return 1;
 return 0;
}
static void imageAdded(const struct mach_header *header,intptr_t slide){
 (void)slide;
 for(uint32_t i=0;i<_dyld_image_count();i++)if(_dyld_get_image_header(i)==header){
  const char *path=_dyld_get_image_name(i);
  if(prohibited(path)){fprintf(stderr,"PRIVATE_ACCOUNT_SYSTEM_IMAGE_BLOCKED %s\n",path);accountTrace();fflush(stderr);_exit(78);}
  if(strstr(path,".iaplugin/")||strstr(path,"InternetAccounts.framework/")||strstr(path,"MLAccountSecurity"))fprintf(stderr,"PRIVATE_ACCOUNT_IMAGE %s\n",path);
  break;
 }
}
__attribute__((constructor)) static void bootstrap(void){
 write(2,"PRIVATE_ACCOUNT_BOOTSTRAP_ENTER\n",32);
 @autoreleasepool{
 Dl_info info;if(!dladdr((void *)bootstrap,&info)){_exit(78);}
 NSString *frameworks=[[NSString stringWithUTF8String:info.dli_fname] stringByDeletingLastPathComponent];
 NSString *contents=[frameworks stringByDeletingLastPathComponent];
 if(![frameworks getFileSystemRepresentation:privateFrameworkRoot maxLength:sizeof(privateFrameworkRoot)])_exit(78);
 NSString *sources=[contents stringByAppendingPathComponent:@"PlugIns/ContactSources"];
 setenv("ML_CONTACTS_PLUGINS",[sources fileSystemRepresentation],1);
 NSString *ia=[frameworks stringByAppendingPathComponent:@"InternetAccounts.framework/Versions/A/InternetAccounts"];
 void *handle=dlopen([ia fileSystemRepresentation],RTLD_NOW|RTLD_LOCAL);
 if(!handle){fprintf(stderr,"PRIVATE_ACCOUNT_BOOTSTRAP_LOAD_FAILED %s\n",dlerror());_exit(78);}
 _dyld_register_func_for_add_image(imageAdded);
 int result=MLInstallPrivateAccountPluginRouting([[contents stringByAppendingPathComponent:@"AccountPlugins"] fileSystemRepresentation]);
 if(result){fprintf(stderr,"PRIVATE_ACCOUNT_ROUTING_FAILED %d\n",result);_exit(78);}
 CFURLRef(*copyURL)(void)=(CFURLRef(*)(void))dlsym(handle,"_CSInternetAccountCopyBaseURL");
 CFURLRef url=copyURL?copyURL():NULL,abs=url?CFURLCopyAbsoluteURL(url):NULL;
 CFStringRef path=abs?CFURLCopyFileSystemPath(abs,kCFURLPOSIXPathStyle):NULL;
 NSString *expected=[NSHomeDirectory() stringByAppendingPathComponent:@"Library/ML Cloud Accounts/V1"];
 BOOL valid=path&&[(NSString *)path isEqualToString:expected];
 if(path)CFRelease(path);if(abs)CFRelease(abs);if(url)CFRelease(url);
 if(!valid){fputs("PRIVATE_ACCOUNT_STORAGE_MISMATCH\n",stderr);_exit(78);}
 fputs("PRIVATE_ACCOUNT_BOOTSTRAP_READY\n",stderr);fflush(stderr);
}}
