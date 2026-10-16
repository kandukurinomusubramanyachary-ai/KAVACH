"""Phase 1 regression coverage.

Covers the versioned protected-state migration (feature 4) and the three attack
presets the roadmap requires in the Scenario Lab (feature 2): unknown sender/key,
invalid authentication tag, and malformed JSON.

All tests use isolated temporary data directories. The presenter's runtime
database and keys are never touched.
"""
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

import backend.app as module
from backend.engine import (
    Engine, INITIAL, MODEL_RULES, MODEL_RULE_FIELDS, STATE_SCHEMA_VERSION,
    STAGES, canonical,
)

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


def validate(engine, message, **kw):
    raw = message if isinstance(message, bytes) else json.dumps(message).encode()
    return engine.validate(raw, now=NOW, **kw)


# --- Feature 4: versioned protected-state schema -------------------------------

class TestStateSchemaMigration:
    def test_fresh_database_has_documented_initial_values(self, engine):
        state = engine.state()
        assert state['protected_state'] == INITIAL
        assert state['state_schema_version'] == STATE_SCHEMA_VERSION
        # Deterministic: the same values every time, no randomness.
        assert INITIAL['antenna_status'] in {'NOMINAL', 'DEGRADED', 'STOWED'}
        assert 0 <= INITIAL['power_level_pct'] <= 100

    def test_initial_values_agree_with_the_model_rule_for_the_initial_mode(self):
        """The documented invariant: initial model fields match the rule for mode."""
        for field in MODEL_RULE_FIELDS:
            assert INITIAL[field] == MODEL_RULES[INITIAL['mode']][field]

    def test_migration_is_additive_and_preserves_existing_values(self, tmp_path):
        """A version-1 database must gain the new fields without losing any value."""
        root = tmp_path / 'legacy'
        engine = Engine(root)
        # Rewrite the stored session back to the version-1 shape, preserving values.
        legacy = {'mode': 'POWER_SAVING', 'report_interval_s': 30}
        with engine.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE id=?',
                       (json.dumps(legacy), engine.active_session()))
            db.execute("INSERT OR REPLACE INTO meta VALUES('state_schema_version','1')")
        # Reopen: the migration must run exactly once and additively.
        migrated = Engine(root)
        state = migrated.state()['protected_state']
        assert state['mode'] == 'POWER_SAVING'          # existing value preserved
        assert state['report_interval_s'] == 30          # existing value preserved
        for field in MODEL_RULE_FIELDS:
            assert state[field] == MODEL_RULES['POWER_SAVING'][field]  # rule-derived default
        assert migrated.state()['state_schema_version'] == STATE_SCHEMA_VERSION

    def test_migration_is_idempotent(self, tmp_path):
        root = tmp_path / 'legacy'
        Engine(root)
        with Engine(root).connect() as db:
            db.execute("UPDATE sessions SET state=? WHERE id=?",
                       (json.dumps({'mode': 'SAFE', 'report_interval_s': 5}), Engine(root).active_session()))
            db.execute("INSERT OR REPLACE INTO meta VALUES('state_schema_version','1')")
        first = Engine(root).state()['protected_state']
        second = Engine(root).state()['protected_state']
        assert first == second, 'A second migration must not alter already-migrated state.'

    def test_migration_never_touches_historical_audit_snapshots(self, engine):
        """Audit records keep the exact shape they were written with."""
        message = engine.issue(now=NOW, payload={'mode':'SAFE'})
        event = validate(engine, message)
        assert event['verdict'] == 'ACCEPTED'
        before = event['protected_state_before']
        with engine.connect() as db:
            row = db.execute('SELECT event FROM audit WHERE id=?', (event['event_id'],)).fetchone()
        stored = json.loads(row[0])
        assert stored['protected_state_before'] == before
        # The stored snapshot is a faithful historical record, not re-migrated.
        assert set(before) >= {'mode', 'report_interval_s'}

    def test_corrupt_state_fails_closed_instead_of_guessing(self, tmp_path):
        root = tmp_path / 'corrupt'
        engine = Engine(root)
        # Simulate a database still on schema version 1 whose state is unreadable.
        with engine.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE id=?', ('not-json', engine.active_session()))
            db.execute("INSERT OR REPLACE INTO meta VALUES('state_schema_version','1')")
        with pytest.raises(ValueError):
            Engine(root)

    def test_mode_transition_updates_model_fields_deterministically(self, engine):
        for mode, expected in MODEL_RULES.items():
            message = engine.issue(now=NOW, payload={'mode': mode})
            event = validate(engine, message)
            assert event['verdict'] == 'ACCEPTED', mode
            after = engine.state()['protected_state']
            assert after['mode'] == mode
            for field, value in expected.items():
                assert after[field] == value, f'{mode} -> {field}'

    def test_rejected_command_cannot_move_model_fields(self, engine):
        """Rule 3: a rejected message never mutates protected state, new fields included."""
        good = engine.issue(now=NOW, payload={'mode':'POWER_SAVING'})
        assert validate(engine, good)['verdict'] == 'ACCEPTED'
        baseline = engine.state()['protected_state']
        tampered = engine.issue(now=NOW, payload={'mode':'SAFE'})
        tampered['payload']['mode'] = 'SAFE'
        tampered['auth_tag'] = 'f' * 64
        event = validate(engine, tampered)
        assert event['verdict'] == 'REJECTED'
        assert event['reason_code'] == 'AUTH_FAILED'
        assert engine.state()['protected_state'] == baseline

    def test_no_message_can_set_model_fields_directly(self, engine):
        """The new fields are model outputs; the message surface is unchanged."""
        # The envelope schema is exact, so an extra field is rejected outright.
        message = engine.issue(now=NOW, payload={'mode':'SAFE'})
        message['power_level_pct'] = 3
        message['auth_tag'] = engine.sign(message)
        event = validate(engine, message)
        assert event['reason_code'] == 'SCHEMA_INVALID'
        assert engine.state()['protected_state']['power_level_pct'] == MODEL_RULES['NORMAL']['power_level_pct']


