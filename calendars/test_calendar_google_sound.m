#define ML_GOOGLE_SOUND_TEST 1
#import "calendar_google_sound.m"
#include <assert.h>
int main(){@autoreleasepool{
 NSString *audio=@"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:test\r\nBEGIN:VALARM\r\nACTION:AUDIO\r\nTRIGGER:-PT30M\r\nATTACH:Basso\r\nEND:VALARM\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n";
 NSString *result=MLGoogleSoundBody(audio);
 assert([result rangeOfString:@"ACTION:AUDIO"].location==NSNotFound);
 assert([result rangeOfString:@"ACTION:DISPLAY\r\nX-RESTORED-CALENDAR-AUDIO:1"].location!=NSNotFound);
 assert([result rangeOfString:@"TRIGGER:-PT30M\r\nATTACH:Basso"].location!=NSNotFound);
 assert([result hasSuffix:@"END:VCALENDAR\r\n"]);
 assert([MLGoogleSoundBody(result) isEqual:result]);
 NSString *message=[audio stringByReplacingOccurrencesOfString:@"ACTION:AUDIO" withString:@"ACTION:DISPLAY"];
 assert(MLGoogleSoundBody(message)==message);
 assert([MLGoogleSoundBody(@"<xml>BEGIN:VCALENDAR</xml>") isEqual:@"<xml>BEGIN:VCALENDAR</xml>"]);
 NSString *uid=nil;NSDictionary *entries=MLSoundEntries(audio,&uid);assert([uid isEqual:@"test"]);assert([entries[@"TRIGGER:-PT30M"] isEqual:@"Basso"]);
 assert([MLSoundEntries(message,NULL) count]==0);
 assert([MLSoundEventKey(uid) length]==64);assert(![MLSoundEventKey(uid) isEqual:MLSoundEventKey(@"another-event")]);
 assert(MLGoogleHost(@"calendar.google.com"));assert(!MLGoogleHost(@"calendar.google.com.example.org"));
 puts("PASS: upload transform, trigger/attachment preservation, message passthrough, idempotence and exact Google host guard.");
}return 0;}
