"""Phase 2 — tamper-evident audit evidence (roadmap feature 9).

Every test uses an isolated temporary data directory. The live runtime database
and its keys are never touched.
"""
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

import backend.app as module
from backend.engine import Engine, CHAIN_GENESIS, CHAIN_COVERED_FIELDS, ROLES

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


def accept(engine, payload=None):
    message = engine.issue(now=NOW, payload=payload or {'mode': 'POWER_SAVING'})
    result = engine.validate(json.dumps(message).encode(), now=NOW)
    assert result['verdict'] == 'ACCEPTED', result
    return message, result


def reject(engine, payload=None):
    message = engine.issue(now=NOW, payload=payload or {'mode': 'SAFE'})
    message['auth_tag'] = '0' * 64
    result = engine.validate(json.dumps(message).encode(), now=NOW)
    assert result['reason_code'] == 'AUTH_FAILED', result
    return message, result


# --- Chain construction --------------------------------------------------------

class TestChainConstruction:
    def test_every_decision_is_chained(self, engine):
        accept(engine)
        reject(engine)
        with engine.connect() as db:
            assert db.execute('SELECT COUNT(*) FROM audit').fetchone()[0] == 2
            assert db.execute('SELECT COUNT(*) FROM audit_chain').fetchone()[0] == 2

    def test_genesis_link_uses_the_documented_zero_hash(self, engine):
        accept(engine)
        with engine.connect() as db:
            row = db.execute('SELECT prev_hash FROM audit_chain ORDER BY seq LIMIT 1').fetchone()
        assert row[0] == CHAIN_GENESIS

    def test_links_are_hash_linked_in_order(self, engine):
        accept(engine)
        accept(engine, {'mode': 'SAFE'})
        with engine.connect() as db:
            rows = db.execute('SELECT seq,record_hash,prev_hash FROM audit_chain ORDER BY seq').fetchall()
        assert len(rows) == 2
        assert rows[0][2] == CHAIN_GENESIS
        assert rows[1][2] == rows[0][1], 'Second link must chain to the first record hash.'

    def test_covered_fields_are_explicitly_declared(self, engine):
        accept(engine)
        report = engine.verify_audit_chain()
        assert 'event_id' in report['covered_fields']
        assert 'verdict' in report['covered_fields']
        assert 'reason_code' in report['covered_fields']
        assert set(report['covered_fields']) == set(CHAIN_COVERED_FIELDS)

    def test_chain_covers_both_accepted_and_rejected(self, engine):
        accept(engine)
        reject(engine)
        with engine.connect() as db:
            kinds = {r[0] for r in db.execute(
                "SELECT json_extract(covered,'$.verdict') FROM audit_chain")}
        assert kinds == {'ACCEPTED', 'REJECTED'}


# --- Verification outcomes -----------------------------------------------------

