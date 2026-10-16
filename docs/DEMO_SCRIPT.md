# Demo Script — 90 seconds

A judge can follow this without reading any source. Every step is executed by the
person demoing; nothing is submitted silently, and no authentication, authorisation, or
freshness check is bypassed to make a step succeed.

Start the app with `npm run dev` (or `python -m backend` + `npm run preview`), then open
the browser. Press **Guided Demo** in the navigation — it walks these same six steps and
tells you which fixture to generate and what to watch.

---

## Before you start (15 s)

1. Point out the header: **live API connected**, the session ID, and the
   `local_simulation` flag.
2. Point out the protected-state panel: mode `NORMAL`, reporting interval `10`,
   antenna `NOMINAL`, power `87 %`. Note that the last two are *derived* from mode and
   cannot be set by any message.
3. Say plainly: this is a synthetic local simulator. There is no live command channel.

---

## Step 1 — Valid command (15 s)

1. In **Guided Demo**, step 1, press **Generate valid fixture**.
2. Press **Submit for validation** in the message builder.
3. Show the result: **ACCEPTED / OK**, all eight stages PASS.
4. Show the protected state: mode moves `NORMAL → POWER_SAVING`, antenna `NOMINAL → STOWED`,
   power `87 → 42`.
5. Point at the audit reference — the decision now exists as a persisted record.

> What to say: "The receiver ran eight ordered checks. All of them passed, so the
> command was committed inside one transaction."

---

## Step 2 — Replay attempt (15 s)

1. Step 2, **Generate replay fixture**. This resubmits the *exact bytes* that were just
   accepted.
2. **Submit**.
3. Show the result: **REJECTED / REPLAY**. Note which stage failed — *replay*, the last
   security stage. Structure, identity, authentication and freshness all **PASSED**.
4. Show the protected state: unchanged.

> What to say: "The signature is valid. The sender is authorised. The message is fresh.
> It is still refused, because it has already been accepted. Replay is a separate
> decision from authentication."

---

## Step 3 — Tampered command (15 s)

1. Step 3, **Generate tampered fixture**. This changes the payload after signing.
2. **Submit**.
3. Show the result: **REJECTED / AUTH_FAILED**. The authentication stage **FAILS**;
   every later stage reads **NOT RUN**.
4. Show the protected state: still `POWER_SAVING`.

> What to say: "The payload was altered, so the HMAC no longer matches. The receiver
> stops at authentication and never evaluates the rest. Note that skipped stages are
> reported as NOT RUN — the timeline never invents a duration for a check that did not
> run."

---

## Step 4 — Authenticated but unauthorised (15 s)

1. Step 4, **Generate unauthorised fixture**. This is a correctly signed message from
   the observer identity.
2. **Submit**.
3. Show the result: authentication **PASS**, authorization **FAIL**, `NOT_AUTHORISED`.
4. Protected state unchanged.

> What to say: "This is the distinction that matters most. A valid HMAC proves who sent
> a message. It does not prove they were allowed to send it. Authentication and
> authorization are separate stages, and passing the first does not imply the second."

---

## Step 5 — Normal vs attack comparison (15 s)

1. Step 5, press **Capture normal**, then generate and submit a valid command, and
   **Capture attack**. Or use any two decisions already in the audit table.
2. Open **Comparison** in the navigation.
3. Show the two columns side by side: both verdicts, the changed fields, the state
   before and after on each side, the per-stage results, and the audit references.
4. Switch to **Raw submitted bytes** to show the exact bytes each side submitted.

> What to say: "Both columns are real submissions. Neither is predicted. The only
> difference between the accepted and rejected run is the bytes that were sent."

---

## Step 6 — Audit evidence and the suite (15 s)

1. Step 6, open **Audit & Evidence**.
2. Press **Verify chain**. Show `VERIFIED`, the number of linked records, and the
   covered-field list.
3. Expand **Show limitations** and read them aloud — this is the honest part:
   the chain detects modification of covered records and broken links; it does not
   prove origin; it does not prevent a full rewrite from genesis; it is **not**
   tamper-proof.
4. Open **Metrics** and show that the counters come from the backend, not the UI.
5. Open **Scenario Lab** and press **Run real suite**. Show the per-case table and the
   score.

> What to say: "Every decision has an event ID and a hash-linked record. The integrity
> check is read-only — it never repairs anything. And the suite result is a real
> execution, not a stored number."

---

## Optional, if there is time

- **Policy** page: show the four roles, the permission matrix, and that administration
  is disabled by default because it is a local boundary, not public authorization.
- **Attack Timeline**: show the linear view of the most recent decision.
- **Anomalies**: the metrics page reports rule-based findings with the disclaimer that
  they are not proof of malicious activity.

---

## Things to say if asked

| Question | Answer |
|---|---|
| Is this real spacecraft software? | No. It is a local synthetic simulator with no live command channel. |
| Can I trust the numbers on screen? | Every counter comes from `GET /api/metrics`, computed from persisted audit rows. The metrics scope is the live session; suite statistics are reported separately. |
| Is the audit log tamper-proof? | No, and it does not claim to be. It is tamper-*evident* for the fields it covers. The limitations are listed in the UI and in `docs/SECURITY_VERIFICATION.md`. |
| Does a valid HMAC mean a command is allowed? | No. Authentication and authorization are separate stages. Step 4 demonstrates this. |
| What happens if the database fails? | The decision becomes `SERVICE_ERROR`, nothing is committed, and no audit record falsely claims persistence. |
| Does a reset destroy history? | No. `POST /api/demo/reset` creates a new session at the documented initial state and reports what was preserved. No session, record, chain link, or key is deleted. |
| Is the anomaly detection AI? | No. Five deterministic rules with published thresholds. |

---

## Timing

| Section | Time |
|---|---|
| Before you start | 15 s |
| Steps 1–4 | 60 s |
| Step 5 | 15 s |
| Step 6 | 15 s |
| **Total** | **~105 s** |

Fixtures expire after **60 seconds**. If a step stalls, regenerate the fixture — the
Guided Demo shows a reminder.