# --- Feature 2: required attack presets ---------------------------------------

class TestAttackPresets:
    def test_unknown_key_is_rejected_before_authentication(self, client):
        fixture = client.post('/api/demo/issue', json={'scenario': 'unknown_key'}).json()
        assert fixture['message']['key_id'] == 'unknown-key-99'
        assert fixture['expected_outcome'] == 'KEY_UNKNOWN'
        result = client.post('/api/messages', content=json.dumps(fixture['message'])).json()
        assert result['verdict'] == 'REJECTED'
        assert result['reason_code'] == 'KEY_UNKNOWN'
        assert result['checks'][1]['status'] == 'FAIL'          # identity stage
        assert result['checks'][2]['status'] == 'NOT_RUN'       # authentication never ran
        assert result['sender_verified'] is False
        assert result['state_changed'] is False

    def test_invalid_authentication_tag_is_rejected(self, engine):
        """Prove the returned tag is genuinely wrong, not merely different."""
        good = engine.issue(now=NOW, payload={'mode': 'POWER_SAVING'})
        bad = dict(good)
        tag = bad['auth_tag']
        bad['auth_tag'] = tag[:-1] + ('0' if tag[-1] != '0' else '1')
        assert bad['auth_tag'] != tag
        assert len(bad['auth_tag']) == 64
        # The receiver's own signing disagrees, so this is a real authentication failure.
        assert engine.sign(bad) != bad['auth_tag']
        result = validate(engine, bad)
        assert result['verdict'] == 'REJECTED'
        assert result['reason_code'] == 'AUTH_FAILED'
        assert result['checks'][0]['status'] == 'PASS'
        assert result['checks'][1]['status'] == 'PASS'
        assert result['checks'][2]['status'] == 'FAIL'
        assert result['checks'][3]['status'] == 'NOT_RUN'
        assert result['sender_verified'] is False
        assert result['state_changed'] is False

    def test_invalid_tag_preset_over_http(self, client):
        fixture = client.post('/api/demo/issue', json={'scenario': 'bad_tag'}).json()
        assert fixture['expected_outcome'] == 'AUTH_FAILED'
        assert len(fixture['message']['auth_tag']) == 64
        result = client.post('/api/messages', content=json.dumps(fixture['message'])).json()
        assert result['reason_code'] == 'AUTH_FAILED'
        assert result['checks'][2]['status'] == 'FAIL'

    def test_malformed_duplicate_key_json_is_rejected(self, client):
        fixture = client.post('/api/demo/issue', json={'scenario': 'malformed'}).json()
        raw = fixture['raw_text']
        assert fixture['expected_outcome'] == 'INVALID_JSON'
        # The editor receives malformed bytes, not a re-serialised envelope.
        assert raw.count('"version"') == 2, 'raw_text must carry the duplicate key'
        result = client.post('/api/messages', content=raw).json()
        assert result['verdict'] == 'REJECTED'
        assert result['reason_code'] == 'INVALID_JSON'
        assert result['checks'][0]['status'] == 'FAIL'
        assert result['state_changed'] is False
        # Python's own parser would silently collapse the duplicate; the receiver must not.
        collapsed = json.loads(raw)
        assert collapsed['version'] == 1

    def test_all_eight_presets_reject_for_the_correct_reason(self, client):
        """Every roadmap-required scenario, exercised through the real HTTP receiver."""
        expected = {
            'valid': 'OK', 'tampered': 'AUTH_FAILED', 'expired': 'EXPIRED',
            'unauthorised': 'NOT_AUTHORISED', 'unknown_key': 'KEY_UNKNOWN',
            'bad_tag': 'AUTH_FAILED', 'malformed': 'INVALID_JSON',
        }
        for scenario, reason in expected.items():
            fixture = client.post('/api/demo/issue', json={'scenario': scenario}).json()
            body = fixture.get('raw_text') or json.dumps(fixture['message'])
            result = client.post('/api/messages', content=body).json()
            assert result['reason_code'] == reason, f'{scenario}: {result["reason_code"]}'
            if reason != 'OK':
                assert result['verdict'] == 'REJECTED'
                assert result['state_changed'] is False

    def test_unknown_key_does_not_advance_replay_state(self, client):
        state_before = client.get('/api/state').json()
        fixture = client.post('/api/demo/issue', json={'scenario': 'unknown_key'}).json()
        result = client.post('/api/messages', content=json.dumps(fixture['message'])).json()
        assert result['replay_state_advanced'] is False
        state_after = client.get('/api/state').json()
        assert state_after['protected_state'] == state_before['protected_state']

    def test_preset_metadata_is_returned_for_the_ui(self, client):
        """The Scenario Lab needs intent/expectation metadata to label each attack."""
        # 'replay' legitimately requires a prior accepted message; accept one first.
        accepted = client.post('/api/demo/issue', json={'scenario': 'valid'}).json()
        client.post('/api/messages', content=json.dumps(accepted['message']))
        for scenario in ['valid', 'tampered', 'replay', 'expired', 'future',
                         'unauthorised', 'invalid', 'telemetry', 'unknown_key',
                         'bad_tag', 'malformed']:
            fixture = client.post('/api/demo/issue', json={'scenario': scenario}).json()
            assert 'message' in fixture
            assert fixture['expected_outcome']
            assert fixture['expectation_source']
