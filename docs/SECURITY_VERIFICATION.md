# Security Verification

Every result in this document comes from an actual execution. Nothing is projected.
Each section names the test that produced it.

---

## 1. The eight acceptance tests

Executed by `tests/acceptance_scenario.py` against a **live FastAPI server on an
isolated temporary data directory**. Result: **9/9 PASS** (8 acceptance tests plus the
initial-state precondition).

| # | Test | Expected | Observed |
|---|------|----------|----------|
| — | Initial state | `NORMAL` / interval 10 / no telemetry | `NORMAL` / `10` / no telemetry |
| 1 | Valid command | ACCEPTED / OK / all stages PASS / mode `POWER_SAVING` / replay advances / audit persists | ACCEPTED / OK / 8/8 PASS / mode `POWER_SAVING` / replay advanced / audit persisted |
| 2 | Tampered command | REJECTED / `AUTH_FAILED` / auth FAIL / later NOT_RUN / mode unchanged | REJECTED / `AUTH_FAILED` / auth FAIL / later NOT_RUN / mode `POWER_SAVING` |
| 3 | Replay attack | REJECTED / `REPLAY` / replay stage FAIL / mode unchanged | REJECTED / `REPLAY` / replay stage FAIL / mode `POWER_SAVING` |
| 4 | Unauthorised command | auth PASS / authorization FAIL / `NOT_AUTHORISED` | auth PASS / authorization FAIL / `NOT_AUTHORISED` |
| 5 | Telemetry | ACCEPTED / telemetry changes / protected mode unchanged | ACCEPTED / telemetry changed / mode `POWER_SAVING` |
| 6 | Concurrency | exactly one ACCEPTED, other REPLAY, one state transition | `['ACCEPTED','REJECTED']` / `['OK','REPLAY']` / 1 transition |
| 7 | Database failure | `SERVICE_ERROR` / no execution claimed / no state mutation / no false audit | `SERVICE_ERROR` / state unchanged / audit rows 0 / persisted `False` |
| 8 | Audit integrity | unmodified VERIFIED / modified FAILED with explanation | clean `VERIFIED` / tampered `FAILED ['RECORD_MODIFIED']` |

Reproduce:

```
.venv/bin/python tests/acceptance_scenario.py
```

Test 3 note: the brief allows `EXPIRED` as a correct outcome when time precedes the
replay. The pipeline evaluates freshness before replay, so an expired fixture yields
`EXPIRED`, never `REPLAY`. Both are correct; the stage order is never rearranged to
produce a preferred verdict.

---

## 2. Tamper detection

`sign()` is HMAC-SHA256 over `canonical()`, which excludes `auth_tag`. Verification uses
`hmac.compare_digest`, so it is not short-circuitable by timing.

`tests/test_phase2.py::TestAuditChain` covers four tamper classes against a real
database:

| Tamper | Result | Detail |
|---|---|---|
| Edit a covered field of a persisted record | `FAILED / RECORD_MODIFIED` | "The persisted audit record no longer matches its chained contents. A covered field was altered after commit." |
| Delete a chain link | `FAILED / BROKEN_LINK` | The following record's `prev_hash` no longer resolves. |
| Renumber links | `FAILED / BROKEN_LINK` | Sequence no longer matches the hash order. |
| Delete the audit row | `FAILED / ORPHAN_LINK` | A chain entry exists with no corresponding record. |
| Unmodified chain | `VERIFIED, links: N, problems: []` | — |
| Legacy database (pre-migration, no chain) | `VERIFIED, links: 0, uncovered_records: 1` | Reported explicitly, not silently. |

The record used for the `RECORD_MODIFIED` check must actually differ from the stored
value. Mutating a record that already reads `ACCEPTED`/`OK` is a no-op and proves
nothing — that mistake was made once during development and is the reason the acceptance
scenario now rewrites `protected_state_after`.

---

## 3. Protected-state protection

Rejection returns before any protected write. The pipeline runs inside a single
`BEGIN IMMEDIATE` transaction and rolls back on `sqlite3.Error`.

| Injected failure | Verdict | `audit_persisted` | State | Rows |
|---|---|---|---|---|
| Commit failure | `SERVICE_ERROR` | `False` | unchanged | 0 everywhere |
| Audit-write failure | `SERVICE_ERROR` | `False` | unchanged | 0 everywhere |
| Lock contention | `SERVICE_ERROR` (HTTP 503) | `False` | unchanged | 0 everywhere |
| Corrupt audit record (read path) | raises; API surfaces bounded `SERVICE_ERROR` | — | unchanged | — |

The lock-contention case is verified over HTTP in
`tests/test_phase4.py::TestFaultInjectionBoundaries::test_lock_contention_is_bounded`,
which holds a `BEGIN IMMEDIATE` transaction and asserts the API returns 503 rather than
hanging.

A successful retry after an injected failure works, which confirms the rollback leaves
the database usable rather than corrupt.

---

## 4. Concurrency

Exercised through the real HTTP surface, not just in-process.

`tests/test_phase4.py::TestConcurrencyOverHttp`:

