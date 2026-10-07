#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <stdio.h>
#include <stdlib.h>
static NSString *pluginRoot;
static IMP originalLoad,originalCreate;
static NSString *privatePath(NSString *path){
 NSString *name=[path lastPathComponent];
 if(![name isEqualToString:@"Google.iaplugin"]&&![name isEqualToString:@"AddressBook.iaplugin"])return nil;
 return [pluginRoot stringByAppendingPathComponent:name];
}
static void routedLoad(id self,SEL cmd,NSString *path,id identifiers){
 NSString *private=privatePath(path);
 if(private)((void(*)(id,SEL,id,id))originalLoad)(self,cmd,private,identifiers);
}
static id routedCreate(id self,SEL cmd,NSString *path){
 NSString *private=privatePath(path);
 return private?((id(*)(id,SEL,id))originalCreate)(self,cmd,private):nil;
}
__attribute__((visibility("default"))) int MLInstallPrivateAccountPluginRouting(const char *root){
 if(pluginRoot||!root)return 1;
 Class cls=NSClassFromString(@"IAPluginManager");
 Method load=class_getInstanceMethod(cls,NSSelectorFromString(@"_loadPluginAtPath:identifiers:"));
 Method create=class_getInstanceMethod(cls,NSSelectorFromString(@"createIAPluginAtPath:"));
 if(!load||!create)return 2;
 char *lr=method_copyReturnType(load),*cr=method_copyReturnType(create);
 BOOL types=lr&&cr&&lr[0]=='v'&&cr[0]=='@'&&method_getNumberOfArguments(load)==4&&method_getNumberOfArguments(create)==3;
 free(lr);free(cr);if(!types)return 3;
 pluginRoot=[[NSString stringWithUTF8String:root] copy];
 if(![pluginRoot isAbsolutePath]){[pluginRoot release];pluginRoot=nil;return 4;}
 originalLoad=method_setImplementation(load,(IMP)routedLoad);
 originalCreate=method_setImplementation(create,(IMP)routedCreate);
 puts("PRIVATE_PLUGIN_ROUTING_INSTALLED");return 0;
}