class TestVerification:
    def test_unmodified_chain_verifies(self, engine):
        accept(engine)
        accept(engine, {'mode': 'SAFE'})
        reject(engine)
        report = engine.verify_audit_chain()
        assert report['status'] == 'VERIFIED'
        assert report['problems'] == []
        assert report['links_checked'] == 3

    def test_modified_covered_record_is_detected(self, engine):
        reject(engine)
        with engine.connect() as db:
            row = db.execute("SELECT id,event FROM audit LIMIT 1").fetchone()
            event = json.loads(row[1])
            event['reason_code'] = 'OK'
            event['verdict'] = 'ACCEPTED'
            db.execute('UPDATE audit SET event=?,verdict=? WHERE id=?', (json.dumps(event), 'ACCEPTED', row[0]))
        report = engine.verify_audit_chain()
        assert report['status'] == 'FAILED'
        assert any(p['kind'] == 'RECORD_MODIFIED' for p in report['problems'])

    def test_broken_link_is_detected(self, engine):
        accept(engine)
        accept(engine, {'mode': 'SAFE'})
        with engine.connect() as db:
            db.execute('DELETE FROM audit_chain WHERE seq=(SELECT MIN(seq) FROM audit_chain)')
        report = engine.verify_audit_chain()
        assert report['status'] == 'FAILED'
        assert any(p['kind'] == 'BROKEN_LINK' for p in report['problems'])

    def test_missing_intermediate_record_is_detected(self, engine):
        accept(engine)
        accept(engine, {'mode': 'SAFE'})
        accept(engine, {'mode': 'NORMAL'})
        with engine.connect() as db:
            # Drop the middle link and renumber, simulating a removed record.
            db.execute('DELETE FROM audit_chain WHERE seq=(SELECT MIN(seq)+1 FROM audit_chain)')
            db.execute('UPDATE audit_chain SET seq=seq-1 WHERE seq>2')
        report = engine.verify_audit_chain()
        assert report['status'] == 'FAILED'
        assert any(p['kind'] in ('BROKEN_LINK', 'MISSING_LINK') for p in report['problems'])

    def test_orphan_link_is_detected(self, engine):
        accept(engine)
        with engine.connect() as db:
            db.execute('DELETE FROM audit')
        report = engine.verify_audit_chain()
        assert report['status'] == 'FAILED'
        assert any(p['kind'] == 'ORPHAN_LINK' for p in report['problems'])

    def test_failure_explanation_identifies_the_problem(self, engine):
        accept(engine)
        with engine.connect() as db:
            row = db.execute('SELECT id,event FROM audit LIMIT 1').fetchone()
            event = json.loads(row[1])
            event['state_changed'] = not event['state_changed']
            db.execute('UPDATE audit SET event=? WHERE id=?', (json.dumps(event), row[0]))
        report = engine.verify_audit_chain()
        problem = next(p for p in report['problems'] if p['kind'] == 'RECORD_MODIFIED')
        assert 'altered after commit' in problem['detail']
        assert problem['link']

    def test_limitations_are_stated_not_omitted(self, engine):
        accept(engine)
        report = engine.verify_audit_chain()
        assert report['status'] == 'VERIFIED'
        text = ' '.join(report['limitations']).lower()
        assert 'tamper-proof' in text and 'not' in text
        assert 'origin' in text
        assert 'rewriting the entire chain' in text

    def test_empty_chain_is_reported_not_silently_passed(self, engine):
        report = engine.verify_audit_chain()
        assert report['links_checked'] == 0
        assert report['uncovered_records'] == 0


# --- Pre-migration safety ------------------------------------------------------

class TestPreMigrationRecords:
    def test_legacy_records_are_uncovered_not_failed(self, engine):
        accept(engine)
        with engine.connect() as db:
            db.execute('DELETE FROM audit_chain')
        report = engine.verify_audit_chain()
        assert report['status'] == 'VERIFIED', 'Legacy records must not be reported as failures.'
        assert report['links_checked'] == 0
        assert report['uncovered_records'] == 1
        assert 'not covered' in report['uncovered_note']

    def test_verification_never_repairs_or_deletes(self, engine):
        accept(engine)
        reject(engine)
        with engine.connect() as db:
            before_audit = db.execute('SELECT COUNT(*) FROM audit').fetchone()[0]
            before_chain = db.execute('SELECT COUNT(*) FROM audit_chain').fetchone()[0]
        engine.verify_audit_chain()
        with engine.connect() as db:
            assert db.execute('SELECT COUNT(*) FROM audit').fetchone()[0] == before_audit
            assert db.execute('SELECT COUNT(*) FROM audit_chain').fetchone()[0] == before_chain

    def test_mixed_legacy_and_chained_records(self, engine):
        accept(engine)
        with engine.connect() as db:
            db.execute('DELETE FROM audit_chain')      # make record 1 legacy
        accept(engine, {'mode': 'SAFE'})                # record 2 gets chained
        report = engine.verify_audit_chain()
        assert report['status'] == 'VERIFIED'
        assert report['links_checked'] == 1
        assert report['uncovered_records'] == 1


# --- Atomicity (Rule 4) --------------------------------------------------------

class TestChainAtomicity:
    def test_chain_write_failure_rolls_back_everything(self, engine, monkeypatch):
        message = engine.issue(now=NOW, payload={'mode': 'SAFE'})
        before = engine.state()
        original = engine.connect

        class BrokenChain:
            def __init__(self): self.conn = original()
            def __getattr__(self, name): return getattr(self.conn, name)

            def execute(self, sql, *args):
                if sql.startswith('INSERT INTO audit_chain'):
                    raise sqlite3.OperationalError('injected chain write failure')
                return self.conn.execute(sql, *args)

        monkeypatch.setattr(engine, 'connect', BrokenChain)
        result = engine.validate(json.dumps(message).encode(), now=NOW)
        monkeypatch.setattr(engine, 'connect', original)

        assert result['verdict'] == 'SERVICE_ERROR'
        assert result['audit_persisted'] is False
        assert result['state_changed'] is False
        assert engine.state()['protected_state'] == before['protected_state']
        assert engine.audit()['total'] == 0
        with engine.connect() as db:
            assert db.execute('SELECT COUNT(*) FROM audit_chain').fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM streams').fetchone()[0] == 0
        # A retry after recovery must still succeed.
        retry = engine.validate(json.dumps(message).encode(), now=NOW)
        assert retry['verdict'] == 'ACCEPTED'

    def test_chain_survives_engine_restart(self, engine):
        accept(engine)
        restarted = Engine(engine.root)
        report = restarted.verify_audit_chain()
        assert report['status'] == 'VERIFIED'
        assert report['links_checked'] == 1
        # A new decision continues the chain across the restart.
        accept(restarted, {'mode': 'SAFE'})
        assert restarted.verify_audit_chain()['links_checked'] == 2


