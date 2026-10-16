"""Phase 3/4 backend coverage: security metrics (feature 13) and rule-based
synthetic telemetry anomaly detection (feature 21).

All counts must come from persisted records. Nothing may be hardcoded, and isolated
scenario-suite statistics must never inflate live-session statistics.
"""
import json

import pytest
from fastapi.testclient import TestClient

import backend.app as module
from backend.engine import Engine, REASON_STAGE, SCENARIO_CASE_COUNT, STAGE_REASONS

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


def reject(engine, **kw):
    kw.setdefault('payload', {'mode': 'NORMAL'})
    message = engine.issue(now=NOW, **kw)
    message['auth_tag'] = '0' * 64
    return engine.validate(json.dumps(message).encode(), now=NOW)


class TestMetrics:
    def test_empty_session_has_zeroed_metrics(self, engine):
        report = engine.metrics()
        assert report['scope'] == 'live session'
        assert report['live']['messages_checked'] == 0
        assert report['live']['accepted'] == 0
        assert report['live']['acceptance_rate'] is None
        assert report['scenario_suites']['cases_executed'] == 0

    def test_counts_are_derived_from_persisted_records(self, engine):
        accept(engine, payload={'mode': 'POWER_SAVING'})
        accept(engine, payload={'mode': 'SAFE'})
        reject(engine, payload={'mode': 'NORMAL'})
        live = engine.metrics()['live']
        assert live['messages_checked'] == 3
        assert live['accepted'] == 2
        assert live['rejected'] == 1
        assert live['authentication_failures'] == 1
        assert live['acceptance_rate'] == round(2 / 3, 4)

    def test_replay_attempts_are_counted(self, engine):
        message = engine.issue(now=NOW, payload={'mode': 'SAFE'})
        first = engine.validate(json.dumps(message).encode(), now=NOW)
        assert first['verdict'] == 'ACCEPTED'
        engine.validate(json.dumps(message).encode(), now=NOW)  # identical bytes -> REPLAY
        live = engine.metrics()['live']
        assert live['replay_attempts_detected'] == 1
        assert live['reason_code_breakdown']['REPLAY'] == 1

    def test_rejection_reasons_exclude_ok(self, engine):
        accept(engine)
        reject(engine)
        live = engine.metrics()['live']
        assert 'OK' not in live['rejection_reasons']
        assert 'AUTH_FAILED' in live['rejection_reasons']
        assert live['reason_code_breakdown']['OK'] == 1

    def test_first_failed_stage_breakdown(self, engine):
        reject(engine)                                        # authentication
        engine.validate(b'{"version":1,"version":1}', now=NOW)  # structure
        stages = engine.metrics()['live']['first_failed_stages']
        assert stages.get('authentication') == 1
        assert stages.get('structure') == 1

    def test_suite_statistics_are_isolated_from_live_counts(self, engine):
        """A suite run must never inflate the live dashboard."""
        accept(engine, payload={'mode': 'SAFE'})
        before = engine.metrics()
        engine.scenarios()
        after = engine.metrics()
        assert after['live']['messages_checked'] == before['live']['messages_checked'], \
            'Isolated suite decisions leaked into the live counters.'
        assert after['scenario_suites']['cases_executed'] == SCENARIO_CASE_COUNT
        assert after['scenario_suites']['cases_passed'] == SCENARIO_CASE_COUNT
        assert after['scenario_suites']['cases_failed'] == 0
        assert after['scenario_suites']['protected_state_integrity_violations'] == 0

    def test_session_scoping(self, engine):
        accept(engine, payload={'mode': 'SAFE'})
        other = engine.new_session()
        accept(engine, session=other, payload={'mode': 'NORMAL'})
        assert engine.metrics(engine.active_session())['live']['messages_checked'] == 1
        assert engine.metrics(other)['live']['messages_checked'] == 1

    def test_metrics_endpoint(self, client):
        client.post('/api/demo/issue', json={})
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        report = client.get('/api/metrics').json()
        assert report['live']['messages_checked'] >= 1
        assert 'secret' not in json.dumps(report).lower()

    def test_metrics_endpoint_session_scoped(self, client):
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        session = client.get('/api/state').json()['session_id']
        report = client.get(f'/api/metrics?session_id={session}').json()
        assert report['session_id'] == session
        assert report['live']['messages_checked'] == 1


