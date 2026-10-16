"""Search extends the read API; receiver security semantics stay unchanged."""
import json
import pytest
from fastapi.testclient import TestClient
import backend.app as module
from backend.engine import Engine


@pytest.fixture
def receiver(tmp_path):
    return Engine(tmp_path)


@pytest.fixture
def client(receiver, monkeypatch):
    monkeypatch.setattr(module, 'engine', receiver)
    return TestClient(module.app,base_url='http://127.0.0.1')


def test_audit_search_identifiers_reasons_and_combined_filters(client, receiver):
    message = receiver.issue(payload={'mode': 'SAFE'})
    accepted = receiver.validate(json.dumps(message).encode())
    rejected = receiver.validate(json.dumps(message).encode())
    for needle in [accepted['event_id'], message['message_id'], 'operator-01',
                   accepted['session_id'], 'replay']:
        response = client.get('/api/audit', params={'q': needle})
        assert response.status_code == 200
        assert response.json()['total'] >= 1
    page = client.get('/api/audit', params={'q': message['message_id'], 'verdict': 'REJECTED',
                                          'stage': 'replay', 'limit': 1}).json()
    assert page['total'] == 1
    assert page['events'][0]['event_id'] == rejected['event_id']
    assert client.get('/api/audit', params={'q': 'not-present'}).json()['total'] == 0


@pytest.mark.parametrize('needle', ['%', '_', "' OR 1=1 --"])
def test_search_treats_wildcards_and_sql_as_literal(client, receiver, needle):
    receiver.validate(json.dumps(receiver.issue(payload={'mode':'SAFE'})).encode())
    assert client.get('/api/audit', params={'q': needle}).json()['total'] == 0


def test_search_length_is_bounded_and_exact_reason_stays_compatible(client):
    assert client.get('/api/audit', params={'q': 'x'*161}).status_code == 422
    assert client.get('/api/audit', params={'reason': 'REPLAY'}).status_code == 200


def test_export_verifies_global_chain_across_interleaved_sessions(receiver):
    original=receiver.active_session()
    first=receiver.validate(json.dumps(receiver.issue(payload={'mode':'SAFE'})).encode())
    isolated=receiver.new_session(False)
    receiver.validate(json.dumps(receiver.issue(session=isolated,payload={'mode':'SAFE'})).encode(),session=isolated)
    receiver.validate(json.dumps(receiver.issue(payload={'mode':'POWER_SAVING'})).encode())
    assert receiver.verify_audit_chain(original)['status']=='VERIFIED'
    exported=receiver.export(original)
    assert exported['audit_chain']['status']=='VERIFIED'
    assert exported['audit_chain']['scope']=='global audit chain'
    assert len(exported['events'])==2
    assert exported['audit_chain']['links_checked']==3
    with receiver.connect() as db:
        row=db.execute('SELECT id,event FROM audit WHERE session=?',(isolated,)).fetchone()
        event=json.loads(row[1]);event['protected_state_after']['mode']='NORMAL'
        db.execute('UPDATE audit SET event=? WHERE id=?',(json.dumps(event),row[0]))
    assert receiver.export(original)['audit_chain']['status']=='FAILED'


def test_export_chain_verification_reuses_its_read_snapshot(receiver,monkeypatch):
    receiver.validate(json.dumps(receiver.issue(payload={'mode':'SAFE'})).encode())
    original_verify=receiver.verify_audit_chain
    observed=[]
    def verify(session=None,db=None):
        assert db is not None and db.in_transaction
        observed.append(db)
        return original_verify(session,db=db)
    monkeypatch.setattr(receiver,'verify_audit_chain',verify)
    assert receiver.export()['audit_chain']['status']=='VERIFIED'
    assert len(observed)==1