# --- HTTP surface --------------------------------------------------------------

class TestChainAPI:
    def test_verify_endpoint(self, client):
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        response = client.get('/api/audit/verify')
        assert response.status_code == 200
        report = response.json()
        assert report['status'] == 'VERIFIED'
        assert report['links_checked'] == 1
        assert report['limitations']

    def test_verify_endpoint_detects_tampering(self, client):
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        receiver = module.engine
        with receiver.connect() as db:
            row = db.execute('SELECT id,event FROM audit LIMIT 1').fetchone()
            event = json.loads(row[1])
            event['reason_code'] = 'TAMPERED'
            db.execute('UPDATE audit SET event=? WHERE id=?', (json.dumps(event), row[0]))
        report = client.get('/api/audit/verify').json()
        assert report['status'] == 'FAILED'
        assert any(p['kind'] == 'RECORD_MODIFIED' for p in report['problems'])

    def test_export_includes_chain_verification(self, client):
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        session = client.get('/api/state').json()['session_id']
        data = client.get(f'/api/export?session_id={session}').json()
        assert 'audit_chain' in data
        assert data['audit_chain']['status'] == 'VERIFIED'
        assert data['audit_chain']['limitations']
        # No secret material may appear in an export.
        blob = json.dumps(data)
        assert 'secret' not in blob.lower()

    def test_verify_is_read_only(self, client):
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        before = client.get('/api/audit').json()['total']
        client.get('/api/audit/verify')
        assert client.get('/api/audit').json()['total'] == before


# --- Feature 8: server-authoritative role policy -------------------------------

