# Final stabilization audit

Audit started 17 October 2026. Target: `kandukurinomusubramanyachary-ai/KAVACH`.
Baseline main: `6b473b4b2a8578c1b60c38aa7683b884ccd4d149`.
Fresh checkout; working tree clean; branch `fix/final-stabilization` created.
No pre-existing runtime directory or local changes were present. Tests must use
temporary data directories; never initialize the presenter's default runtime.

The README, DESIGN, roadmap, feature map, prior test/risk/security reports, contract,
release builder/manifest, package manifests, source imports and test runners were
reviewed. Historical reports describe another environment and are not fresh evidence.

## Findings before fixes

| ID / severity | Exact file | Reproduction / root cause | Required fix / regression | Actual verification |
|---|---|---|---|---|
| R01 critical | `release-files.json` | `python scripts/release.py --output ../KAVACH-baseline.zip` refuses missing `reports/browser-results.json`; obsolete generated evidence is allowlisted, current components/fonts/tests are missing. | Review exact source allowlist; add source-completeness and clean-extraction gates without weakening path, hash or secret checks. | Baseline failure reproduced. Final result recorded in RELEASE_VERIFICATION.md. |
| R02 high | `.github/workflows/ci.yml` (absent) | No workflow in fresh checkout. | Five independent jobs for Python, frontend, scenarios, browsers, secure extraction. | Implemented; local gates verified. Remote status is recorded in CI_VERIFICATION.md. |
| R03 high | `scripts/test-editor.mjs`, `scripts/test-csv.mjs`, `tests/test_frontend_gates.py` | Direct native esbuild path and ELF-only assertion assume Linux; Windows uses a different binary layout. | Use esbuild's supported JavaScript API and execute real module assertions on every platform. | Editor 12/12, CSV 12/12 and actual Windows frontend subprocess gates PASS. |
| R04 medium | `tests/test_release.py` | Real archive gate skips unless a specially named sibling ZIP exists. | Build and verify a fresh real archive in a temporary directory, never silently skip. | Fresh real archive gate PASS; OS symlink check explicitly skipped on Windows. |
| R05 medium | `web/src/main.tsx` | Search sends all text as an exact reason code; CSV ignores date filters and silently stops at 200 rows. | Search actual audit identifiers/reasons; export all matching records with identical filters. | PASS: real API search, 206-row export, six-step browser journey. |
| R06 medium | `web/src/components/GuidedDemo.tsx`, `web/src/main.tsx` | Guide's normal fixture inherits prior form fields; step outcome can refer to an earlier submission. | Explicit valid operator fixture for guide; show outcomes for the relevant step; test six-step journey. | PASS: real API search, 206-row export, six-step browser journey. |
| R07 medium | `web/src/main.tsx`, `web/src/tokens.css`, `web/src/styles.css` | Missing light theme, skip link, comprehensive help, print rules, mobile Escape/focus handling and export/loading feedback. | Apply relevant UX checklist while preserving incumbent design and security semantics. | PASS: 46 browser UX checks; applicability in FRONTEND_UX_CHECKLIST.md. |

## Risk controls

Keep the eight-stage receiver, canonical HMAC, replay streams and transaction logic
unchanged. Exact packaging must fail on omissions; generated evidence is not source.
Run all tests and server processes on disposable paths. Do not expose fixture signing
or policy administration publicly. Never copy historical PASS counts into final results.
Commit/push only the named target; no deployment, merge or force push is authorized.

## Execution evidence

Fresh commands, counts, limitations and final outcomes are maintained in
`FINAL_TEST_RESULTS.md`, `RELEASE_VERIFICATION.md`, `CI_VERIFICATION.md` and
`FRONTEND_UX_CHECKLIST.md`. Ignored `reports/final/` contains raw execution logs.

### Additional findings during independent QA

- R08 / medium, `web/src/csv.ts`: rejected claimed sender strings can begin with
  spreadsheet formula characters. RFC quoting alone does not stop formula evaluation.
  Fix: escape formula-like string cells; numeric measurements remain numeric; JSON
  keeps original evidence. Two CSV regressions added.
- R09 / medium, `web/src/styles.css`: details/summary pipeline, highlighted editor,
  line-number spans and threat definition lists were styled as older markup. Real
  screenshots showed vertical stage labels, inline numbers and an unstyled textarea.
  Corrected selectors in release.css; responsive/editor browser assertions cover this.
- R10 / medium, `tests/visual_design.py`: a fixed port and swallowed seed exceptions
  could inspect another local process or show empty data. Use the shared disposable
  server and assert each real seed response. Missing verdict banners now fail.
- R11 / low, `web/public/fonts/`: new font families lacked their own redistribution
  notices. Added official Inter and JetBrains Mono OFL texts to the exact allowlist.

Fresh intermediate Python result: 246 passed, 2 explicitly skipped on Windows,
0 failed (187.88s). Skips are POSIX permissions and OS symlink privilege; Linux CI
must execute both. Test-development mistakes (default TestClient host rejected by
local guard, invalid empty SET_MODE fixture) were corrected without weakening the guard.

- R12 / high, `backend/engine.py::verify_audit_chain` and `export`: the new real
  browser export regression failed after a suite introduced another session.
  Traversal failed to advance the global previous hash for other-session links;
  export also verified through a separate connection after its evidence snapshot.
  Fix: always advance through the global chain, report its scope, and verify inside
  the same read transaction as state/events/suites. Regressions cover interleaved
  sessions, actual covered-field tampering, and reuse of the export snapshot.
  The receiver stages, hash representation and acceptance transaction are unchanged.

- R13 / high, `web/src/components/AttackTimeline.tsx`: an operational SERVICE_ERROR
  was labeled Accepted in the timeline heading, and its first failure read None.
  Fix: use the actual verdict/checks and confirmed audit_persisted flag. Regression
  renders a real storage-failure receiver response through React server rendering.
  No security verdict is mocked or fabricated for this test.

## Final verification

Full latest Python gate: 249 passed / 2 platform skips / 0 failures, 43.35 s.
Editor 12/12; CSV 12/12; build PASS; security 31/31; acceptance 9/9;
browser smoke 16/16, hardening 30/30, design 8/8, visual 39/39, UX 46/46.
The final release gate independently installs/builds/starts an extracted source ZIP;
its generated report records the exact hash and status. CI status is read from GitHub,
never inferred from local results. See the companion verification documents.
