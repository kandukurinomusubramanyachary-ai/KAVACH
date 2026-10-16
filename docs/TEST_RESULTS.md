# Test Results

All figures below were produced by the commands shown. Nothing is estimated,
extrapolated, or carried over from a previous run.

Last full run: **2026-10-16**, branch `feature/roadmap-24-completion`.

---

## Gate summary

| Gate | Command | Result |
|---|---|---|
| Python suite | `.venv/bin/python -m pytest -q` | **228 passed, 1 skipped** |
| Editor | `npm run test:editor` | **12 / 12 pass** |
| CSV serialisation | `npm run test:csv` | **10 / 10 pass** |
| Frontend build | `npm run build` | **PASS** |
| Runtime scenarios | `.venv/bin/python -m scripts.run_scenarios` | **31 / 31 pass** |
| Acceptance scenario | `.venv/bin/python tests/acceptance_scenario.py` | **9 / 9 pass** |
| Browser smoke | `.venv/bin/python tests/browser_smoke.py` | **16 / 16**, zero JS errors |
| Browser hardening | `.venv/bin/python tests/browser_hardening.py` | **30 / 30**, zero JS errors |
| Browser design | `.venv/bin/python tests/browser_design.py` | **8 / 8** |
| Visual design | `.venv/bin/python tests/visual_design.py` | **38 / 38** |

All four browser scripts start their own isolated server on a temporary data directory, so
they cannot read or write the live runtime database. `KAVACH_URL` overrides this only when a
server is deliberately pointed at by hand.

### The one skipped test

`tests/test_release.py` skips the release-ZIP gate by design. It is not a failure and
must not be reported as one.

### The browser gates, previously blocked, now run

Playwright 1.64.0 and Chromium are installed, so all four scripts execute against a real
server and a real browser. The historical "30 browser-hardening assertions" claim is now
supported rather than withdrawn: `browser_hardening.py` reports 30/30.

The earlier caveat still carries a lesson: `browser_smoke.py` historically exited **0**
while reporting a `BLOCKED:` message, and that exit code must **not** be read as success.
Read the reported counts, never the exit code.

`tests/visual_design.py` is new. It asserts computed styles from the live DOM — canvas,
surface ladder, hairline colour, radii, button heights, type scale and tracking, both
vendored font families, and the danger tint on a rejected verdict — plus no horizontal
overflow and correct nav collapse at five viewports. It writes full-page screenshots for
all eight pages at three viewports into `reports/design/`.

Not covered: only Chromium is exercised. Firefox, WebKit and screen readers are not
verified.

---

## Test files

| File | Tests | Covers |
|---|---|---|
| `tests/test_engine.py` | — | Signature generation/verification, canonicalisation, expiry, ordering, state rules |
| `tests/test_api.py` | — | HTTP surface, request-body cap, fixture issuance |
| `tests/test_hardening.py` | — | Lock contention, audit-write failure, commit failure, restart durability |
| `tests/test_release.py` | 1 skipped | Release-ZIP gate (skipped by design) |
| `tests/test_phase1.py` | 16 | State migration, three required attack presets, model rules |
| `tests/test_phase2.py` | 34 | Chain construction, four tamper classes, fail-closed atomicity, restart durability, role truth table, admin gate |
| `tests/test_phase3_backend.py` | 34 | Metrics, anomaly rules, evidence filtering |
| `tests/test_phase4.py` | 22 | Deterministic reset, HTTP concurrency, boundary inputs, CSV data integrity |
| `tests/test_runtime_isolation.py` | 5 | Guard: no test may touch the live runtime database |
| `tests/test_frontend_gates.py` | 5 | `npm run test:editor` regression (DEFECT-01) |
| `tests/acceptance_scenario.py` | 9 | The eight roadmap acceptance tests against a live server |

`tests/test_phase4.py` also asserts that `SCENARIO_CASE_COUNT` equals the number of
cases the suite actually executes, and that every receiver stage except `commit` is
exercised by at least one case.