class TestRolePolicy:
    def test_default_roles_reproduce_baseline_authorisation(self, engine):
        """The role model must be behaviour-identical to the previous expression."""
        cases = [
            ('observer-01', 'COMMAND', 'GET_STATUS', True),
            ('observer-01', 'COMMAND', 'SET_MODE', False),
            ('observer-01', 'TELEMETRY', 'TELEMETRY_STATUS', False),
            ('operator-01', 'COMMAND', 'GET_STATUS', True),
            ('operator-01', 'COMMAND', 'SET_MODE', True),
            ('operator-01', 'COMMAND', 'SET_REPORT_INTERVAL', True),
            ('operator-01', 'TELEMETRY', 'TELEMETRY_STATUS', False),
            ('satellite-01', 'TELEMETRY', 'TELEMETRY_STATUS', True),
            ('satellite-01', 'COMMAND', 'GET_STATUS', False),
            ('satellite-01', 'COMMAND', 'SET_MODE', False),
            ('intruder-99', 'COMMAND', 'SET_MODE', False),
        ]
        for sender, kind, action, expected in cases:
            allowed, _ = engine.permitted(sender, kind, action)
            assert allowed is expected, f'{sender}/{kind}/{action} -> {allowed}, expected {expected}'

    def test_role_cannot_be_granted_by_a_message_field(self, engine):
        """A frontend-supplied field must never confer a role."""
        message = engine.issue(now=NOW, sender='observer-01', payload={'mode': 'SAFE'})
        message['role'] = 'ADMINISTRATOR'
        message['auth_tag'] = engine.sign(message)
        result = engine.validate(json.dumps(message).encode(), now=NOW)
        assert result['reason_code'] == 'SCHEMA_INVALID', 'Extra envelope fields are rejected.'
        assert engine.state()['protected_state']['mode'] == 'NORMAL'

    def test_administrator_role_is_inert_by_default(self, engine):
        allowed, role = engine.permitted('operator-01', 'COMMAND', 'SET_MODE')
        assert allowed and role == 'OPERATOR'
        snapshot = engine.policy_snapshot()
        admin = next(r for r in snapshot['roles'] if r['role'] == 'ADMINISTRATOR')
        assert admin['senders'] == [], 'No baseline sender may default to ADMINISTRATOR.'

    def test_policy_snapshot_is_read_only_and_secret_free(self, engine):
        snapshot = engine.policy_snapshot()
        blob = json.dumps(snapshot)
        assert 'secret' not in blob.lower()
        assert snapshot['server_authoritative'] is True
        assert {r['role'] for r in snapshot['roles']} == set(ROLES)

    def test_policy_change_is_versioned_and_audited(self, engine):
        before = engine.policy_version()
        version = engine.set_role_permissions('VIEWER', {'COMMAND': ['GET_STATUS', 'SET_MODE']})
        assert version != before
        assert version.rsplit('.', 1)[1] == str(int(before.rsplit('.', 1)[1]) + 1)
        allowed, _ = engine.permitted('observer-01', 'COMMAND', 'SET_MODE')
        assert allowed is True, 'The change must take effect for later decisions.'
        with engine.connect() as db:
            row = db.execute("SELECT event FROM audit WHERE verdict='POLICY_CHANGE' ORDER BY rowid DESC LIMIT 1").fetchone()
        assert row is not None
        event = json.loads(row[0])
        assert event['role'] == 'VIEWER'
        assert event['policy_version'] == version

    def test_policy_change_is_chained(self, engine):
        engine.set_role_permissions('VIEWER', {'COMMAND': ['GET_STATUS']})
        report = engine.verify_audit_chain()
        assert report['status'] == 'VERIFIED'
        assert report['links_checked'] >= 1

    def test_policy_change_survives_restart(self, tmp_path):
        root = tmp_path
        Engine(root).set_role_permissions('VIEWER', {'COMMAND': ['GET_STATUS', 'SET_MODE']})
        restarted = Engine(root)
        allowed, _ = restarted.permitted('observer-01', 'COMMAND', 'SET_MODE')
        assert allowed is True, 'Policy rows must persist and must not be re-seeded over.'

    def test_invalid_policy_change_is_rejected(self, engine):
        for bad in [{'COMMAND': ['NOT_AN_ACTION']}, {'BOGUS_KIND': ['GET_STATUS']}, {}, {'COMMAND': 'GET_STATUS'}]:
            with pytest.raises(ValueError):
                engine.set_role_permissions('VIEWER', bad)
        with pytest.raises(ValueError):
            engine.set_role_permissions('NO_SUCH_ROLE', {'COMMAND': ['GET_STATUS']})
        # Nothing was written.
        allowed, _ = engine.permitted('observer-01', 'COMMAND', 'SET_MODE')
        assert allowed is False

    def test_unauthorised_message_still_cannot_command_after_grant(self, engine):
        """Granting a role via the admin surface must not let a *message* escalate."""
        engine.set_role_permissions('VIEWER', {'COMMAND': ['GET_STATUS', 'SET_MODE']})
        message = engine.issue(now=NOW, sender='observer-01', payload={'mode': 'SAFE'})
        message['auth_tag'] = engine.sign(message)
        result = engine.validate(json.dumps(message).encode(), now=NOW)
        # observer-01 now legitimately holds SET_MODE through the policy model...
        assert result['verdict'] == 'ACCEPTED'
        # ...but an unauthenticated attempt still fails at authentication.
        message['auth_tag'] = '0' * 64
        assert engine.validate(json.dumps(message).encode(), now=NOW)['reason_code'] == 'AUTH_FAILED'


class TestPolicyAPI:
    def test_policy_endpoint_is_read_only(self, client):
        response = client.get('/api/policy')
        assert response.status_code == 200
        body = response.json()
        assert 'secret' not in json.dumps(body).lower()
        assert body['roles']

    def test_policy_admin_is_closed_by_default(self, client):
        response = client.post('/api/policy/roles/VIEWER',
                               json={'permissions': {'COMMAND': ['SET_MODE']}})
        assert response.status_code == 403
        assert 'local administrative boundary' in response.json()['detail']
        # Nothing changed.
        allowed, _ = module.engine.permitted('observer-01', 'COMMAND', 'SET_MODE')
        assert allowed is False

    def test_policy_admin_rejects_unknown_actions(self, client, monkeypatch):
        monkeypatch.setenv('KAVACH_ALLOW_POLICY_ADMIN', '1')
        response = client.post('/api/policy/roles/VIEWER',
                               json={'permissions': {'COMMAND': ['LAUNCH']}})
        assert response.status_code == 422
        allowed, _ = module.engine.permitted('observer-01', 'COMMAND', 'SET_MODE')
        assert allowed is False
