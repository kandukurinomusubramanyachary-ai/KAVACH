# Remaining Risks and Known Limitations

Everything listed here is a real, current limitation of this build. None of it is
hidden by the UI. Items are ordered by how likely they are to matter to a reviewer.

---

## R1 — CLOSED: browser verification now runs for real

Previously blocked because `playwright` was not installed and no Chromium binary
existed, so all three browser scripts exited with a `BLOCKED:` message. Playwright
1.64.0 and Chromium are now installed and the scripts execute end to end.

| Script | Result |
|---|---|
| `tests/visual_design.py` | 38/38 design checks |
| `tests/browser_smoke.py` | 16/16, zero uncaught page errors |
| `tests/browser_hardening.py` | 30/30 checks, zero uncaught page errors |
| `tests/browser_design.py` | 8/8 checks |

The historical caveat that `browser_smoke.py` exits 0 even when blocked no longer
applies, but the underlying lesson does: read the reported counts, never the exit
code.

**What is still not covered by these gates:** only Chromium is exercised. Firefox and
WebKit rendering, and any browser other than the installed Chromium build, are
untested. Screen readers and keyboard-only navigation beyond the modal focus
containment check are not verified.

---
## R2 — The audit chain cannot detect a full rewrite from genesis

The chain links each record to its predecessor. An attacker with write access to the
database can recompute every hash from a new genesis and produce a chain that verifies.

`verify_audit_chain()` returns this as an explicit limitation, and the UI displays it.
KAVACH never claims "tamper-proof".

**Partial mitigation available:** an external anchor (a signed, periodically published
root hash) would detect full rewrites. It is not implemented, because it introduces an
out-of-band dependency that this local simulator does not need.

---

## R3 — The chain does not prove origin

A verified chain proves the records are internally consistent and unchanged since they
were linked. It does not prove who wrote them or that the writer was the receiver.

This is a property of hash chains, not a defect. It is stated in the API response and
the UI.

---

## R4 — Secrets are held in a local JSON file

`data/sender-secrets.json` holds the three signing keys in plaintext, with the
directory at mode `0700` and the file at `0600`.

This is acceptable for a local simulator and is explicitly a non-goal to change (Rule 5
forbids rotating the existing keys). It is **not** acceptable for a real deployment,
which would need an HSM or a secrets manager.

**Note on `auth_tag`:** the tag appears in persisted records and in `submitted_text`.
It is an HMAC over public envelope fields, not a secret. The receiver needs it to
demonstrate byte-exact replay. No key *value* appears in any API response — this is
asserted in `tests/test_phase4.py`.

---

## R5 — `expires_at` and `issued_at` are signed, but wall-clock time is trusted

Freshness is evaluated against the receiver's clock with a 5-second permitted future
skew. A receiver with a wrong clock will misjudge freshness, and an attacker who can
set the receiver's clock can influence the `time` stage.

Clock synchronisation is out of scope for a local simulator.

---

## R6 — Concurrency is bounded by SQLite, not by a queue

Two simultaneous submissions are resolved by a `BEGIN IMMEDIATE` transaction with a
bounded wait. The tests confirm exactly-one-acceptance for 2-way and 3-way races.

Under sustained high concurrency the bounded wait will return `SERVICE_ERROR` rather
than queueing. That is the deliberate fail-closed choice, and it is the honest one for
this architecture — but it is a throughput limit, not a correctness one.

No load or throughput figure has ever been measured. None is claimed.

---

## R7 — The anomaly rules are rule-based and narrow

Five deterministic rules with published thresholds. They are not machine learning and
are not represented as such.

They detect only: out-of-range battery/temperature, a battery drop over 30 points, a
temperature jump over 40 °C, a mode change without a command, and a stale report. They
will not detect a subtle or novel attack. Every finding carries the verdict and reason
code of the accepted record it came from, plus the disclaimer that findings are "NOT
proof of malicious activity".

---

## R8 — Policy administration is gated, not authenticated

`POST /api/policy/roles/{role}` is disabled unless `KAVACH_ALLOW_POLICY_ADMIN=1` is set
on a trusted loopback launch. There is no separate authentication layer on top of that
flag.

This is sufficient for a local simulator and is documented as "a local administrative
boundary, not public authorization". A real deployment needs real authentication on
this surface.

---

