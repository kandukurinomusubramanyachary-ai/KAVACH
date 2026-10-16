# Roadmap Progress — KAVACH 24-Feature Completion

Branch: `feature/roadmap-24-completion`
Status: **all 24 features implemented and tested** against the local Python runtime.

This document records what was actually built, which files implement it, how it was
verified, and what is still limited. Numbers in this file come from real runs; nothing
is estimated. See `docs/TEST_RESULTS.md` for gate output and
`docs/REMAINING_RISKS.md` for known limits.

---

## Phase 0 — Baseline audit

**Deliverable:** `docs/ROADMAP_BASELINE_AUDIT.md` (created).

All 24 features were mapped to implementing files before any code changed, and each
was classified P0–P3. One genuine repository defect was found and fixed:

| ID | Defect | Fix | Verification |
|----|--------|-----|--------------|
| DEFECT-01 | `npm run test:editor` crashed: `scripts/test-editor.mjs` fed esbuild's native ELF binary to `node`, producing `SyntaxError: Invalid or unexpected token`. The gate was broken, not the code. | Execute the platform binary directly. | `12/12` editor tests pass. Regression test in `tests/test_frontend_gates.py`. |

Commit `ded21d9b`.

---

## Phase 1 — Mission Control + Attack Lab (features 1–4)

**Deliverable:** `docs/FEATURE_IMPLEMENTATION.md` §Phase 1.