class TestAnomalyDetection:
    def test_consistent_telemetry_produces_no_findings(self, engine):
        accept(engine, payload={'mode': 'POWER_SAVING'})
        accept(engine, sender='satellite-01', kind='TELEMETRY', action='TELEMETRY_STATUS',
               payload={'battery_pct': 87, 'temperature_c': 24, 'mode': 'POWER_SAVING'})
        report = engine.anomalies()
        assert report['finding_count'] == 0

    def test_stale_mode_report_is_flagged(self, engine):
        accept(engine, payload={'mode': 'POWER_SAVING'})
        result = accept(engine, sender='satellite-01', kind='TELEMETRY', action='TELEMETRY_STATUS',
                        payload={'battery_pct': 87, 'temperature_c': 24, 'mode': 'SAFE'})
        # The telemetry itself is authenticated and accepted...
        assert result['verdict'] == 'ACCEPTED'
        # ...but the anomaly detector still flags the disagreement.
        findings = engine.anomalies()['findings']
        assert any(f['rule'] == 'STALE_REPORT' for f in findings)

    def test_sudden_battery_drop_is_flagged(self, engine):
        accept(engine, sender='satellite-01', kind='TELEMETRY', action='TELEMETRY_STATUS',
               payload={'battery_pct': 90, 'temperature_c': 24, 'mode': 'NORMAL'})
        accept(engine, sender='satellite-01', kind='TELEMETRY', action='TELEMETRY_STATUS',
               payload={'battery_pct': 40, 'temperature_c': 24, 'mode': 'NORMAL'})
        findings = engine.anomalies()['findings']
        assert any(f['rule'] == 'SUDDEN_BATTERY_DROP' for f in findings)

    def test_sudden_temperature_jump_is_flagged(self, engine):
        accept(engine, sender='satellite-01', kind='TELEMETRY', action='TELEMETRY_STATUS',
               payload={'battery_pct': 90, 'temperature_c': 20, 'mode': 'NORMAL'})
        accept(engine, sender='satellite-01', kind='TELEMETRY', action='TELEMETRY_STATUS',
               payload={'battery_pct': 90, 'temperature_c': 90, 'mode': 'NORMAL'})
        findings = engine.anomalies()['findings']
        assert any(f['rule'] == 'SUDDEN_TEMPERATURE_JUMP' for f in findings)

    def test_mode_without_command_is_flagged(self, engine):
        accept(engine, sender='satellite-01', kind='TELEMETRY', action='TELEMETRY_STATUS',
               payload={'battery_pct': 90, 'temperature_c': 20, 'mode': 'NORMAL'})
        findings = engine.anomalies()['findings']
        assert any(f['rule'] == 'MODE_WITHOUT_COMMAND' for f in findings)

    def test_rejected_messages_never_produce_findings(self, engine):
        """Only accepted telemetry is analysed; a rejection is not an anomaly source."""
        message = engine.issue(now=NOW, sender='satellite-01', kind='TELEMETRY',
                               action='TELEMETRY_STATUS',
                               payload={'battery_pct': 90, 'temperature_c': 20, 'mode': 'NORMAL'})
        message['auth_tag'] = '0' * 64
        result = engine.validate(json.dumps(message).encode(), now=NOW)
        assert result['verdict'] == 'REJECTED'
        assert engine.anomalies()['finding_count'] == 0

    def test_findings_are_explainable_and_carry_evidence(self, engine):
        accept(engine, payload={'mode': 'POWER_SAVING'})
        accept(engine, sender='satellite-01', kind='TELEMETRY', action='TELEMETRY_STATUS',
               payload={'battery_pct': 87, 'temperature_c': 24, 'mode': 'SAFE'})
        report = engine.anomalies()
        for finding in report['findings']:
            assert finding['detail']
            assert finding['event_id']
            assert finding['rule'] in {r['rule'] for r in report['rules']}

    def test_rules_and_thresholds_are_documented_in_the_response(self, engine):
        report = engine.anomalies()
        assert {r['rule'] for r in report['rules']} == {
            'OUT_OF_RANGE', 'SUDDEN_BATTERY_DROP', 'SUDDEN_TEMPERATURE_JUMP',
            'MODE_WITHOUT_COMMAND', 'STALE_REPORT'}
        assert report['rules'][0]['thresholds']
        assert 'NOT proof of malicious activity' in report['disclaimer']

    def test_anomaly_is_not_an_authentication_verdict(self, engine):
        """An anomaly must never be reported as an authentication or authorisation failure."""
        accept(engine, payload={'mode': 'POWER_SAVING'})
        accept(engine, sender='satellite-01', kind='TELEMETRY', action='TELEMETRY_STATUS',
               payload={'battery_pct': 87, 'temperature_c': 24, 'mode': 'SAFE'})
        report = engine.anomalies()
        assert report['findings']
        for finding in report['findings']:
            assert finding['verdict'] == 'ACCEPTED'
            assert finding['reason_code'] == 'OK'

    def test_anomalies_endpoint(self, client):
        fixture = client.post('/api/demo/issue', json={'scenario': 'telemetry'}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        report = client.get('/api/anomalies').json()
        assert 'findings' in report
        assert report['disclaimer']
        assert 'secret' not in json.dumps(report).lower()


class TestEvidenceFiltering:
    """Feature 22 — filtering by sender, type, verdict, reason, stage, session, time."""

    def _populate(self, engine):
        accept(engine, payload={'mode': 'POWER_SAVING'})
        reject(engine, payload={'mode': 'SAFE'})                       # AUTH_FAILED
        engine.validate(b'{"version":1,"version":1}', now=NOW)          # INVALID_JSON
        accept(engine, sender='observer-01', kind='COMMAND', action='GET_STATUS', payload={})

    def test_filter_by_verdict(self, engine):
        self._populate(engine)
        accepted = engine.audit(verdict='ACCEPTED')
        rejected = engine.audit(verdict='REJECTED')
        assert accepted['total'] == 2
        assert rejected['total'] == 2
        assert all(e['verdict'] == 'ACCEPTED' for e in accepted['events'])

    def test_filter_by_sender(self, engine):
        self._populate(engine)
        page = engine.audit(sender='observer-01')
        assert page['total'] == 1
        assert page['events'][0]['message']['sender_id'] == 'observer-01'

    def test_filter_by_reason(self, engine):
        self._populate(engine)
        page = engine.audit(reason='AUTH_FAILED')
        assert page['total'] == 1
        assert page['events'][0]['reason_code'] == 'AUTH_FAILED'

    def test_filter_by_message_type(self, engine):
        self._populate(engine)
        # The malformed-JSON case has no parsed message, so its kind is UNKNOWN.
        assert engine.audit(kind='COMMAND')['total'] == 3
        assert engine.audit(kind='UNKNOWN')['total'] == 1

    def test_filter_by_validation_stage(self, engine):
        self._populate(engine)
        auth = engine.audit(stage='authentication')
        structure = engine.audit(stage='structure')
        assert auth['total'] == 1 and auth['events'][0]['reason_code'] == 'AUTH_FAILED'
        assert structure['total'] == 1 and structure['events'][0]['reason_code'] == 'INVALID_JSON'

    def test_stage_filter_maps_to_the_right_stage_for_every_code(self, engine):
        """Each reason code must resolve to exactly one stage."""
        assert set(REASON_STAGE) == {r for rs in STAGE_REASONS.values() for r in rs}
        for stage, reasons in STAGE_REASONS.items():
            for reason in reasons:
                assert REASON_STAGE[reason] == stage

    def test_every_event_reports_its_first_failed_stage(self, engine):
        self._populate(engine)
        for event in engine.audit()['events']:
            if event['verdict'] == 'REJECTED':
                assert event['first_failed_stage']
                assert event['first_failed_stage'] in STAGE_REASONS
            else:
                assert event['first_failed_stage'] is None

    def test_filter_by_time_range(self, engine):
        self._populate(engine)
        base = NOW
        everything = engine.audit()['total']
        assert engine.audit(since=base - 10, until=base + 10)['total'] == everything
        assert engine.audit(since=base + 1000)['total'] == 0
        assert engine.audit(until=base - 1000)['total'] == 0

    def test_pagination_stays_accurate_under_filters(self, engine):
        for index in range(6):
            reject(engine, payload={'mode': 'SAFE'})
        page = engine.audit(verdict='REJECTED', limit=3, offset=0)
        assert page['total'] == 6
        assert len(page['events']) == 3
        second = engine.audit(verdict='REJECTED', limit=3, offset=3)
        assert len(second['events']) == 3
        ids = {e['event_id'] for e in page['events']} | {e['event_id'] for e in second['events']}
        assert len(ids) == 6, 'Pages must not overlap.'

    def test_session_filter(self, engine):
        self._populate(engine)
        other = engine.new_session()
        accept(engine, session=other, payload={'mode': 'NORMAL'})
        assert engine.audit(session=other)['total'] == 1

    def test_unknown_stage_is_rejected(self, engine):
        with pytest.raises(ValueError):
            engine.audit(stage='not-a-stage')

    def test_bad_timestamp_is_rejected(self, engine):
        with pytest.raises(ValueError):
            engine.audit(since='yesterday')

    def test_audit_endpoint_rejects_unknown_stage_with_400(self, client):
        response = client.get('/api/audit?stage=bogus')
        assert response.status_code == 400
        assert 'Unknown validation stage' in response.json()['detail']

    def test_corrupt_audit_record_is_service_error_not_leaked(self, client):
        """A storage failure must surface as a bounded SERVICE_ERROR, never as a 400
        that echoes corrupt content, and never as a stack trace."""
        fixture = client.post('/api/demo/issue', json={}).json()
        client.post('/api/messages', content=json.dumps(fixture['message']))
        with module.engine.connect() as db:
            db.execute("UPDATE audit SET event='CORRUPT_PRIVATE_STORAGE_VALUE'")
        response = client.get('/api/audit')
        assert response.status_code == 503
        assert response.json()['verdict'] == 'SERVICE_ERROR'
        assert 'CORRUPT_PRIVATE_STORAGE_VALUE' not in response.text
