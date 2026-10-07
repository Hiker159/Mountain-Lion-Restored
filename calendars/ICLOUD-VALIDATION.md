# iCloud Calendar validation

On 2026-10-05, the user reported that downloading calendars/events, creating events, remote edits, deletion and reopening worked in Calendar-iCloud-Trace-Test-03. Setup used manual CalDAV with the principal server/path discovered by the connection test and an Apple app-specific password. The direct discovery and principal tests both returned HTTP 207.

The latest collected Calendar log contained no account-refresh failure, and all 22 recorded account password reads returned a nonempty value. AOSKit still logged 178 unauthorized-client messages. These messages have not prevented the reported CalDAV tests, but their cause remains unresolved. Do not describe this as isolated full iCloud account-service support.

The dedicated iCloud wizard remains disabled. Contacts/Notes iCloud support and iCloud-specific background/login/alert tests remain unverified. The diagnostic build adds tracing only, so its successful run does not establish a causal authentication fix.

The subsequent closed-app test failed: the helper remained running but the remote event was fetched only when Calendar opened, after which its alert appeared. `account_calendar_poll.m` / `build_calendar_background04.py` add an experimental 60-second refresh fallback through the private CalendarAgent refresh manager. Background behavior remains pending runtime validation; there is no claim of working iCloud push delivery.

On 2026-10-06, the new helper (PID 2000) logged four refresh requests with no account-refresh failure in the collected setup log, but the user reported no notification while closed or after reopening. Poll invocation alone does not validate download completion or alarm scheduling. Full startup/alarm diagnostics and the event alert state are needed before claiming background support or selecting a fix.

A follow-up on 2026-10-06 confirmed alerts for a remotely created iCloud event at 11:53 and an event created in restored Calendar at 11:55. The full helper log confirms the 60-second poll timer, repeated refresh requests, a running helper (PID 2000), and wake recovery rescans around both times, with no account-refresh failures in the current log. Event-specific delivery is confirmed by the user; the log does not name those events. A third remotely edited/moved event alerted on neither Mac, so its failure cannot yet be attributed to the restored helper. Logout/login validation remains pending. AOS unauthorized-client warnings persist.
