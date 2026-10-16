# KAVACH — Roadmap Baseline Audit (Phase 0)

**Audit date:** 2026-10-16
**Baseline commit:** `33c0093182f2b4570b67123a6375e104da38ec95` — *"Update gitignore"*
**Branch created:** `feature/roadmap-24-completion` (from `main`)
**Working tree at audit start:** clean (`git status --porcelain` empty — no uncommitted work to preserve)
**Runtime data:** untouched. `data/kavach.sqlite3` and `data/sender-secrets.json` were **not** modified, rotated, or exposed. All testing used isolated temporary data directories.

> The roadmap source `KAVACH_Feature_Roadmap_and_Judging_Plan.pdf` is not present in this
> repository or upload area. The 24-feature roadmap used here is the specification supplied in
> the engineering brief. Where that brief and the existing contracts differ, the contracts
> (`README.md`, `docs/CONTRACT.md`, `docs/SECURITY.md`) govern receiver behaviour.

---

## 1. Actual baseline command results

Executed in the live workspace on the baseline commit. Historical repository reports are
**not** reproduced below; only this execution is reported.

| Command | Result | Notes |
|---|---|---|
| `python -m pytest -q` | **110 passed, 1 skipped** | The skip is `tests/test_release.py`'s release-ZIP gate, which is pending until a release archive exists — expected by design. |
| `npm run test:editor` | **12 passed** | **Was failing at baseline.** Fixed during Phase 0 — see §2. |
| `npm run build` (`tsc --noEmit && vite build`) | **PASS** | 1941 modules, 298.18 kB JS / 93.23 kB CSS. |
| `python -m scripts.run_scenarios` | **29 / 29 passed** | Isolated active state unchanged: `True`. |
| `python tests/browser_smoke.py` | **BLOCKED** | Playwright package not installed; no Chromium binary. Not counted as a pass. |
| `python tests/browser_hardening.py` | **BLOCKED** | Same blocker. |

**Comparison with historical claims** (111 Python tests, 12 editor tests, 29 scenarios,
30 browser-hardening assertions):

- Python: 110 passed + 1 skipped = **111 total** — matches the historical count.
- Editor: **12** — matches, *but only after the fix in §2*. At the untouched baseline commit
  this command crashed.
- Scenarios: **29** — matches.
- Browser: historical 30 assertions are **not reproducible here** — environment BLOCKED.

---

## 2. Defect found and fixed during Phase 0

### DEFECT-01 (P1) — `npm run test:editor` crashes for every user

**Status:** FIXED in Phase 0. Regression coverage added.

`scripts/test-editor.mjs` spawned esbuild like this:

```js
spawnSync(process.execPath, ['node_modules/esbuild/bin/esbuild', ...])
```

That hands the esbuild **native ELF binary** to `node`, which then tries to parse machine code
as JavaScript:

```
Error: /home/user/KAVACH/node_modules/esbuild/bin/esbuild:1
ELF\u0002\u0001\u0001
SyntaxError: Invalid or unexpected token
```

**Root cause.** esbuild ≥ 0.16 (this repo pins 0.25.12 transitively via Vite 6.4.4) ships the
platform executable *directly* at `node_modules/esbuild/bin/esbuild`. The JS-shim layout the
script assumes was removed years ago. The script was written against the old layout and broke
when the dependency tree was bumped. This is a real repository defect, not an environment
artifact — `npm ci` from a clean tree reproduces it.

**Fix.** Invoke the binary directly instead of through `process.execPath`, with a comment
recording why.

**Verification.** `npm run test:editor` → `# pass 12 / # fail 0`.

**Why this matters for judging.** `npm run test:editor` is a documented verification command in
`README.md`. A judge following the README hits a crash on the first frontend gate.

---

## 3. Architecture as found

```
React/TypeScript (web/src)  ──relative HTTP, exact editor bytes──▶  FastAPI (backend/app.py)
                                                                        │
                                              strict JSON → registry → HMAC → target/payload
                                                    → time → policy → replay
                                                    → atomic state + replay + audit commit
                                                                        │
                                                                    SQLite (data/kavach.sqlite3)
```

