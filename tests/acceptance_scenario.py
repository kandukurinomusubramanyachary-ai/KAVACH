"""Roadmap acceptance scenario, executed for real.

Runs the eight acceptance tests from the engineering brief against a live FastAPI
server on an isolated data directory, and prints an honest PASS/FAIL table.

Run:  .venv/bin/python tests/acceptance_scenario.py
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.engine import Engine  # noqa: E402  (needs the path insertion above)
PORT = int(os.environ.get('KAVACH_ACCEPTANCE_PORT', '8099'))
BASE = f'http://127.0.0.1:{PORT}'
RESULTS = []


def record(number, name, expected, observed, passed, detail=''):
    RESULTS.append({'test': number, 'name': name, 'expected': expected,
                    'observed': observed, 'passed': bool(passed), 'detail': detail})


def call(path, method='GET', body=None, raw=None, headers=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    request = urllib.request.Request(BASE + path, data=data, method=method,
                                     headers={'Content-Type': 'application/json', **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or '{}')


def issue(scenario='valid', **kw):
    return call('/api/demo/issue', 'POST', {'scenario': scenario, **kw})[1]


def submit(message, session=None):
    text = message if isinstance(message, str) else json.dumps(message)
    path = '/api/messages' + (f'?session_id={session}' if session else '')
    return call(path, 'POST', raw=text.encode())[1]


def state(session=None):
    return call('/api/state' + (f'?session_id={session}' if session else ''))[1]


def main():
    with tempfile.TemporaryDirectory(prefix='kavach-acceptance-') as directory:
        environment = dict(os.environ, KAVACH_DATA_DIR=directory, KAVACH_ALLOW_POLICY_ADMIN='1')
        server = subprocess.Popen(
            [sys.executable, '-m', 'backend', '--port', str(PORT)],
            cwd=ROOT, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(60):
                try:
                    if call('/api/health')[1].get('status') == 'online':
                        break
                except Exception:
                    pass
                time.sleep(0.25)
            else:
                print('BLOCKED: server did not become healthy.')
                return 2
            run_acceptance()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()

    width = max(len(r['name']) for r in RESULTS)
    print(f"\n{'TEST':<6}{'NAME':<{width}}  {'RESULT':<7}OBSERVED")
    print('-' * (width + 34))
    for row in RESULTS:
        print(f"{row['test']:<6}{row['name']:<{width}}  {'PASS' if row['passed'] else 'FAIL':<7}{row['observed']}")
    failed = [r for r in RESULTS if not r['passed']]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} acceptance tests passed.")
    return 1 if failed else 0


def run_acceptance():
    initial = state()
    record('Setup', 'Initial state', "mode NORMAL / interval 10 / no telemetry",
           f"{initial['protected_state']['mode']} / {initial['protected_state']['report_interval_s']} / "
           f"{'no telemetry' if initial['latest_telemetry'] is None else 'telemetry present'}",
           initial['protected_state']['mode'] == 'NORMAL'
           and initial['protected_state']['report_interval_s'] == 10
           and initial['latest_telemetry'] is None)

    # --- Test 1: valid command ---
    session = initial['session_id']
    fixture = issue('valid')
    result = submit(fixture['message'], session)
    after = state(session)
    checks = result.get('checks') or []
    record(1, 'Valid command', 'ACCEPTED / OK / all stages PASS / mode POWER_SAVING / replay advances / audit persists',
           f"{result['verdict']} / {result['reason_code']} / "
           f"{sum(1 for c in checks if c['status'] == 'PASS')}/8 PASS / mode {after['protected_state']['mode']} / "
           f"replay {'advanced' if result['replay_state_advanced'] else 'unchanged'} / "
           f"audit {'persisted' if result['audit_persisted'] else 'not persisted'}",
           result['verdict'] == 'ACCEPTED' and result['reason_code'] == 'OK'
           and all(c['status'] == 'PASS' for c in checks)
           and result['sender_verified'] is True
           and after['protected_state']['mode'] == 'POWER_SAVING'
           and result['replay_state_advanced'] is True
           and result['audit_persisted'] is True)

    # --- Test 2: tampered command ---
    fixture = issue('valid')
    tampered = dict(fixture['message'])
    tampered['payload'] = {'mode': 'SAFE'}
    result = submit(tampered, session)
    after = state(session)
    checks = result.get('checks') or []
    record(2, 'Tampered command', 'REJECTED / AUTH_FAILED / auth FAIL / later NOT_RUN / mode unchanged / replay unchanged / audit persists',
           f"{result['verdict']} / {result['reason_code']} / "
           f"auth {next((c['status'] for c in checks if c['stage'] == 'authentication'), '?')} / "
           f"later {next((c['status'] for c in checks if c['stage'] == 'payload'), '?')} / "
           f"mode {after['protected_state']['mode']} / "
           f"replay {'unchanged' if not result['replay_state_advanced'] else 'ADVANCED'} / "
           f"audit {'persisted' if result['audit_persisted'] else 'not persisted'}",
           result['verdict'] == 'REJECTED' and result['reason_code'] == 'AUTH_FAILED'
           and next(c['status'] for c in checks if c['stage'] == 'authentication') == 'FAIL'
           and all(c['status'] == 'NOT_RUN' for c in checks if c['stage'] in
                   {'payload', 'time', 'permissions', 'replay', 'commit'})
           and after['protected_state']['mode'] == 'POWER_SAVING'
           and result['replay_state_advanced'] is False
           and result['audit_persisted'] is True)

    # --- Test 3: replay attack ---
    fixture = issue('valid')
    accepted = submit(fixture['message'], session)
    replayed = submit(fixture['message'], session)
    after = state(session)
    checks = replayed.get('checks') or []
    record(3, 'Replay attack', 'REJECTED / REPLAY / replay stage FAIL / mode unchanged / replay state unchanged',
           f"{replayed['verdict']} / {replayed['reason_code']} / "
           f"replay stage {next((c['status'] for c in checks if c['stage'] == 'replay'), '?')} / "
           f"mode {after['protected_state']['mode']} / "
           f"replay state {'unchanged' if not replayed['replay_state_advanced'] else 'ADVANCED'}",
           replayed['verdict'] == 'REJECTED' and replayed['reason_code'] == 'REPLAY'
           and next(c['status'] for c in checks if c['stage'] == 'replay') == 'FAIL'
           and after['protected_state']['mode'] == 'POWER_SAVING'
           and replayed['replay_state_advanced'] is False)

    # --- Test 4: unauthorised command ---
    fixture = issue('unauthorised')
    result = submit(fixture['message'], session)
    after = state(session)
    checks = result.get('checks') or []
    record(4, 'Unauthorised command', 'auth PASS / authorization FAIL / NOT_AUTHORISED / mode unchanged / replay unchanged',
           f"auth {next((c['status'] for c in checks if c['stage'] == 'authentication'), '?')} / "
           f"authorization {next((c['status'] for c in checks if c['stage'] == 'permissions'), '?')} / "
           f"{result['reason_code']} / mode {after['protected_state']['mode']} / "
           f"replay {'unchanged' if not result['replay_state_advanced'] else 'ADVANCED'}",
           next(c['status'] for c in checks if c['stage'] == 'authentication') == 'PASS'
           and next(c['status'] for c in checks if c['stage'] == 'permissions') == 'FAIL'
           and result['reason_code'] == 'NOT_AUTHORISED'
           and after['protected_state']['mode'] == 'POWER_SAVING'
           and result['replay_state_advanced'] is False)

    # --- Test 5: telemetry ---
    before_telemetry = state(session)['latest_telemetry']
    fixture = issue('telemetry')
    result = submit(fixture['message'], session)
    after = state(session)
    record(5, 'Telemetry', 'ACCEPTED / telemetry changes / protected mode still POWER_SAVING',
           f"{result['verdict']} / telemetry {'changed' if after['latest_telemetry'] != before_telemetry else 'UNCHANGED'} / "
           f"mode {after['protected_state']['mode']}",
           result['verdict'] == 'ACCEPTED'
           and after['latest_telemetry'] is not None
           and after['latest_telemetry'] != before_telemetry
           and after['protected_state']['mode'] == 'POWER_SAVING')

    # --- Test 6: concurrency ---
    fresh = call('/api/demo/reset', 'POST')[1]
    concurrency_session = fresh['session_id']
    fixture = issue('valid', session_id=concurrency_session)
    raw = json.dumps(fixture['message'])
    barrier = threading.Barrier(2)

    def simultaneous(_):
        barrier.wait(timeout=20)
        return submit(raw, concurrency_session)

    with ThreadPoolExecutor(2) as pool:
        concurrent = list(pool.map(simultaneous, range(2)))
    verdicts = sorted(r['verdict'] for r in concurrent)
    reasons = sorted(r['reason_code'] for r in concurrent)
    transitions = sum(1 for r in concurrent if r['state_changed'])
    record(6, 'Concurrency', 'exactly one ACCEPTED, other REPLAY, one state transition, consistent records',
           f"{verdicts} / {reasons} / {transitions} transition(s) / "
           f"accepted rows {call('/api/audit?verdict=ACCEPTED')[1]['total']}",
           verdicts == ['ACCEPTED', 'REJECTED'] and reasons == ['OK', 'REPLAY']
           and transitions == 1
           and call('/api/audit/verify')[1]['status'] == 'VERIFIED')

    # --- Test 7: database failure (injected commit failure) ---
    # Fault injection uses a fresh isolated engine; the live runtime database is never opened.
    with tempfile.TemporaryDirectory(prefix='kavach-fault-') as fault_dir:
        fault_engine = Engine(fault_dir)
        message = fault_engine.issue(now=int(time.time()), payload={'mode': 'SAFE'})
        before = fault_engine.state()
        original = fault_engine.connect

        class BrokenCommit:
            def __init__(self): self.conn = original()
            def __getattr__(self, name): return getattr(self.conn, name)
            def commit(self): raise sqlite3.OperationalError('injected commit failure')

        fault_engine.connect = BrokenCommit
        result = fault_engine.validate(json.dumps(message).encode())
        fault_engine.connect = original
        unchanged = (fault_engine.state()['protected_state'] == before['protected_state']
                     and fault_engine.audit()['total'] == 0)
        record(7, 'Database failure', 'SERVICE_ERROR / no execution claimed / no state mutation / replay unchanged / no false audit',
               f"{result['verdict']} / state {'unchanged' if unchanged else 'CHANGED'} / "
               f"audit rows {fault_engine.audit()['total']} / "
               f"persisted {result.get('audit_persisted')}",
               result['verdict'] == 'SERVICE_ERROR'
               and result.get('audit_persisted') is False
               and result['state_changed'] is False and unchanged)

    # --- Test 8: audit integrity ---
    verify_before = call('/api/audit/verify')[1]
    with tempfile.TemporaryDirectory(prefix='kavach-chain-') as chain_dir:
        chain_engine = Engine(chain_dir)
        for mode in ['POWER_SAVING', 'SAFE', 'NORMAL']:
            message = chain_engine.issue(now=int(time.time()), payload={'mode': mode})
            chain_engine.validate(json.dumps(message).encode())
        clean = chain_engine.verify_audit_chain()
        with chain_engine.connect() as db:
            row = db.execute('SELECT id,event FROM audit ORDER BY rowid LIMIT 1').fetchone()
            event = json.loads(row[1])
            # Rewrite a covered field to a value the receiver never produced. Using
            # protected_state_after (not verdict/reason, which are already 'ACCEPTED'/'OK'
            # for these records) so the tamper is a genuine change.
            original_after = event['protected_state_after']
            event['protected_state_after'] = {'mode': 'SAFE', 'report_interval_s': 1,
                                              'antenna_status': 'STOWED', 'power_level_pct': 1}
            assert event['protected_state_after'] != original_after
            db.execute('UPDATE audit SET event=? WHERE id=?', (json.dumps(event), row[0]))
        tampered = chain_engine.verify_audit_chain()
        problems = [p['kind'] for p in tampered['problems']]
        record(8, 'Audit integrity', 'unmodified VERIFIED / modified FAILED with explanation / no silent repair / no tamper-proof claim',
               f"clean {clean['status']} / tampered {tampered['status']} {problems} / "
               f"{len(tampered['limitations'])} limitations stated",
               clean['status'] == 'VERIFIED'
               and tampered['status'] == 'FAILED'
               and 'RECORD_MODIFIED' in problems
               and any('altered after commit' in p['detail'] for p in tampered['problems'])
               and any('tamper-proof' in limitation.lower() for limitation in tampered['limitations']))


if __name__ == '__main__':
    sys.exit(main())
