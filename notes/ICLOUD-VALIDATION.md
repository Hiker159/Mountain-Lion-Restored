# iCloud Notes trial

Notes iCloud Menu Test 05 adds a Notes application menu action, Add iCloud Notes Account…, opening the existing private Mail/IMAP setup wizard. It is not the full system iCloud setup provider. The menu provides Apple’s IMAP/SMTP settings and directs the user to enable Notes only with an app-specific password. Existing private Google accounts and data paths remain unchanged.

The private pane method addAccountUsingPluginID:service: has a verified void return and two object arguments. The private Mail identifier org.ntest.mail.iaplugin occurs in both the framework and plugin metadata. This avoids relying on globally exported symbols from a framework loaded locally.

The original Apple iCloud provider depends on AOSUI and additional system services; this trial uses the existing private IMAP path. It does not implement the upgraded Notes format. Apple documents upgraded iCloud notes as requiring OS X 10.11 or later: https://support.apple.com/guide/notes/apda3f8513ed/mac . Mail settings: https://support.apple.com/102525 .

Runtime sign-in, legacy-note visibility, and two-way note synchronization are pending Mavericks testing. A successful IMAP login alone does not prove upgraded Notes compatibility.

Test 05 opened the private Mail wizard but iCloud auto-discovery failed. Its fallback tried launching org.ntest.mail, causing NSWorkspace launchApplicationAtURL assertion and an unresponsive sheet. Test 06 instead selects org.ntest.Notes.iaplugin; the private pane contains IANotesAccountSetupController and the Notes plugin accepts IANotesAccountSetupInput. This tests the dedicated Notes IMAP setup path. Runtime remains pending.

Test 06 failed to open the dedicated wizard with NSApplication modal-session assertions. Test 07 removes the introductory runModal alert, activates the Accounts window, and defers wizard creation to the next UI cycle. It also catches and logs exception names without credential values. Generic manual Mail setup retains the old handoff failure; the dedicated menu action is the test path. Runtime pending.

Test 07 executed the action but raised NSInternalInconsistencyException in NSApplication modal setup. Static inspection confirms IANotesAccountSetupController inherits the base controller without loading a standalone window: AccountSetupCommon.nib has no setup window; MailAccountSetup.nib supplies it to IAMailAccountSetupController. Test 08 therefore uses a custom iCloud form and directly invokes the private Notes plugin createAccountForInput:discoveredResult:error: API, matching the existing preconfigured-IMAP creation path. A fixed configurator supplies imap.mail.me.com, SSL, port 993, and the private ClearText password scheme over TLS. Credentials are entered in a secure field, cleared after creation, and not logged by the new UI. Creation, authentication, sidebar registration, and syncing are all pending runtime validation.

Test 08 showed the custom form but caught NSInvalidArgumentException without account creation result. Test 09 adds operation-stage names and a restricted class/selector extraction from unrecognized-selector exceptions. It never logs full exception reasons, account values or passwords. It is a diagnostic build, not a claimed fix.

Test 09 identified the failing call: MLNotesFixedIMAP userName, raised inside native_create. Test 10 adds userName, emailAddress, password and fullName accessors to the fixed configurator, supplying the same entered credentials to the native account creator. These values remain in process memory, are released with the configurator, and are never added to the new diagnostic output. Runtime account creation and sync remain pending.

Test 10 created an account and displayed it in the sidebar, but no notes appeared. The log confirms success=1, no IMAP authentication result, and AOS XPC unauthorized errors. Account creation is not authentication proof. Static inspection shows the plugin chooses NFAosImapAccountProxy for iCloud email addresses despite explicit IMAP settings. Test 11 scopes an isAOSEmailAddress bypass to creation of a new iCloud/me/mac IMAP trial account, forcing ordinary NFIMAPAccountProxy. Existing accounts are not converted or removed. TLS and password settings remain fixed. Runtime connection and legacy-note visibility remain pending.


Test 11 created an ordinary IMAP proxy but no notes appeared. Static inspection confirms NFIMAPAccount.isAOSAccount and proxy reconstruction reclassify Apple email addresses after creation. Test 12 keeps that classifier bypass active inside the private Notes process, including startup. Runtime validation pending.


Direct IMAP check 01 (2026-10-06): folder listing and read-only EXAMINE both returned curl exit 0. The legacy Notes folder exists and contains 9 messages. The supplied app-specific credentials and server access work in the direct diagnostic; this does not prove native Notes authenticated. Native private account/folder initialization remains unresolved (Test 12 defaultFolder assertion).


Test 13: native createAccountForInput saves an IMAP password only in the discovered-result proxy branch; the nil-result manual factory branch skips that step. During custom iCloud creation only, wrap the private factory, verify imap.mail.me.com + SSL + port 993, and call native setPassword before the account is committed. Log retrieval presence only. Correct receivingAccountInfo server key to MailAccountServerName. Existing stores retained. Runtime pending; defaultFolder assertion resolution not yet established.


Test 13 user validation (2026-10-06): all iCloud Notes folders and their respective notes downloaded successfully on Mavericks. Manifest confirms Test 13 and log records account creation success. Password-hook marker was absent, so the precise recovery mechanism is not proven. Three AOS authorization messages remain. Upload/edit/delete, persistence after relaunch, and background/logout behavior are not yet validated.


Test 13 follow-up: login persists and remote notes appear after relaunch; outgoing creation and live incoming deletion are not confirmed working. Test 14 adds private iCloud-only trace wrappers around native connection, refresh and IMAP upload methods, preserving their return values and behavior. No additional accounts or resets required. Runtime pending.


Test 14 trace confirms iCloud connection success and initial native folder refresh. One native update upload begins with no completion before capture; this suggests waiting inside the upload path but is not proof of a permanent hang. Notes Sync Inspection 01 samples only restored Notes processes to locate the wait. Runtime pending.


Test 14 confirmed working for two-way iCloud Notes creation and editing (2026-10-06): notes created in Restored Notes appeared on iPhone; edits on both devices propagated. Earlier comparison Mac had signed out, explaining misleading results. Missing upload-return marker does not establish a failed sync. Process inspection is no longer required. App relaunch sign-in persistence was already confirmed. Deletion propagation and app-quit background sync remain untested.


Deletion validation: iPhone deletion was reflected after relaunching Restored Notes; deletion in Restored Notes eventually propagated to iPhone. Both directions are confirmed, with a live incoming-deletion refresh limitation. App-quit background sync remains untested.
