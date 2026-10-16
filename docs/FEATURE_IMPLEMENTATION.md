# Feature Implementation Map

All 24 roadmap features, the files that implement each one, the test that verifies it,
and the observed result. Every result is from a real execution on
2026-10-16, branch `feature/roadmap-24-completion`.

Legend — **PASS** executed and passed · **BLOCKED** could not be executed in this
environment · **NOT RUN** deliberately not exercised.

---

## Priority 0 — Foundation

| # | Feature | Files | Test | Result |
|---|---|---|---|---|
| — | Baseline audit of all 24 features | `docs/ROADMAP_BASELINE_AUDIT.md` | manual review | **PASS** |

---

## Priority 1 — Mission Control + Attack Lab

| # | Feature | Implementing files | Acceptance test | Actual result |
|---|---|---|---|---|
| 1 | Show telemetry and protected state | `web/src/main.tsx`, `backend/engine.py` | `tests/acceptance_scenario.py` Test 5 | **PASS** — telemetry changes, protected mode stays `POWER_SAVING` |
| 2 | Compose and submit a message | `web/src/main.tsx`, `web/src/editor.ts` | `npm run test:editor` | **PASS** — 12/12 |
| 3 | Attack presets | `backend/app.py`, `web/src/main.tsx` | `tests/test_phase1.py` | **PASS** — `unknown_key`→`KEY_UNKNOWN`, `bad_tag`→`AUTH_FAILED`, `malformed`→`INVALID_JSON` with `raw_text` |
| 4 | Visual validation pipeline | `web/src/components/ValidationPipeline.tsx` | `tests/acceptance_scenario.py` Tests 1–4 | **PASS** — PASS/FAIL/NOT RUN all observed |

**Phase 1 additions**

- Versioned state migration: `STATE_SCHEMA_VERSION=2`, `_migrate_state()`,
  `MODEL_RULES`, `ANTENNA_STATES`. Verified on a **copy** of the live database first;
  values and all 3 audit events preserved, key file byte-identical.
- `antenna_status` / `power_level_pct` are **not** envelope fields. A message carrying
  them is `SCHEMA_INVALID` — asserted in `tests/test_phase1.py`.
- `INITIAL` = `{"mode":"NORMAL","report_interval_s":10,"antenna_status":"NOMINAL","power_level_pct":87}`.

---

## Priority 2 — Security depth + evidence integrity

| # | Feature | Implementing files | Acceptance test | Actual result |
|---|---|---|---|---|
| 5 | Replay protection | `backend/engine.py` | Acceptance Test 3 | **PASS** — REJECTED / `REPLAY` |
| 6 | Unauthorized sender handling | `backend/engine.py` | Acceptance Test 4 | **PASS** — auth PASS, authz FAIL, `NOT_AUTHORISED` |
| 7 | Tampered message detection | `backend/engine.py` | Acceptance Test 2 | **PASS** — REJECTED / `AUTH_FAILED` |
| 8 | State protection | `backend/engine.py` | Acceptance Tests 2,3,4,7 | **PASS** — mode unchanged in every rejection |
| 9 | Tamper-evident audit | `backend/engine.py`, `backend/app.py` | Acceptance Test 8, `tests/test_phase2.py` | **PASS** — clean `VERIFIED`; four tamper classes `FAILED` |
| 10 | Server-authoritative policy | `backend/engine.py`, `backend/app.py` | `tests/test_phase2.py::TestRolePolicy` | **PASS** — 11-case truth table |

**Chain:** `record_hash = SHA256(prev_hash ‖ 0x00 ‖ canonical(covered_fields))`, genesis
`'0'*64`, ordered by `seq`, written in the same transaction as the audit row. 17
covered fields. Limits are returned by `verify_audit_chain()` and shown in the UI.

**Policy:** `policy` table, `role_for()`, `permitted()`, `policy_version()`,
`set_role_permissions()`. The admin endpoint is **403** by default. A distinct
`TELEMETRY_SOURCE` role exists because an earlier cut gave `OPERATOR` the telemetry
action.

---

## Priority 3 — Judge experience

| # | Feature | Implementing files | Acceptance test | Actual result |
|---|---|---|---|---|
| 11 | Attack timeline | `web/src/components/AttackTimeline.tsx` | `npm run build` + Acceptance Tests 1–4 | **PASS** — NOT RUN shown for skipped stages; no per-stage duration invented |
| 12 | Normal vs attack comparison | `web/src/components/ComparisonView.tsx` | `npm run build` | **PASS** — both columns are real submissions |
| 13 | Metrics dashboard | `web/src/components/MetricsDashboard.tsx`, `backend/engine.py` | `tests/test_phase3_backend.py` | **PASS** — every counter from `GET /api/metrics` |
| 14 | Guided demo | `web/src/components/GuidedDemo.tsx` | `docs/DEMO_SCRIPT.md` | **PASS** — ~105 s, user-triggered |
| 15 | Before/after state display | `web/src/main.tsx`, `ComparisonView.tsx` | Acceptance Tests 1–5 | **PASS** |
| 16 | CSV export | `web/src/csv.ts`, `web/src/main.tsx` | `npm run test:csv`, `tests/test_phase4.py::TestCsvExport` | **PASS** — 10/10 unit, data integrity asserted |
| 17 | Protected-state invariants | `web/src/components/MetricsDashboard.tsx` | `tests/test_phase3_backend.py` | **PASS** — `protected_state_integrity_violations` from real rows |
| 18 | Reproducible sessions | `backend/app.py`, `backend/engine.py` | `tests/test_phase4.py::TestDeterministicReset` | **PASS** — reset preserves history and keys |

