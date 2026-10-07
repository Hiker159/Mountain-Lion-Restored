"""Shared Calendar trial inputs and deliberately excluded legacy helpers."""
FRAMEWORKS = ['CalendarStore', 'CalendarAgentLink', 'CalendarUI', 'CalendarDraw',
              'CalendarFoundation', 'EventKit', 'AOSAccounts', 'Admin',
              'Message', 'IMAP', 'CoreMessage', 'CalendarAgent']
EXCLUDED = [
    'Message.framework/Versions/B/Resources/Syncer.syncschema',
    *['Admin.framework/Versions/A/Resources/' + name for name in
      ('writeconfig', 'readconfig', 'DirectoryTools', 'UpdateSettingsTool',
       'activateSettings', 'userInit')],
    'CalendarStore.framework/Versions/A/Resources/iCal.syncschema',
    'CalendarStore.framework/Versions/A/Resources/iCalExternalSync',
]
