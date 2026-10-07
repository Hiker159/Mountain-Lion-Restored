#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
static NSURL *notesLibrary;
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
 fputs("PRIVATE_NOTES_STORAGE_READY\n",stderr);fflush(stderr);
}}