| Feature | Implementation | Files |
|---|---|---|
| 1. Telemetry + protected state | Existing telemetry/state surfaces retained and documented. | `web/src/main.tsx`, `backend/engine.py` |
| 2. Compose & submit | Message composer retained; signing is fixture-side and stays outside the receiver. | `web/src/main.tsx`, `web/src/editor.ts` |
| 3. Attack presets | Three **required** presets added (`unknown_key` → `KEY_UNKNOWN`, `bad_tag` → `AUTH_FAILED`, `malformed` → `INVALID_JSON` with `raw_text`), alongside the existing presets. | `backend/app.py`, `web/src/main.tsx` |
| 4. Visual validation pipeline | Ordered 8-stage pipeline with PASS/FAIL/**NOT RUN**. | `web/src/components/ValidationPipeline.tsx` |

Also in Phase 1: versioned state migration to schema v2 (`STATE_SCHEMA_VERSION`,
`_migrate_state()`), synthetic `MODEL_RULES` for `antenna_status`/`power_level_pct`, and
the `ThreatPanel` explaining each preset.

**Migration safety was verified on a copy of the live database before the live database
migrated:** values and all 3 audit events preserved, key file byte-identical. Only then
was the live database allowed to migrate.

Commit `49e2f8e`.

---

## Phase 2 — Security depth + evidence integrity (features 5–10)

**Deliverable:** `docs/SECURITY_VERIFICATION.md`.

| Feature | Implementation | Files |
|---|---|---|
| 5. Replay protection | Per-sender monotonic sequence + issuer nonce; enforced in the `replay` stage. | `backend/engine.py` |
| 6. Unauthorized sender handling | `SET_MODE`/`SET_REPORT_INTERVAL` reserved for `operator-01`; observers denied. | `backend/engine.py` |
| 7. Tampered message detection | HMAC-SHA256 over the canonical envelope, compared with `hmac.compare_digest`. | `backend/engine.py` |
| 8. State protection | Rejection returns before any protected write, inside one transaction. | `backend/engine.py` |
| 9. Tamper-evident audit | Hash-linked chain (`record_hash = SHA256(prev_hash ‖ 0x00 ‖ canonical(covered_fields))`), written in the same transaction as the record. 17 covered fields. | `backend/engine.py` |
| 10. Server-authoritative policy | `policy` table, `role_for()`, `permitted()`, `policy_version()`, versioned audit of changes, admin surface gated off by default. | `backend/engine.py`, `backend/app.py` |

Two real defects were found by the new tests during this phase and fixed:

1. **Role-model regression:** a first cut gave `OPERATOR` the `TELEMETRY_STATUS`
   action, breaking `test_humans_cannot_publish_telemetry_satellite_cannot_command`.
   Fixed by adding a distinct `TELEMETRY_SOURCE` role.
2. **Design flaw:** `permitted()` opened a **second** SQLite connection inside
   `validate()`'s open `BEGIN IMMEDIATE` transaction, which moved injected commit
   failures to the wrong stage and risked lock contention. Fixed by threading the
   caller's `db` through `permitted()`/`role_for()`/`_stored_policy()`.

A third finding was a bug in my own verification, not in the product: a "chain detects
nothing" symptom was caused by mutating a record that was already `ACCEPTED`/`OK`, so
the UPDATE was a no-op. Retested on a genuinely rejected record, the chain reported
`FAILED / RECORD_MODIFIED`.

Commit `ea57894`.

---

## Phase 3 — Judge experience (features 11–18)

**Deliverable:** `docs/DEMO_SCRIPT.md`, `docs/FEATURE_IMPLEMENTATION.md` §Phase 3.

| Feature | Implementation | Files |
|---|---|---|
| 11. Attack timeline | Linear `MESSAGE RECEIVED → … → AUDIT EVIDENCE`. Stages that never ran read **NOT RUN**. No per-stage duration is invented; only the end-to-end decision is measured, and the panel says so. | `web/src/components/AttackTimeline.tsx` |
| 12. Normal vs attack comparison | Both columns are real submissions. Changed fields, verdicts, first failure, state before/after, per-stage results, audit references, raw bytes, JSON export. | `web/src/components/ComparisonView.tsx` |
| 13. Metrics dashboard | Every counter comes from `GET /api/metrics`. **Replaced the hardcoded `MiniSpark` SVG**, which presented a static curve in a security UI while being derived from nothing. | `web/src/components/MetricsDashboard.tsx`, `backend/engine.py` |
| 14. Guided demo | Six steps, ~90 s. Every step is user-triggered; the guide never submits silently and no check is bypassed. | `web/src/components/GuidedDemo.tsx` |
| 15. Before/after state display | Before/after on both the console and the comparison screen. | `web/src/main.tsx`, `web/src/components/ComparisonView.tsx` |
| 16. CSV export | RFC 4180 quoting, pure module, unit-tested. Covers 14 decision columns; no secret material. | `web/src/csv.ts`, `scripts/test-csv.mjs`, `web/src/main.tsx` |
| 17. Protected-state invariants panel | Protected vs derived state, integrity counter, integrity violations. | `web/src/components/MetricsDashboard.tsx`, `web/src/main.tsx` |
| 18. Reproducible sessions | `POST /api/demo/sessions` (new isolated session) and `POST /api/demo/reset` (deterministic reset to the documented `INITIAL`, reporting what was preserved). | `backend/app.py`, `backend/engine.py` |

**Metrics scope fix.** The first cut of `metrics()` counted *every* session, which
leaked isolated suite decisions into the live dashboard. `scope` now defaults to the
active session; suite statistics are reported separately under `scenario_suites`.

Commit `017e792` (backend) and `078314b` (UI).

---

## Phase 4 — Advanced engineering (features 19–24)

**Deliverable:** `docs/TEST_RESULTS.md`, `docs/REMAINING_RISKS.md`.

| Feature | Implementation | Files |
|---|---|---|
| 19. Fault injection | Suite expanded 29 → 31, adding the two missing roadmap cases: **oversized body** and **corrupt storage**. `SCENARIO_CASE_COUNT` is declared and asserted equal to the executed suite, and the UI count is fetched, so the displayed number cannot drift. | `backend/engine.py`, `tests/test_phase4.py` |
| 20. Concurrency | Real HTTP concurrency tests (2- and 3-way) plus in-process ones. | `tests/test_phase4.py` |
| 21. Telemetry anomaly detection | Five **rule-based** rules (no ML): `OUT_OF_RANGE`, `SUDDEN_BATTERY_DROP`, `SUDDEN_TEMPERATURE_JUMP`, `MODE_WITHOUT_COMMAND`, `STALE_REPORT`. Every finding carries the verdict and reason code of the accepted record it came from, so an anomaly is never reported as an authentication/authorisation failure. | `backend/engine.py`, `web/src/components/MetricsDashboard.tsx` |
| 22. Evidence filtering | `stage`, `since`, `until` added to `session`, `verdict`, `sender`, `message_type`, `reason`. `STAGE_REASONS`/`REASON_STAGE` map stages to deterministic reason sets so pagination stays accurate. | `backend/engine.py`, `backend/app.py` |
| 23. Signed evidence export | `/api/export` emits decisions + audit-chain verification. | `backend/app.py` |
| 24. Deterministic reset | `reset_demo()`; no session, record, chain link, or key is deleted or rotated. | `backend/engine.py` |

Three defects were caught during this phase:

1. `metrics()` counted every session → isolated suite statistics leaked into the live
   dashboard. Fixed by defaulting `scope` to the active session.
2. A latent typo in uncommitted code (`first_failures` referenced as
   `first_failed_stages`) → `NameError`. Fixed.
3. **A real security regression I introduced:** wrapping `receiver.audit(...)` in a
   broad `except ValueError → HTTPException(400)` would have swallowed storage and
   parse failures that must surface as a bounded `503 SERVICE_ERROR`. Fixed by
   validating `stage`/`since`/`until` explicitly and letting storage errors propagate.
   Regression test: `test_corrupt_audit_record_is_service_error_not_leaked`.

---

## Runtime-data incident (disclosed)

During Phase 3/4 verification a server was started once **without** `KAVACH_DATA_DIR`,
so it wrote extra sessions and audit events into the repository's runtime database.

- **Nothing was erased, overwritten, or rotated.** The signing keys were verified
  byte-identical before and after.
- The shipped state was restored from a backup taken before migration: 1 session,
  3 audit events. The original session and all 3 original events are intact.
- **Guard added:** `tests/test_runtime_isolation.py` (5 tests) fails if any source
  constructs an `Engine` on a non-isolated path, if the acceptance runner falls back to
  the repository data directory, if runtime data becomes git-tracked, or if an
  engine/receiver/client fixture is not isolated from `tmp_path`. The guard was
  verified by reintroducing the exact mistake and confirming it fails.

---

## Current state

| Item | Value |
|---|---|
| Branch | `feature/roadmap-24-completion` |
| Latest commit | see `git log --oneline` |
| Python tests | **228 passed, 1 skipped** |
| Editor gate | **12/12** |
| CSV gate | **10/10** |
| Frontend build | **PASS** |
| Runtime scenarios | **31/31** |
| Acceptance scenario | **9/9** |
| Browser tests | **54 checks passing** — visual design 38/38, smoke 16/16, hardening 30/30, design 8/8 |
| Live runtime data | 1 session, 3 audit events, 3 keys, state schema v2 |

The 1 skipped test is `tests/test_release.py`'s release-ZIP gate, skipped by design.


---

## Design restyle in the Linear language

After the roadmap work, the frontend was restyled in the Linear design language rather
than rebuilt. Every one of the 337 class names used by the React tree is covered by the
new `web/src/tokens.css` and `web/src/styles.css`; no class was renamed and no TSX logic
changed. The previous palette, DM Sans/IBM Plex Mono, 7px radius and copper accent are
gone, and `web/src/mission.css` is a retirement stub. `DESIGN.md` documents the new system.

Two hues (`--danger`, `--warn`) are added beyond the spec's single accent, because a
security console must say "this failed a check" and a marketing page never has to. They
are used only for verdicts, never decoration, and the deviation is recorded in
`tokens.css` and `DESIGN.md`. A stage that never ran stays neutral rather than amber or
red.

### Browser verification, previously blocked, now real

Playwright 1.64.0 and Chromium were installed, which closed the finding that all three
browser scripts exited with a `BLOCKED:` message. They now execute and pass:
visual design 38/38, smoke 16/16, hardening 30/30, design 8/8, with zero uncaught page
errors. The three scripts had rotted against the current UI — stale nav labels, a stale
export-button label, an assertion looking for exact prose, and two elements sharing a
class — and were fixed rather than loosened.

`tests/visual_design.py` is new. It reads computed styles off the live DOM so it proves
the tokens are applied rather than merely written, and asserts no horizontal overflow and
correct nav collapse at five viewports.

### Defects found by that verification

1. `verdict-banner` classes were mismatched — the JSX writes `accepted`/`rejected`/
   `service-error` but the CSS targeted `has-accepted`/`has-rejected`/`has-error`, so no
   verdict tint rendered at all.
2. `.nav-toggle` needed `.icon-btn.nav-toggle`; without it the hamburger was visible at
   every viewport, causing ~137px of horizontal overflow at 1440px.
3. Four class names were styled but never matched the JSX (`stage-index` vs
   `step-index`, `metric-note` vs `metrics-note`, plus `timeline-page` and `session-item`).
4. The mobile breakpoint had to reset `flex-wrap:nowrap`. With wrap, column flex items
   stretch to the widest item on the line instead of the container, overflowing by 33px
   at 320px.
5. The eight-destination nav did not fit between 1280 and 1440px. Labels were shortened
   and the collapse point moved to 1200px.

### Runtime data was modified a second time — disclosed

`browser_smoke.py` and `browser_hardening.py` defaulted to a hard-coded
`http://127.0.0.1:8000`. Running them while the app was up wrote 25 sessions and 236
audit events into the live database. Nothing was erased or rotated; the shipped state was
restored from the pre-modification backup.

The original isolation guard did not catch this, because it only inspects `Engine(...)`
calls in Python source, not a test reaching a live server over HTTP. Both are now fixed:
the browser scripts start their own server on a temporary data directory
(`tests/_isolated_server.py`), and the guard fails if any browser script reintroduces a
fixed local URL. The new rule was verified by reintroducing the pattern and confirming the
test fails.

Live runtime data afterwards: 1 session `KVC-1728F0A5`, 3 audit events, 3 keys, schema
v2, `data/` 0700, files 0600.
