#import "account_provider_bootstrap.m"
#import <dispatch/dispatch.h>
#include <string.h>
static dispatch_source_t accountPollTimer;
static BOOL methodType(Method method,char type){
 if(!method||method_getNumberOfArguments(method)!=2)return NO;
 char *r=method_copyReturnType(method);BOOL valid=r&&r[0]==type;free(r);return valid;
}
static void pollPrivateAccounts(void){
 @autoreleasepool{
  @try{
   Class cls=NSClassFromString(@"CalAgentRefreshManager");
   const char *path=cls?class_getImageName(cls):NULL;
   if(!path||!strstr(path,"/Mountain Lion Calendar.app/Contents/")||!strstr(path,"/CalendarAgent.framework/")){
    fputs("PRIVATE_ACCOUNT_POLL unavailable_private_manager\n",stderr);return;
   }
   SEL get=NSSelectorFromString(@"defaultManager"),refresh=NSSelectorFromString(@"refreshAllAccounts");
   if(!methodType(class_getClassMethod(cls,get),'@')||!methodType(class_getInstanceMethod(cls,refresh),'v')){
    fputs("PRIVATE_ACCOUNT_POLL unavailable_method_signature\n",stderr);return;
   }
   id manager=((id(*)(id,SEL))[cls methodForSelector:get])(cls,get);
   if(!manager){fputs("PRIVATE_ACCOUNT_POLL manager_not_ready\n",stderr);return;}
   ((void(*)(id,SEL))[manager methodForSelector:refresh])(manager,refresh);
   fputs("PRIVATE_ACCOUNT_POLL refresh_requested\n",stderr);
  }@catch(NSException *e){fputs("PRIVATE_ACCOUNT_POLL refresh_exception\n",stderr);}
 }
}
__attribute__((constructor)) static void installPrivateAccountPoll(void){
 @autoreleasepool{
  if(![[[NSProcessInfo processInfo] processName] isEqualToString:@"CalendarAgent"])return;
  accountPollTimer=dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER,0,0,dispatch_get_main_queue());
  dispatch_source_set_timer(accountPollTimer,dispatch_time(DISPATCH_TIME_NOW,20*NSEC_PER_SEC),60*NSEC_PER_SEC,5*NSEC_PER_SEC);
  dispatch_source_set_event_handler(accountPollTimer,^{pollPrivateAccounts();});
  dispatch_resume(accountPollTimer);
  fputs("PRIVATE_ACCOUNT_POLL installed interval_seconds=60\n",stderr);
 }
}