**Defect fixed here:** the hardcoded `MiniSpark` SVG presented a static curve in a
security UI while being derived from nothing. Removed; the dashboard reads real metrics.

**Metrics scope:** `scope` is `live session` by default. Suite statistics live under
`scenario_suites` and cannot leak into live counters, because suite runs write into
their own isolated session.

---

## Priority 4 — Advanced engineering

| # | Feature | Implementing files | Acceptance test | Actual result |
|---|---|---|---|---|
| 19 | Fault injection | `backend/engine.py`, `tests/test_phase4.py` | `.venv/bin/python -m scripts.run_scenarios` | **PASS** — 31/31 |
| 20 | Concurrency | `backend/engine.py`, `tests/test_phase4.py` | Acceptance Test 6 | **PASS** — exactly one ACCEPTED, one transition, chain `VERIFIED` |
| 21 | Anomaly detection | `backend/engine.py`, `MetricsDashboard.tsx` | `tests/test_phase3_backend.py` | **PASS** — 5 rules, thresholds returned |
| 22 | Evidence filtering | `backend/engine.py`, `backend/app.py` | `tests/test_phase3_backend.py` | **PASS** — stage + time range added |
| 23 | Signed evidence export | `backend/app.py` | `tests/test_phase4.py::TestCsvExport` | **PASS** — JSON export verifies |
| 24 | Deterministic reset | `backend/engine.py` | `tests/test_phase4.py::TestDeterministicReset` | **PASS** — deterministic, history and keys preserved |

**Fault-injection coverage vs the roadmap list:**

| Roadmap case | Status |
|---|---|
| Missing fields | covered |
| Unexpected fields | covered |
| Incorrect types | covered (boolean as integer) |
| Duplicate JSON keys | covered |
| Invalid numeric ranges | covered |
| Oversized payloads | **added in Phase 4** |
| Unknown commands | covered |
| Unknown senders | covered |
| Expired timestamps | covered |
| Clock skew | covered |
| SQLite lock contention | covered |
| Audit write failures | covered |
| Transaction commit failures | covered |
| Corrupt storage | **added in Phase 4** |
| Restart behavior | covered |

**Anomaly rules:** `OUT_OF_RANGE`, `SUDDEN_BATTERY_DROP` (>30 pts),
`SUDDEN_TEMPERATURE_JUMP` (>40 °C), `MODE_WITHOUT_COMMAND`, `STALE_REPORT`. Ranges:
`battery_pct (0,100)`, `temperature_c (-50,120)`. Each finding carries the verdict and
reason code of the accepted record it came from. Rejected messages never produce
findings. Response includes the disclaimer "NOT proof of malicious activity".

**Filtering:** `STAGE_REASONS` maps each stage to its deterministic reason-code set;
`REASON_STAGE` is the inverse. Every returned event carries `first_failed_stage`.

---

## Not verified

| Item | Status | Why |
|---|---|---|
| Browser rendering and interaction | **BLOCKED** | No Playwright, no Chromium. See `docs/REMAINING_RISKS.md` R1. |
| Performance or load | **NOT RUN** | Never measured. No figure is claimed. |
| Key rotation | **NOT RUN** | Forbidden by Rule 5. |

---

## Mission success criteria

| Criterion | Where proven |
|---|---|
| 1. Legitimate synthetic commands accepted | Acceptance Test 1 |
| 2. Tampered messages fail authentication | Acceptance Test 2 |
| 3. Replayed messages rejected | Acceptance Test 3 |
| 4. Unauthorized senders denied even when authenticated | Acceptance Test 4 |
| 5. Rejected messages cannot modify protected state | Acceptance Tests 2,3,4,7 |
| 6. Every decision explainable | `explanation`, per-stage `checks`, `first_failed_stage` |
| 7. Audits persist and integrity is checkable | Acceptance Test 8, `GET /api/audit/verify` |
| 8. Test outcomes from real executions | `docs/TEST_RESULTS.md` |
| 9. Judge understands without reading source | `docs/DEMO_SCRIPT.md`, Guided Demo |
| 10. All features operate together reproducibly | `tests/acceptance_scenario.py` — 9/9 |