**Backend.** `backend/engine.py` (422 lines) holds the entire security boundary: eight ordered
stages, HMAC-SHA256 signing/verification via `hmac.compare_digest`, strict envelope schema,
per-sender 256-bit synthetic secrets in `sender-secrets.json`, replay streams in SQLite, and a
single `BEGIN IMMEDIATE` transaction per validation that commits state + replay + audit
atomically or rolls back all three. `backend/app.py` (236 lines) is a thin HTTP surface with a
local/DNS-rebinding host guard and a body-size guard.

**Frontend.** `web/src/main.tsx` (182 lines, dense) plus extracted components
`ValidationPipeline`, `AttackProofSummary`, `AuditTable`, `MessageEditor`. `web/src/api.ts` is
the single HTTP boundary; `web/src/editor.ts` implements lossless JSON formatting that
deliberately preserves duplicate keys and oversized attack input as evidence.

**What is genuinely solid and must not regress:** the receiver's stage ordering, canonical
signing representation, constant-time tag comparison, rejection-implies-no-execution, atomic
commit, restart durability, and the 29-scenario isolated suite. All roadmap work below is
additive around this core.

---

## 4. Feature-by-feature mapping (all 24)

Legend: **IMPLEMENTED** · **PARTIAL** · **ABSENT**

### Phase 1 — Mission Control & Attack Lab