## R9 — The public tunnel is a convenience, not a boundary

The Cloudflare quick tunnel used during development has **no uptime guarantee**. It was
verified end-to-end once; it should be treated as unavailable unless re-verified.

It is not a security control. It exposes the same local simulator to anyone with the
URL, which is why Rule 7 applies to sharing it.

The Arena preview panel is the supported way to view the app.

---

## R10 — Runtime data was modified twice during development

A server was started without `KAVACH_DATA_DIR`, writing extra sessions and audit events
into the repository's runtime database. Nothing was erased or rotated, and the shipped
state was restored from a pre-modification backup both times.

It happened a second time during the design restyle: `tests/browser_smoke.py` and
`browser_hardening.py` defaulted to a hard-coded `http://127.0.0.1:8000`, so running
them while the app was up wrote 25 sessions and 236 audit events into the live
database. The original guard did not cover that, because it only inspects `Engine(...)`
constructor calls in Python source, not a test that reaches a live server over HTTP.

Both events are disclosed in `docs/ROADMAP_PROGRESS.md`.

**Closure:** the three browser scripts now start their own server on a temporary data
directory via `tests/_isolated_server.py`, so they cannot reach the live runtime at all.
`tests/test_runtime_isolation.py` was extended to fail if any browser script reintroduces
a fixed local URL fallback, and the new rule was verified by reintroducing the pattern and
confirming the test fails.

**Residual risk:** the guard is a static check, so it catches the patterns it was written
for rather than every possible route to the live database. Nothing prevents a developer
from manually pointing a server at `data/`.

---
## R11 - CLOSED: release gate is mandatory

The final-stabilization suite builds/verifies a real temporary ZIP on every run.
Generated reports are excluded; omitted new sources fail the allowlist completeness
check. Clean installation/startup/security and Chromium-from-extraction are independent
release gates. See RELEASE_VERIFICATION.md for the final artifact and commands.

---

## R12 — The state model's derived fields are synthetic

`antenna_status` and `power_level_pct` are produced by `MODEL_RULES` from the mode. They
are documented as synthetic and are not settable by any message — a message carrying
them is `SCHEMA_INVALID`.

They should not be read as physical telemetry.

---

## How to re-verify anything in this document

| Claim | Command |
|---|---|
| Gates | see `docs/TEST_RESULTS.md` |
| Acceptance tests | `.venv/bin/python tests/acceptance_scenario.py` |
| Runtime isolation guard | `.venv/bin/python -m pytest tests/test_runtime_isolation.py -v` |
| Chain limits | `GET /api/audit/verify` — read `limitations[]` in the response |
| Policy gate | `POST /api/policy/roles/VIEWER` without the env flag → 403 |
| Metrics scope | `GET /api/metrics` — `scope` is `live session`; suite counts are under `scenario_suites` |

## Current verification limits (17 October 2026)

Final-stabilization evidence supersedes historical environment claims above; see
FINAL_TEST_RESULTS.md and CI_VERIFICATION.md. Local verification uses Windows,
Python 3.14 and Node 24. Linux CI targets Python 3.12 / Node 22. POSIX permissions
and OS symlink creation cannot run under this Windows account; both remain mandatory
on Linux. Archive-symlink rejection is separately exercised on every platform.

The design detector reports two Inter-font warnings; retaining the incumbent Inter
system is explicitly required by the brief. No new typeface or redesign was introduced.
Chromium is the tested engine. Firefox/WebKit, physical devices and screen-reader
certification remain unverified. Theme storage failure falls back to the current tab.

The standalone HTML is a separate eight-case JavaScript fallback, not the full Python
application. Backend-only panels fail with an explicit unavailable message there.
The complete judge workflow requires the supported local Python-served build.

Transitive Python dependencies use the constraints supplied by pinned direct packages;
this work did not introduce a platform-specific freeze or uncontrolled dependency upgrade.
Known-secret scanning does not replace an independent comprehensive secret audit.
No tunnel, deployment or external-host exception was enabled during stabilization.

Audit verification covers exactly the 17 `CHAIN_COVERED_FIELDS` published by the API.
Explanation text, `audit_persisted` and message-display fields are not independently
covered. The historical security report overstated that list and is corrected.
Changing the covered set would require a versioned migration, not a silent change to
existing chains. The tamper regression deliberately changes protected_state_after.
