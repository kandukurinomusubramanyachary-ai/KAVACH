# Final test results

Fresh local verification, 17 October 2026. Target branch: fix/final-stabilization.
Windows / Python 3.14.3 / Node 24.13.0 / Playwright 1.64.0 Chromium.
No old PASS result was copied into these figures.

| Gate | Actual result | Evidence |
|---|---|---|
| Python unit/API/full discovery | 249 passed, 0 failed, 2 skipped; 43.35 s | reports/final/pytest.xml and pytest.log |
| Editor | 12/12 passed | reports/final/editor.log |
| CSV | 12/12 passed | reports/final/csv.log |
| TypeScript / Vite | PASS | build.log; clean extraction rebuilds from shipped sources |
| Security scenarios | 31/31 passed; isolated active state unchanged | scenarios.log |
| Acceptance | 9/9 passed | acceptance.log |
| Browser smoke | 16/16 passed | reports/browser-results.json |
| Browser hardening | 30/30 passed | reports/sprint/browser-hardening.json |
| Browser design | 8/8 passed | reports/design/verification.json |
| Visual design | 39/39 passed | visual-design.log |
| UX / judge journey | 46/46 passed | reports/final/ux-results.json |
| Offline fallback | Eight JS scenarios passed; zero runtime errors/external requests | reports/offline-prototype-tests.json |
| Exact release packaging / hash and secret checks | PASS on rebuilt candidate | release CLI output; final artifact report |
| Clean-extraction final artifact | See generated clean-extraction.json for the exact ZIP hash and executed result | independent scripts/verify_release.py --browser |
| GitHub Actions | See CI_VERIFICATION.md; local success does not establish remote CI | actual GitHub run/jobs required |

The 2 skips are POSIX permission enforcement (not applicable on Windows) and OS
symlink creation (WinError 1314, missing account privilege). Neither is a pass.
Archive symlink refusal is tested on Windows without OS privileges. Ubuntu CI must
execute both platform gates and fail on required skips.

The suite now collects 251 Python tests: 21 added against the fresh baseline's 230
collected tests. Additions: 8 Windows-unsafe path cases, 5 source/hash/report/archive
regressions, 5 audit-search cases, 2 global-chain/export-snapshot cases and 1 React
renderer regression using a real storage-failure response. CSV grows 10 to 12 with
formula-string safety and numeric negative-value tests. Visual checks grow 38 to 39
because an absent verdict banner now explicitly fails. No expected security count
was changed: runtime remains 31 and acceptance remains 9.

The browser journey executed the six guided steps in 8.05 seconds of automation
(excluding human explanation); this is not a measured human-demo duration. The UI
requires user generation/submission. It captures actual comparison decisions,
verifies the chain, runs the real suite and proves live metrics remain unchanged.
Replay was within lifetime. No per-stage timing or outcome is invented.

Additional coverage: 206-row CSV pagination, identical search/date constraints,
actual IDs and rejection-code searches, global audit verification after other-session
suite activity, covered-field tampering, same-snapshot export, copy feedback, print,
failed transport recovery, persisted light theme, FAQ focus, mobile Escape and skip
link, and no page-level overflow at 1440/1024/768/390/320. Intentional table scrolling
remains inside its container. All browser suites reported no uncaught page errors.

Real screenshots: reports/design/{console,demo,scenarios,timeline,compare,metrics,
audit,policy}-{desktop,tablet,mobile}.png; reports/final/ux-light-*.png,
ux-comparison.png, ux-guide-completed.png and ux-mobile-light.png. These are ignored
local/CI artifacts, never allowlisted release source or unreviewed recordings.

The mechanical design scan reports only two Inter-font warnings. The brief explicitly
requires preserving that incumbent system. Human review of desktop/mobile dark and
light screenshots confirmed the corrected editor, pipeline, threat text and layout.

Initial failed attempts remain documented: obsolete release entries; Windows esbuild
invocation; Node reporter mismatch; unavailable OS symlink privilege; a default-host
TestClient fixture; test queries matching legitimate literal underscores/threat text;
and the renderer harness's external-package resolution. Fixes were verified, not
hidden by changing the security verdicts or bypassing checks. One Starlette/httpx
deprecation warning remains; no uncontrolled package upgrades were made.

Runtime safety: fresh checkout had no data directory, and none was created in the
project. Every executed engine/server used disposable test data. Signing keys,
protected state, replay records and historical audit data from a presenter were not
accessed, reset or rotated. Release defenses detected synthetic secret canaries in
negative tests; known-secret scanning is not a universal detector.