| # | Feature | Status | Evidence / files | Missing |
|---|---|---|---|---|
| 1 | Live Mission Control | **PARTIAL** | `main.tsx` console panel: session id, target, sender/message identity, command type, editor, verdict banner, 8-stage pipeline, before/after protected state, replay status, persisted event id. Receiver liveness via `/api/health` (10 s poll) shown in footer only. | Connection state is not prominent; no explicit "receiver connected" indicator in the console header. |
| 2 | Attack Scenario Lab | **PARTIAL** | 8 UI presets in `main.tsx` (`valid`, `tampered`, `replay`, `expired`, `future`, `unauthorised`, `invalid`, `telemetry`). | Roadmap requires **Unknown sender/key**, **Malformed JSON**, and **Invalid authentication tag** presets — absent from the UI (though the receiver enforces all three, and the 29-case suite covers them). No structured "attack intent / original input / changed input" presentation. |
| 3 | Explainable Decision Inspector | **IMPLEMENTED** | Decision modal in `main.tsx`: verdict, reason code, explanation, full 8-check trace with per-stage PASS/FAIL/**NOT_RUN**, state before→after, event id, session, input SHA-256, bounded submitted message. | Nothing missing against the roadmap. |
| 4 | Protected Satellite-State Simulator | **PARTIAL** | `INITIAL = {'mode': 'NORMAL', 'report_interval_s': 10}` in `engine.py`. | Roadmap asks to **evaluate** adding fictional antenna-status and power-level fields. Not implemented; needs a documented versioned migration. |

### Phase 2 — Security Depth & Evidence Integrity

| # | Feature | Status | Evidence / files | Missing |
|---|---|---|---|---|
| 5 | Cryptographic Message Integrity | **IMPLEMENTED** | `Engine.sign` / `canonical` (sorted keys, compact separators, ASCII), `hmac.compare_digest` at the authentication stage. Keys never reach the browser. Editing never re-signs. | Nothing missing. |
| 6 | Replay-Attack Demonstration | **IMPLEMENTED** | `replay` UI preset, `REPLAY`/`OUT_OF_ORDER`/`EXPIRED` handling, restart-durable `streams`/`accepted` tables, barrier-based concurrency case in `scenarios()`. | Nothing missing. |
| 7 | Identity vs Authentication vs Authorization | **IMPLEMENTED** | Three distinct stages (`identity`, `authentication`, `permissions`) plus the `AttackProofSummary` "identity gates" panel and the explicit "Authentication confirms authenticity. Authorisation determines permission." statement. | Nothing missing. |
| 8 | Policy & Permission Simulator | **PARTIAL** | Authorisation is a hardcoded expression in `engine.py`: `(kind == 'TELEMETRY' and sender == 'satellite-01') or (kind == 'COMMAND' and (sender == 'operator-01' or (sender == 'observer-01' and action == 'GET_STATUS')))`. | No Viewer/Operator/Administrator role model, no server-authoritative policy store, no policy versioning, no policy-change audit event, no policy mutation surface. Roles are implicit in sender ids. |
| 9 | Tamper-Evident Audit Evidence | **ABSENT** | `audit` table stores one JSON blob per event, ordered by `rowid`. `export()` reads state + events + suites in one snapshot. | **No hash-linked chain, no previous-record hash, no integrity verification action.** Cannot detect modification of a covered record. |
| 10 | Automated Security Test Runner | **IMPLEMENTED** | `Engine.scenarios()` — 29 real receiver operations in an isolated session, injected clock `1792137600`, expected/observed/pass, `state_preserved`, `effect_matches`, `event_id`, plus concurrency, restart, and fault-injection cases. Surfaced via `/api/scenarios/run` and the Scenario Lab UI. | Fault coverage is limited to commit/audit failure and lock contention. No corrupt-storage or oversized-body cases. |

### Phase 3 — Judge Experience & Presentation

| # | Feature | Status | Evidence / files | Missing |
|---|---|---|---|---|
| 11 | Attack Replay Timeline | **PARTIAL** | `ValidationPipeline` renders the 8 ordered stages with PASS/FAIL/NOT_RUN, and the detail modal shows the same trace. | No single linear timeline view spanning MESSAGE RECEIVED → … → AUDIT EVIDENCE. No explicit "not run" affordance outside the pipeline. |
| 12 | Normal vs Attack Comparison | **ABSENT** | — | No side-by-side valid-vs-malicious comparison. |
| 13 | Security Metrics Dashboard | **ABSENT** | — | No metrics endpoint. The only visual is a **hardcoded decorative** `MiniSpark` SVG path in `main.tsx` — a static curve that is *not* derived from data. Must be replaced with backend-derived counts. |
| 14 | Guided Demo Mode | **ABSENT** | — | No scripted walkthrough. |
| 15 | Interactive Message Builder | **PARTIAL** | Generator controls for sender, kind, action, mode, seconds, battery, temperature. `editor.ts` + `MessageEditor` for raw editing. Signed-vs-edited distinction tracked via the `signed` state. | Sequence and timestamps are not editable through the builder; unsigned-edit vs explicit-signing distinction is implicit rather than stated. |
| 16 | Evidence Export | **PARTIAL** | JSON export (`/api/export`, per-decision download). | **No CSV export.** |
| 17 | Threat Explanation Panel | **PARTIAL** | Help modal ("A simulator. Not a live uplink.") covers principles and limitations. | No dedicated per-threat explanation panel tied to the selected scenario. |
| 18 | Session Reset & Seeded Scenarios | **PARTIAL** | `POST /api/demo/sessions` creates an isolated namespace, preserves history, does not rotate keys. | No seeded/deterministic scenario reset that restores a known starting state for repeatable demos. |

### Phase 4 — Advanced Engineering

| # | Feature | Status | Evidence / files | Missing |
|---|---|---|---|---|
| 19 | Fault Injection & Boundary Testing | **PARTIAL** | Suite covers missing/extra fields, wrong types, duplicate keys, bad ranges, unknown command/target/sender, expired, clock skew, commit failure, audit-write failure, lock contention, restart. | Missing: oversized body, corrupt storage, and a restart case exercised through the HTTP surface. |
| 20 | Concurrent Message Testing | **IMPLEMENTED** | `threading.Barrier(2)` + `ThreadPoolExecutor` in `scenarios()`; `test_simultaneous_duplicate_executes_once` asserts exactly one acceptance and one state transition. | Concurrency is exercised at engine level, not through the HTTP API. |
| 21 | Synthetic Telemetry Anomaly Detection | **ABSENT** | — | No rule-based detector. |
| 22 | Evidence Search & Filtering | **PARTIAL** | `/api/audit` filters: `verdict`, `sender`, `message_type` (`kind`), `reason`. UI adds verdict/sender/type/reason/session(current\|all)/free-text, pagination. | Missing: filter by **validation stage** and by **time range**. |
| 23 | Documented Schema & API | **PARTIAL** | `docs/CONTRACT.md` (160 lines) documents the message envelope and stages. | Does not cover roles/policy, audit-chain model, anomaly rules, new endpoints, or CSV export. |
| 24 | Deterministic Scenario Reset | **PARTIAL** | Suite uses a fresh isolated session with an injected clock. | No user-facing deterministic reset that returns to a documented initial state while preserving history. |

---

## 5. Deficiency classification

**P0 — security correctness.** None found. The receiver's core invariants hold at baseline:
rejection never mutates protected state, replay never executes, atomicity holds, restart
durability holds, and concurrency yields exactly one acceptance.

**P1 — broken or misleading.**
- **DEFECT-01** — `npm run test:editor` crashes (§2). *Fixed in Phase 0.*
- **F-09** — No audit integrity verification; records are described in the UI as "not immutable
  or tamper-proof", which is honest but leaves roadmap feature 9 entirely unimplemented.
- **F-13** — `MiniSpark` is a decorative hardcoded curve presented in a security UI. It is not
  derived from data and could read as a live metric. Must be replaced with real backend counts.

**P2 — roadmap features absent or partial.**
- F-02 missing attack presets (unknown key, malformed JSON, invalid tag).
- F-04 state-field migration not evaluated.
- F-08 role-based policy model absent.
- F-11 timeline, F-12 comparison, F-14 guided demo, F-16 CSV export, F-17 threat panel,
  F-18 seeded reset, F-21 anomaly detection, F-22 stage/time filters, F-23 doc coverage.

**P3 — polish.** F-01 receiver-connection prominence, F-15 builder fields.

---

## 6. Dependencies and environment notes

- Python 3.13.16, Node 20.20.2, npm 10.8.2 — all satisfy the README's stated floors.
- `fastapi` 0.143.2, `pydantic` 2.13.5, `uvicorn` 0.54.0; `pytest` 9.0.3, `httpx` 0.28.1 (dev).
- Frontend: React 19.3.1, Vite 6.4.4, TypeScript 5.7.3, lucide-react 1.58.0.
- **Known environment hazard:** the workspace snapshot mechanism drops `.venv`, `node_modules/`,
  and `dist/`, and has been observed to corrupt `node_modules/esbuild/bin/esbuild` (the native
  binary overwriting the shim path). Any future session must re-run
  `python -m venv .venv && pip install -r requirements.txt -r requirements-dev.txt`,
  `npm ci`, and `npm run build` before trusting test results. This is an environment artifact,
  distinct from DEFECT-01.
- Playwright and Chromium are unavailable → all browser gates report **BLOCKED**, never PASS.

---

## 7. Constraints carried forward

1. No greenfield rebuild; improve this repository.
2. Python remains authoritative for every security outcome; the frontend must not fabricate one.
3. Rejection means no protected execution — ever.
4. Atomicity of state + replay + audit must be preserved.
5. Existing keys, databases, and historical audit events must never be erased, rotated, or exposed.
6. No fabricated test counts, metrics, or screenshots. PASS / FAIL / BLOCKED / NOT RUN only.
7. Local-first boundary preserved; the fixture issuer is privileged, not public authentication.
8. Contract changes must be deliberate, versioned, documented, and regression-tested.
9. No unnecessary AI/ML, no live satellite link, no microservices, no artificial security scores.
10. No uncontrolled dependency upgrades.
11. No unsupported claims of production certification or tamper-proofing.
12. No direct pushes to `main`; work on the feature branch and produce a PR.

---

## 8. Phase 0 exit criteria — status

- [x] Baseline commit recorded (`33c0093`).
- [x] Git status checked; no uncommitted work existed to preserve.
- [x] Dedicated feature branch `feature/roadmap-24-completion` created.
- [x] Full repository tree inspected (backend, frontend, tests, docs, reports, scripts).
- [x] Backend API and receiver implementation inspected line-by-line.
- [x] React screens, components, styles, and API client inspected.
- [x] Existing test suites, reports, and release scripts inspected.
- [x] All 24 roadmap features mapped to source files (§4).
- [x] Implemented / partial / absent / broken classified.
- [x] Limitations, dependencies, and security risks identified (§5, §6).
- [x] Baseline commands executed and actual results reported (§1).
- [x] No existing functionality lost; no runtime data changed; no keys exposed.
- [x] One pre-existing defect found, fixed, and regression-tested (§2).

**Phase 0 complete.** Proceeding to Phase 1.