---

## Runtime scenario suite — 31 cases

`.venv/bin/python -m scripts.run_scenarios` runs every case in a temporary directory
and asserts the isolated active state is unchanged afterwards.

| Category | Cases |
|---|---|
| Structure | Missing required field; unknown envelope field; boolean is not integer; duplicate JSON key; invalid payload range; oversized body |
| Identity | Unknown key |
| Authentication | Bad authentication tag; malformed JSON |
| Payload | Unknown action; unknown target |
| Freshness | Expired message; future timestamp (clock skew) |
| Authorization | Unauthorised mode command |
| Replay | Duplicate submission; out-of-order sequence; replay after restart |
| Commit | Database commit failure rollback; database audit failure rollback |
| Durability | Engine restart preserves replay protection |
| Storage | Corrupt storage surfaces as an error |

The two cases added in Phase 4 (oversized body, corrupt storage) close the last gaps
against the roadmap's fault-injection list.

---

## Acceptance scenario detail

`tests/acceptance_scenario.py` starts a real server with `KAVACH_DATA_DIR` pointed at a
`tempfile.TemporaryDirectory`, so the live runtime database is never opened. It prints
a table and exits non-zero on any failure.

Observed output:

```
TEST  NAME                  RESULT OBSERVED
------------------------------------------------------
Setup Initial state         PASS   NORMAL / 10 / no telemetry
1     Valid command         PASS   ACCEPTED / OK / 8/8 PASS / mode POWER_SAVING / replay advanced / audit persisted
2     Tampered command      PASS   REJECTED / AUTH_FAILED / auth FAIL / later NOT_RUN / mode POWER_SAVING / replay unchanged / audit persisted
3     Replay attack         PASS   REJECTED / REPLAY / replay stage FAIL / mode POWER_SAVING / replay state unchanged
4     Unauthorised command  PASS   auth PASS / authorization FAIL / NOT_AUTHORISED / mode POWER_SAVING / replay unchanged
5     Telemetry             PASS   ACCEPTED / telemetry changed / mode POWER_SAVING
6     Concurrency           PASS   ['ACCEPTED', 'REJECTED'] / ['OK', 'REPLAY'] / 1 transition(s)
7     Database failure      PASS   SERVICE_ERROR / state unchanged / audit rows 0 / persisted False
8     Audit integrity       PASS   clean VERIFIED / tampered FAILED ['RECORD_MODIFIED'] / 4 limitations stated

9/9 acceptance tests passed.
```

---

## Metrics from a real isolated run

`tests/test_phase3_backend.py` records these actual values from a smoke run on an
isolated database (30 messages checked):

| Counter | Value |
|---|---|
| `messages_checked` | 30 |
| `accepted` | 8 |
| `rejected` | 22 |
| `replay_attempts_detected` | 3 |
| `first_failed_stages` | authentication 3, identity 7, permissions 6, replay 2, structure 1 |
| Suite cases | 29 / 29 passed (before the suite grew to 31) |
| `protected_state_integrity_violations` | 0 |
| `anomalies.finding_count` | 0 |

These are measurements, not targets. The UI reads the same endpoint at runtime and
never hardcodes a counter.

---

## What is NOT verified

| Item | Status |
|---|---|
| Browser rendering and interaction | Chromium only — 54 checks passing. Firefox, WebKit and screen readers are **NOT RUN**. |
| The public tunnel URL | Verified once, end-to-end, during development. Cloudflare quick tunnels have no uptime guarantee; treat as unavailable unless re-verified. |
| Any performance or load characteristic | **NOT RUN** — never measured, never claimed. |
| Behaviour under a real network adversary | **NOT RUN** — the tunnel is a convenience, not a security boundary. |
| Cryptographic key rotation | **NOT RUN** — and by Rule 5 it must never be exercised against the live keys. |
