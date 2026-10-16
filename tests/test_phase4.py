"""Phase 4 coverage: deterministic reset (features 18/24), fault-injection expansion
(feature 19), and concurrency exercised through the real HTTP surface (feature 20).

All destructive testing uses isolated temporary data directories. The live runtime
database and its signing keys are never touched.
"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

import backend.app as module
from backend.engine import Engine, INITIAL, SCENARIO_CASE_COUNT, STAGE_REASONS

NOW = 1792137600


@pytest.fixture
def engine(tmp_path):
    return Engine(tmp_path)


@pytest.fixture
def client(tmp_path, monkeypatch):
    receiver = Engine(tmp_path / 'private')
    monkeypatch.setattr(module, 'engine', receiver)
    with TestClient(module.app, base_url='http://127.0.0.1') as c:
        yield c


def accept(engine, **kw):
    kw.setdefault('payload', {'mode': 'POWER_SAVING'})
    message = engine.issue(now=NOW, **kw)
    result = engine.validate(json.dumps(message).encode(), now=NOW)
    assert result['verdict'] == 'ACCEPTED', result
    return result


class TestDeclaredCaseCount:
    def test_declared_count_matches_the_real_suite(self, engine):
        """The number shown in the UI can never drift from the executed suite."""
        report = engine.scenarios()
        assert report['total'] == SCENARIO_CASE_COUNT
        assert report['passed'] == report['total']

    def test_every_roadmap_fault_case_is_present(self, engine):
        report = engine.scenarios()
        names = {r['name'] for r in report['results']}
        required = {
            'Missing required field', 'Unknown envelope field', 'Boolean is not integer',
            'Duplicate JSON key', 'Invalid payload range', 'Unknown action', 'Unknown key',
            'Expired message', 'Future timestamp', 'Oversized body',
            'Database commit failure rollback', 'Database audit failure rollback',
            'Replay after engine restart', 'Corrupt storage surfaces as an error',
            'Concurrent duplicate / 1', 'Concurrent duplicate / 2',
        }
        missing = required - names
        assert not missing, f'Suite is missing roadmap fault cases: {sorted(missing)}'

    def test_suite_covers_every_receiver_stage(self, engine):
        """Every stage that can fail must be exercised by at least one case."""
        report = engine.scenarios()
        failed_stages = set()
        for case in report['results']:
            for check in case['result'].get('checks') or []:
                if check.get('status') == 'FAIL':
                    failed_stages.add(check['stage'])
        # Every stage except commit (which only fails on injected storage errors,
        # covered separately by the rollback cases) must be reachable.
        assert failed_stages >= {'structure', 'identity', 'authentication', 'payload',
                                 'time', 'permissions', 'replay'}


class TestDeterministicReset:
    def test_reset_returns_the_documented_initial_state(self, engine):
        accept(engine, payload={'mode': 'SAFE'})
        result = engine.reset_demo()
        assert result['protected_state'] == INITIAL
        assert result['latest_telemetry'] is None
        assert result['state_schema_version'] == 2

    def test_reset_is_deterministic(self, engine):
        first = engine.reset_demo()['protected_state']
        second = engine.reset_demo()['protected_state']
        assert first == second == INITIAL

    def test_reset_preserves_history_and_keys(self, engine):
        accept(engine)
        before_audit = engine.audit()['total']
        before_chain = engine.verify_audit_chain()['links_checked']
        before_keys = dict(engine.secrets)
        result = engine.reset_demo()
        assert engine.audit()['total'] == before_audit
        assert engine.verify_audit_chain()['links_checked'] == before_chain
        assert engine.secrets == before_keys, 'Signing keys must never be rotated by a reset.'
        assert result['preserved']['audit_events'] == before_audit
        assert result['preserved']['signing_keys'] == len(before_keys)

    def test_reset_creates_an_isolated_replay_stream(self, engine):
        accept(engine)
        reset = engine.reset_demo()
        # A message from the previous session cannot be replayed into the new one,
        # and the new stream starts at sequence 1.
        message = engine.issue(session=reset['session_id'], payload={'mode': 'NORMAL'}, now=NOW)
        assert message['sequence'] == 1
        result = engine.validate(json.dumps(message).encode(), session=reset['session_id'], now=NOW)
        assert result['verdict'] == 'ACCEPTED'

    def test_reset_endpoint(self, client):
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        response = client.post('/api/demo/reset')
        assert response.status_code == 200
        body = response.json()
        assert body['protected_state'] == INITIAL
        assert body['preserved']['audit_events'] >= 1
        # The reset session is isolated and live.
        state = client.get('/api/state').json()
        assert state['session_id'] == body['session_id']
        assert state['protected_state'] == INITIAL


class TestConcurrencyOverHttp:
    def test_exactly_one_acceptance_over_http(self, client):
        """Two simultaneous submissions of the same bytes through the real API."""
        fixture = client.post('/api/demo/issue', json={}).json()
        raw = json.dumps(fixture['message'])
        session = client.get('/api/state').json()['session_id']
        barrier = threading.Barrier(2)

        def submit(_):
            barrier.wait(timeout=15)
            return client.post('/api/messages?session_id=' + session, content=raw)

        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(submit, range(2)))
        verdicts = sorted(r.json()['verdict'] for r in results)
        assert verdicts == ['ACCEPTED', 'REJECTED'], verdicts
        accepted = next(r.json() for r in results if r.json()['verdict'] == 'ACCEPTED')
        rejected = next(r.json() for r in results if r.json()['verdict'] == 'REJECTED')
        assert accepted['reason_code'] == 'OK'
        assert rejected['reason_code'] == 'REPLAY'
        assert accepted['state_changed'] is True
        assert rejected['state_changed'] is False
        # Exactly one committed state transition and one persisted acceptance.
        assert client.get('/api/state').json()['protected_state']['mode'] == 'POWER_SAVING'
        page = client.get('/api/audit?verdict=ACCEPTED').json()
        assert page['total'] == 1
        assert client.get('/api/audit/verify').json()['status'] == 'VERIFIED'

    def test_persisted_replay_records_are_consistent(self, client):
        fixture = client.post('/api/demo/issue', json={}).json()
        raw = json.dumps(fixture['message'])
        session = client.get('/api/state').json()['session_id']
        barrier = threading.Barrier(3)

        def submit(_):
            barrier.wait(timeout=15)
            return client.post('/api/messages?session_id=' + session, content=raw)

        with ThreadPoolExecutor(3) as pool:
            results = list(pool.map(submit, range(3)))
        verdicts = sorted(r.json()['verdict'] for r in results)
        assert verdicts == ['ACCEPTED', 'REJECTED', 'REJECTED']
        assert sum(1 for r in results if r.json()['state_changed']) == 1
        with module.engine.connect() as db:
            assert db.execute('SELECT COUNT(*) FROM streams').fetchone()[0] == 1
            assert db.execute('SELECT COUNT(*) FROM accepted').fetchone()[0] == 1
        assert client.get('/api/audit/verify').json()['status'] == 'VERIFIED'


class TestFaultInjectionBoundaries:
    @pytest.mark.parametrize('body,expected', [
        (b'{}', 'SCHEMA_INVALID'),
        (b'[]', 'SCHEMA_INVALID'),
        (b'null', 'SCHEMA_INVALID'),
        (b'"string"', 'SCHEMA_INVALID'),
        (b'{"version":1,"version":2}', 'INVALID_JSON'),
        (b'{not json}', 'INVALID_JSON'),
        (b'', 'INVALID_JSON'),
        (b' ' * 8200 + b'{}', 'BODY_TOO_LARGE'),
        (b'{"a":' + b'[' * 200, 'INVALID_JSON'),
    ])
    def test_boundary_inputs(self, engine, body, expected):
        result = engine.validate(body, now=NOW)
        assert result['reason_code'] == expected, body[:40]
        assert result['state_changed'] is False

    def test_unknown_stage_reason_mapping_is_exhaustive(self):
        """Every reason code the receiver can emit must map to exactly one stage."""
        from backend.engine import REASON_STAGE
        assert set(REASON_STAGE) == {r for rs in STAGE_REASONS.values() for r in rs}
        for stage, reasons in STAGE_REASONS.items():
            for reason in reasons:
                assert REASON_STAGE[reason] == stage

    def test_corrupt_storage_raises_rather_than_swallowing(self, engine):
        accept(engine)
        with engine.connect() as db:
            db.execute("UPDATE audit SET event='CORRUPT_PRIVATE_STORAGE_VALUE'")
        with pytest.raises(Exception):
            engine.audit()
        # The engine itself is still usable afterwards.
        assert engine.state()['protected_state']['mode'] == 'POWER_SAVING'

    def test_lock_contention_is_bounded(self, client):
        receiver = module.engine
        receiver.db_timeout_s = 0.05
        with receiver.connect() as lock:
            lock.execute('BEGIN IMMEDIATE')
            response = client.post('/api/demo/issue', json={})
            assert response.status_code == 503
            assert response.json()['verdict'] == 'SERVICE_ERROR'
        receiver.db_timeout_s = 2


class TestCsvExport:
    """Feature 16 — CSV export of decision records."""

    def test_audit_rows_carry_every_exported_column(self, client):
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        session = client.get('/api/state').json()['session_id']
        page = client.get(f'/api/audit?session_id={session}&limit=200').json()
        assert page['total'] == 1
        event = page['events'][0]
        for column in ['event_id', 'session_id', 'received_at', 'verdict', 'reason_code',
                       'first_failed_stage', 'sender_verified', 'state_changed',
                       'replay_state_advanced', 'audit_persisted', 'input_sha256']:
            assert column in event, f'CSV column {column} has no backing data.'
        assert event['first_failed_stage'] is None  # accepted decision

    def test_csv_source_data_contains_no_secrets(self, client):
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        session = client.get('/api/state').json()['session_id']
        page = client.get(f'/api/audit?session_id={session}&limit=200').json()
        blob = json.dumps(page)
        assert 'secret' not in blob.lower()
        # The signing key *values* must never appear in any response. Key identifiers
        # such as 'operator-key-01' are public labels, not secrets.
        for name, value in module.engine.secrets.items():
            assert value not in blob, f'Signing key for {name} leaked into the API response.'
        # The key file itself must never be readable through any endpoint.
        key_file = json.dumps(module.engine.secrets)
        assert key_file not in blob
        # Note: `auth_tag` legitimately appears in the persisted record. It is an
        # HMAC-SHA256 tag over public envelope fields, not a secret key, and the
        # receiver needs it to demonstrate byte-exact replay. It is deliberately NOT
        # one of the exported CSV columns.
        assert 'auth_tag' in json.dumps(page['events'][0].get('message') or {})

    def test_json_export_still_works_and_stays_secret_free(self, client):
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        session = client.get('/api/state').json()['session_id']
        data = client.get(f'/api/export?session_id={session}').json()
        assert data['events'] and data['audit_chain']['status'] == 'VERIFIED'
        assert 'secret' not in json.dumps(data).lower()