| Submissions | Verdicts | Reasons | Transitions | Streams | Accepted rows | Chain |
|---|---|---|---|---|---|---|
| 2 identical, released on a barrier | `ACCEPTED`, `REJECTED` | `OK`, `REPLAY` | 1 | 1 | 1 | `VERIFIED` |
| 3 identical, released on a barrier | `ACCEPTED`, `REJECTED`, `REJECTED` | `OK`, `REPLAY`, `REPLAY` | 1 | 1 | 1 | `VERIFIED` |

Exactly one acceptance, exactly one committed state transition, and the chain still
verifies afterwards.

---

## 5. Authorization

`tests/test_phase2.py::TestRolePolicy::test_default_roles_reproduce_baseline_authorisation`
asserts this truth table:

| Sender | Role | Action | Outcome |
|---|---|---|---|
| `observer-01` | VIEWER | `COMMAND/GET_STATUS` | allowed |
| `observer-01` | VIEWER | `COMMAND/SET_MODE` | **denied** |
| `observer-01` | VIEWER | `TELEMETRY/TELEMETRY_STATUS` | **denied** |
| `operator-01` | OPERATOR | `COMMAND/GET_STATUS` | allowed |
| `operator-01` | OPERATOR | `COMMAND/SET_MODE` | allowed |
| `operator-01` | OPERATOR | `COMMAND/SET_REPORT_INTERVAL` | allowed |
| `operator-01` | OPERATOR | `TELEMETRY/TELEMETRY_STATUS` | **denied** |
| `satellite-01` | TELEMETRY_SOURCE | `TELEMETRY/TELEMETRY_STATUS` | allowed |
| `satellite-01` | TELEMETRY_SOURCE | `COMMAND/SET_MODE` | **denied** |
| `satellite-01` | TELEMETRY_SOURCE | `COMMAND/GET_STATUS` | **denied** |
| `intruder-99` | — | any | **denied** |

The distinct `TELEMETRY_SOURCE` role exists because an earlier cut granted `OPERATOR`
the telemetry action, which broke
`test_humans_cannot_publish_telemetry_satellite_cannot_command`.

**The policy is server-authoritative.** No message field can grant a role;
`permitted()` reads the `policy` table.

---

## 6. Policy administration boundary

`POST /api/policy/roles/{role}` returns **403** with this detail unless
`KAVACH_ALLOW_POLICY_ADMIN=1` is set on a trusted loopback launch:

> Policy administration is disabled. This is a local administrative boundary, not public
> authorization; set KAVACH_ALLOW_POLICY_ADMIN=1 on a trusted loopback launch to enable
> it.

Invalid role/kind/action → **422** and nothing is written. Every accepted change is
versioned, attributed, audited, and chained.

---

## 7. Secret handling

Verified in `tests/test_phase4.py::TestCsvExport`:

- No signing key **value** from `sender-secrets.json` appears in any API response.
- The key file itself is not retrievable through any endpoint.
- CSV export contains no secret material.

**Deliberate and documented:** `auth_tag` *does* appear in the persisted record and in
`submitted_text`. It is an HMAC-SHA256 tag over public envelope fields, not a secret
key, and the receiver needs it to demonstrate byte-exact replay. It is not one of the
exported CSV columns. `key_id` values such as `operator-key-01` are public labels.

The fixture issuer is never exposed publicly: the UI shows fixture JSON only after an
explicit user action, and the issuer is not bound to an externally reachable interface.

---

## 8. Audit chain design and its limits

`record_hash = SHA256(prev_hash || 0x00 || canonical(covered_fields))`, genesis
`'0'*64`, ordered by `seq`, written in the same transaction as the audit row.

`CHAIN_COVERED_FIELDS` (17), corrected against the implementation during final
stabilization: `event_id`, `session_id`, `verdict`, `reason_code`, `sender`, `kind`,
`received_at`, `input_sha256`, `sender_verified`, `state_changed`,
`replay_state_advanced`, `protected_state_before`, `protected_state_after`,
`telemetry_before`, `telemetry_after`, `checks`, `policy_version`.
The earlier list incorrectly named `explanation` and `audit_persisted`. Those fields
are not covered. Raw message display fields are not independently covered either;
the input hash is covered. Do not infer whole-record attestation from VERIFIED.

**What it detects:** modification of covered record contents; broken links; missing
intermediate records.

**What it does not do, stated by `verify_audit_chain()` itself:**

- It does not prove origin.
- It does not prevent an attacker with write access from rewriting the entire chain
  from genesis.
- It is **not tamper-proof**, and KAVACH never claims otherwise.

Verification is strictly read-only. It never repairs, rewrites, or deletes anything.

---

## 9. Claims this software does not make

- It is not "tamper-proof".
- It is not "production-certified".
- It is not a real spacecraft command interface; it is a local synthetic simulator.
- Anomaly detection is **rule-based**, not machine learning.
- Anomaly findings are never reported as authentication or authorisation failures; each
  finding carries the verdict and reason code of the accepted record it came from, and
  the response includes the disclaimer "NOT proof of malicious activity".
