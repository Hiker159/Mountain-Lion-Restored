#import <Cocoa/Cocoa.h>
#include <sys/sysctl.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <errno.h>
static void fail(NSString *message){NSAlert *a=[[[NSAlert alloc] init] autorelease];[a setMessageText:@"Restored app could not open"];[a setInformativeText:message];[a runModal];exit(1);}
static int run(NSString *exe,NSArray *args){NSTask *t=[[[NSTask alloc] init] autorelease];[t setLaunchPath:exe];[t setArguments:args];[t setStandardInput:[NSFileHandle fileHandleWithNullDevice]];[t launch];[t waitUntilExit];return [t terminationStatus];}
int main(int argc,char **argv){@autoreleasepool{
 NSString *app=[[NSBundle mainBundle] bundlePath],*kind=[[NSBundle mainBundle] objectForInfoDictionaryKey:@"MLRestoredAppKind"];
 if(![@[@"Notes",@"Contacts",@"Calendar"] containsObject:kind])fail(@"The application configuration is missing.");
 NSString *folder=[app stringByDeletingLastPathComponent],*home=NSHomeDirectory();
 NSString *frameworks=[app stringByAppendingPathComponent:@"Contents/Frameworks"],*exe=[app stringByAppendingPathComponent:[@"Contents/MacOS/" stringByAppendingString:kind]];
 NSMutableArray *defs=[NSMutableArray array];
 NSArray *pairs=nil;NSString *profile=nil,*logName=nil,*libraries=nil;
 NSMutableArray *extra=[NSMutableArray array];
 if([kind isEqual:@"Notes"]){
 pairs=@[@[@"KEYCHAINS",@"Library/Keychains"],@[@"ACCOUNTS",@"Library/Accounts"],@[@"INET",@"Library/Internet Accounts"],@[@"MAIL",@"Library/Mail"],@[@"NOTES",@"Library/Containers/com.apple.Notes"],@[@"CONTACTS",@"Library/Application Support/AddressBook"],@[@"CALENDARS",@"Library/Calendars"],@[@"NOTES_PREFS",@"Library/Preferences/com.apple.Notes.plist"],@[@"MAIL_PREFS",@"Library/Preferences/com.apple.mail.plist"]];profile=@"notes-private.sb";logName=@"ML Private Notes";
 libraries=[NSString stringWithFormat:@"%@/MLAccountBootstrap.dylib:%@/MLNotesStorage.dylib:%@/MLNotesAccountsUI.dylib",frameworks,frameworks,frameworks];
 }else if([kind isEqual:@"Contacts"]){
 pairs=@[@[@"STOCK_CONTACTS",@"Library/Application Support/AddressBook"],@[@"STOCK_ACCOUNTS",@"Library/Accounts"],@[@"STOCK_INET",@"Library/Internet Accounts"],@[@"STOCK_CALENDARS",@"Library/Calendars"],@[@"STOCK_CONTACT_PREFS",@"Library/Preferences/com.apple.AddressBook.plist"]];profile=@"contacts-accounts.sb";logName=@"ML Contacts Accounts";
 libraries=[frameworks stringByAppendingPathComponent:@"MLAccountBootstrap.dylib"];
 [extra addObjectsFromArray:@[@"-MLAlternateDataStoreDirectory",[home stringByAppendingPathComponent:@"Library/Application Support/ML-GContact"]]];
 }else{
 pairs=@[@[@"STOCK_CALENDARS",@"Library/Calendars"],@[@"STOCK_ICAL_SUPPORT",@"Library/Application Support/iCal"],@[@"STOCK_CONTACTS",@"Library/Application Support/AddressBook"],@[@"STOCK_ICAL_PREFS",@"Library/Preferences/com.apple.iCal.plist"],@[@"STOCK_ACCOUNTS",@"Library/Accounts"],@[@"STOCK_INET",@"Library/Internet Accounts"]];profile=@"calendar-trial.sb";logName=@"ML Calendar Private Accounts";
 libraries=[frameworks stringByAppendingPathComponent:@"MLAccountBootstrap.dylib"];
 [extra addObjectsFromArray:@[@"-MLAlternateDataStoreDirectory",[home stringByAppendingPathComponent:@"Library/Application Support/ML-AcctBook"],@"-MLCalAuthDirectory",[home stringByAppendingPathComponent:@"Library/MLCalAuth"],@"-iCalApplicationSupportDirectory",[home stringByAppendingPathComponent:@"Library/Application Support/ML-CalAuthx"]]];
 }
 for(NSArray *p in pairs)[defs addObjectsFromArray:@[@"-D",[NSString stringWithFormat:@"%@=%@",p[0],[home stringByAppendingPathComponent:p[1]]]]];
 [defs addObjectsFromArray:@[@"-f",[folder stringByAppendingPathComponent:profile],@"/usr/bin/env",[@"DYLD_INSERT_LIBRARIES=" stringByAppendingString:libraries],exe]];
 [defs addObjectsFromArray:extra];
 for(int i=1;i<argc;i++)[defs addObject:[NSString stringWithUTF8String:argv[i]]];
 // Static planning mode runs only this new launcher; never loads legacy libraries.
 if(argc==2&&!strcmp(argv[1],"--print-launch-plan")){[defs removeLastObject];NSData *data=[NSJSONSerialization dataWithJSONObject:@{@"app":app,@"kind":kind,@"executable":exe,@"arguments":defs} options:NSJSONWritingPrettyPrinted error:NULL];fwrite([data bytes],1,[data length],stdout);return 0;}
 char release[128];size_t length=sizeof(release);
 if(sysctlbyname("kern.osrelease",release,&length,NULL,0)||strncmp(release,"13.",3))fail(@"These restored apps require OS X Mavericks (10.9).");
 if(geteuid()==0)fail(@"Open this app as your normal logged-in user, without sudo.");
 unsetenv("DYLD_INSERT_LIBRARIES");unsetenv("DYLD_PRINT_LIBRARIES");unsetenv("NSRunningFromLaunchd");
 if(run(@"/usr/bin/codesign",@[@"--verify",@"--deep",app]))fail(@"The app's signature check failed. Reinstall the complete package.");
 NSFileManager *fm=[NSFileManager defaultManager];
 if(![fm isExecutableFileAtPath:exe]||![fm fileExistsAtPath:[folder stringByAppendingPathComponent:profile]])fail(@"Required application files are missing. Reinstall the complete package.");
 NSString *logDir=[home stringByAppendingPathComponent:[@"Library/Logs/" stringByAppendingString:logName]];
 if(![fm createDirectoryAtPath:logDir withIntermediateDirectories:YES attributes:nil error:NULL])fail(@"The log folder could not be created.");
 for(NSUInteger i=1;i<[extra count];i+=2)if(![fm createDirectoryAtPath:extra[i] withIntermediateDirectories:YES attributes:nil error:NULL])fail(@"A private data folder could not be created.");
 int fd=open([[logDir stringByAppendingPathComponent:[kind stringByAppendingString:@".log"]] fileSystemRepresentation],O_WRONLY|O_CREAT|O_APPEND,0600);
 if(fd<0)fail(@"The application log could not be opened.");dup2(fd,STDOUT_FILENO);dup2(fd,STDERR_FILENO);close(fd);
 int input=open("/dev/null",O_RDONLY);if(input>=0){dup2(input,STDIN_FILENO);close(input);}
 if([kind isEqual:@"Calendar"]&&run(@"/usr/bin/python",@[[folder stringByAppendingPathComponent:@"calendar_login_control.py"],@"open"]))fail(@"The Calendar alert helper could not start. Use the diagnostic tools in the installation folder.");
 if([kind isEqual:@"Contacts"]){
 NSString *job=[home stringByAppendingPathComponent:@"Library/LaunchAgents/org.ctest.AddressBook.SourceSync.plist"];
 NSDictionary *saved=[NSDictionary dictionaryWithContentsOfFile:job];
 if([[saved objectForKey:@"MLRestoredContactsManaged"] intValue]==1&&[[saved objectForKey:@"Label"] isEqual:@"org.ctest.AddressBook.SourceSync"]){
 if(run(@"/usr/bin/python",@[[folder stringByAppendingPathComponent:@"contacts_background_control.py"],@"enable"]))fail(@"The existing Contacts background sync could not be moved to this installation.");
 }
 }
 const char **args=calloc([defs count]+2,sizeof(char *));args[0]="/usr/bin/sandbox-exec";
 for(NSUInteger i=0;i<[defs count];i++)args[i+1]=[[defs objectAtIndex:i] fileSystemRepresentation];
 execv(args[0],(char *const *)args);free(args);fail(@"The protected application launch failed.");
}return 1;}
