# Frontend UX checklist

Stabilization, 17 October 2026. The existing dark Linear design remains default.
`tests/browser_ux.py` drives actual backend decisions and checks UX; the original
browser suites remain required. Final executed counts are in FINAL_TEST_RESULTS.md.

| # | Feature | Classification | Implementation / verification |
|---|---|---|---|
| 1 | Dark mode toggle | IMPLEMENTED | Optional light theme, semantic tokens, accessible pressed state, persisted local preference; reload and responsive browser checks. |
| 2 | Cookie banner | NOT APPLICABLE | No cookies, trackers or third-party analytics. Only a local theme preference; explained in Help. |
| 3 | Search | IMPLEMENTED | Bound literal API search across event/message/session IDs, sender, reason and explanation; scenario and FAQ search. API tests cover SQL/wildcard literals, bounds and combined filters. |
| 4 | Back to top | IMPLEMENTED | Appears after document scrolling; returns scroll and keyboard focus to main. |
| 5 | Mobile menu | IMPLEMENTED | Active destination, focus on opening, Escape/outside dismissal and focus restoration; five required widths. |
| 6 | Loading | IMPLEMENTED | Connection, issuer, submit, suite, audit, metrics and exports have operation-specific states. No invented stage durations or percentages. |
| 7 | Interactive states | IMPLEMENTED | Shared hover, focus-visible, pressed, disabled and reduced-motion rules; real browser interaction checks. |
| 8 | Scroll progress | NOT APPLICABLE | Operational panels are not reading-progress tasks; searchable compact FAQ does not need an indicator. |
| 9 | Copy | IMPLEMENTED | Editor JSON, message/session/event IDs, input hash and reason code with success/failure feedback. Only public evidence fields. |
| 10 | Print | IMPLEMENTED | Decision dialog, state comparison, audit tables and reports use a paper palette and hide irrelevant controls; print-media DOM assertions. |
| 11 | Sticky headers | IMPLEMENTED | Existing sticky main navigation/table headers retained; menu bounded to viewport height. |
| 12 | Skip link | IMPLEMENTED | Keyboard-visible link targets focusable main content; browser assertion. |
| 13 | Password visibility | NOT APPLICABLE | No password fields or account system. |
| 14 | UTM tracking | NOT APPLICABLE | No approved analytics or marketing requirement; no external tracking added. |
| 15 | Success | IMPLEMENTED | Fixture/session/export/copy completion feedback remains distinct from receiver ACCEPTED/REJECTED. |
| 16 | Errors | IMPLEMENTED | Failed submit preserves exact editor bytes; failed downloads show recoverable errors; read-service failures cannot masquerade as data. |
| 17 | Confirmation | IMPLEMENTED | Session creation and reset warn about clearing drafts/comparisons and preserve server history/keys. Ordinary attacks remain direct. |
| 18 | Updated times | IMPLEMENTED | Actual received_at, successful audit refresh and suite executed_at; no synthetic freshness claims. |
| 19 | FAQ | IMPLEMENTED | Eight searchable native details covering HMAC, replay, tamper, permissions, expiry, state, chain and synthetic scope; keyboard modal containment. |
| 20 | Help/contact | IMPLEMENTED | Persistent header Help opens real searchable guidance and links repository demo docs. No fabricated support address or extra floating overlay. |

16 applicable items implemented; 4 intentionally not applicable; none blocked by design.
Final verification status depends on the executed gates, not this classification table.
