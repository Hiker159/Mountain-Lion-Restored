#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>
#include <stdlib.h>
#include <unistd.h>
static NSURL *notesLibrary;
static NSString *mailRoot;
static id privateMailRoot(id self,SEL cmd){(void)self;(void)cmd;return mailRoot;}
static id privateLibrary(id self,SEL cmd){(void)self;(void)cmd;return notesLibrary;}
__attribute__((constructor)) static void storageBootstrap(void){@autoreleasepool{
 NSString *path=[NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/ML Private Notes/Library"];
 notesLibrary=[[NSURL fileURLWithPath:path isDirectory:YES] retain];
 Method m=class_getClassMethod(NSClassFromString(@"NFPersistenceManager"),NSSelectorFromString(@"libraryURL"));
 char *type=m?method_copyReturnType(m):NULL;
 BOOL valid=m&&type&&type[0]=='@'&&method_getNumberOfArguments(m)==2;
 free(type);if(!valid){fputs("PRIVATE_NOTES_STORAGE_METHOD_MISMATCH\n",stderr);_exit(78);}
 if(![[NSFileManager defaultManager] createDirectoryAtPath:path withIntermediateDirectories:YES attributes:nil error:NULL]){fputs("PRIVATE_NOTES_STORAGE_CREATE_FAILED\n",stderr);_exit(78);}
 method_setImplementation(m,(IMP)privateLibrary);
 mailRoot=[[NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/ML Private Notes/Mail"] retain];
 Dl_info ownImage;
 if(!dladdr((void *)storageBootstrap,&ownImage)){fputs("PRIVATE_NOTES_MAIL_IMAGE_LOOKUP_FAILED\n",stderr);_exit(78);}
 NSString *frameworks=[[NSString stringWithUTF8String:ownImage.dli_fname] stringByDeletingLastPathComponent];
 NSString *message=[frameworks stringByAppendingPathComponent:@"Message.framework/Versions/B/Message"];
 if(!dlopen([message fileSystemRepresentation],RTLD_NOW|RTLD_LOCAL)){fprintf(stderr,"PRIVATE_NOTES_MAIL_LOAD_FAILED %s\n",dlerror());_exit(78);}
 Class defaults=NSClassFromString(@"Defaults");
 const char *image=defaults?class_getImageName(defaults):NULL;
 if(!image||!strstr(image,"/Contents/Frameworks/Message.framework/")){fputs("PRIVATE_NOTES_MAIL_CLASS_MISMATCH\n",stderr);_exit(78);}
 const char *names[]={"tildeUnresolvedBaseMailDirectory","unresolvedBaseMailDirectory","baseMailDirectory","nonContainerizedMailRootDirectory"};
 for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++){
  Method method=class_getInstanceMethod(defaults,sel_registerName(names[i]));
  char *result=method?method_copyReturnType(method):NULL;
  BOOL good=method&&result&&result[0]=='@'&&method_getNumberOfArguments(method)==2;free(result);
  if(!good){fputs("PRIVATE_NOTES_MAIL_METHOD_MISMATCH\n",stderr);_exit(78);}
 }
 if(![[NSFileManager defaultManager] createDirectoryAtPath:mailRoot withIntermediateDirectories:YES attributes:nil error:NULL]){fputs("PRIVATE_NOTES_MAIL_CREATE_FAILED\n",stderr);_exit(78);}
 for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++)method_setImplementation(class_getInstanceMethod(defaults,sel_registerName(names[i])),(IMP)privateMailRoot);
 fputs("PRIVATE_NOTES_MAIL_STORAGE_READY\n",stderr);
 fputs("PRIVATE_NOTES_STORAGE_READY\n",stderr);fflush(stderr);
}}
