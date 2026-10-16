# Two-minute judge demonstration

Launch the supported Python-served build using README startup commands, then open
http://127.0.0.1:8000. Everything below is available in the UI; no hidden commands,
automatic acceptance or bypassed checks are used.

1. **Prepare (10 s).** Point out local synthetic simulation, API Connected and the
   current session. Click **Reset**, confirm **Reset demo** if starting another run.
   History, audit links and signing keys are preserved. Mode starts NORMAL / 10 s.
2. **Valid command (15 s).** Open **Demo** and generate the valid-command fixture.
   The console opens. Press **Submit for validation**: ACCEPTED / OK, all eight
   checks pass, mode becomes POWER_SAVING and the receipt confirms audit/replay.
   Click **Return to guided demo**.
3. **Replay (10 s).** Click **Next step**, generate the replay fixture, submit exact
   original bytes. Expect REPLAY and unchanged protected state. Return to the guide.
   Do this within the original 60-second lifetime; EXPIRED is the correct earlier
   time-stage result if delayed. Restart the demonstration to show a fresh replay.
4. **Tamper (15 s).** Next step, generate payload tampering, submit. Observe
   AUTH_FAILED; later checks are NOT RUN. State/accepted telemetry/replay remain
   unchanged. Return to the guide.
5. **Authorization (15 s).** Next step, generate the observer fixture, submit.
   Authentication passes, permissions fail: NOT_AUTHORISED. Explain that a valid
   HMAC does not grant permission. Return to the guide.
6. **Comparison (15 s).** Next step, **Open captured comparison**. The two sides are
   real decisions captured from the accepted command and rejected attack. Inspect
   state before/after and event IDs; export comparison if useful.
7. **Evidence and tests (25 s).** Return to **Demo**, Next step. **Verify audit chain**
   checks the global hash-linked history read-only. **Run security suite** executes
   the actual 31 cases, isolated from live mission metrics. Open audit evidence,
   search an event/reason, inspect, copy, print or export JSON/CSV.

The guide marks a step complete only from actual outcomes/captured decisions, not
because it was visited. Repeated fixtures are fresh operator commands; the replay
step alone loads accepted original bytes. Generate after any delay, never re-sign by
editing or formatting. Backend errors remain operational failures, never acceptance.

Explain the boundary: HMAC is shared-key integrity/authentication, not encryption;
model telemetry is synthetic; the audit chain checks only its listed covered fields,
not origin or a complete rewrite from genesis. This is a local simulator, not a
certified spacecraft system. Keep privileged signing/policy endpoints off untrusted
networks. Final executed results are in FINAL_TEST_RESULTS.md.
