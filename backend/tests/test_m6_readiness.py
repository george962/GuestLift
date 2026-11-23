"""M6: export isolation, preview acknowledgement, support controls, and no-PII signals."""
import csv
import io
import zipfile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import saas, readiness
from journey_support import harness  # noqa: F401


def test_preview_ack_is_explicit_and_persisted(harness):
    harness.sign_up()
    before = harness.get('/api/readiness/preview').json()
    assert before == {'version': readiness.PREVIEW_VERSION, 'acknowledged': False}
    assert harness.post('/api/readiness/preview', {'version': readiness.PREVIEW_VERSION,
                                                  'acknowledged': False}).status_code == 422
    assert harness.post('/api/readiness/preview', {'version': readiness.PREVIEW_VERSION,
                                                  'acknowledged': True}).status_code == 200
    assert harness.get('/api/readiness/preview').json()['acknowledged'] is True
    assert harness.post('/api/readiness/preview', {'version': readiness.PREVIEW_VERSION,
                                                  'acknowledged': True}).status_code == 200
    with Session(saas.engine) as db:
        assert len(db.scalars(select(readiness.WorkspacePreviewAck)).all()) == 1


def test_support_requests_are_scoped_rate_limited_and_not_emailed(harness):
    harness.sign_up()
    assert harness.post('/api/readiness/support', {'category':'other','description':'x'}).status_code == 422
    for i in range(3):
        r = harness.post('/api/readiness/support', {
            'category':'connection', 'description':f'Cannot sync my development workspace, attempt {i}'})
        assert r.status_code == 201
        assert 'No email' in r.json()['notice']
    assert harness.post('/api/readiness/support', {
        'category':'connection', 'description':'Fourth test request'}).status_code == 429
    with Session(saas.engine) as db:
        rows = db.scalars(select(readiness.SupportTicket)).all()
        assert len(rows) == 3 and all(x.category == 'connection' for x in rows)


def test_owner_export_uses_only_requested_workspace_and_never_tokens(harness):
    harness.sign_up()
    harness.connect_oauth(); harness.select_eligible()
    assert harness.post('/api/integrations/square/sync').status_code == 200
    r = harness.get('/api/readiness/export')
    assert r.status_code == 200 and r.headers['content-type'].startswith('application/zip')
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert {'square_orders.csv','square_refunds.csv','saved_decisions.csv','monitored_locations.csv','support_requests.csv'} <= set(z.namelist())
        rows = list(csv.DictReader(io.StringIO(z.read('square_orders.csv').decode('utf-8-sig'))))
        assert rows and all(x['source_order_id'] for x in rows)
        assert 'token_ciphertext' not in z.read('square_orders.csv').decode()
        assert 'access_token' not in z.read('README.txt').decode()
    assert r.headers['cache-control'] == 'no-store'


def test_export_isolation_other_workspace_gets_no_first_workspace_orders(harness):
    from fastapi.testclient import TestClient
    from app.main import app
    from journey_support import Harness

    harness.sign_up('first@isolation.test')
    harness.connect_oauth(); harness.select_eligible()
    assert harness.post('/api/integrations/square/sync').status_code == 200
    second = Harness(TestClient(app), harness.square)
    second.sign_up('second@isolation.test')
    zipped = second.get('/api/readiness/export')
    assert zipped.status_code == 200
    with zipfile.ZipFile(io.BytesIO(zipped.content)) as z:
        only_header = list(csv.DictReader(io.StringIO(z.read('square_orders.csv').decode('utf-8-sig'))))
        assert only_header == []


def test_new_readiness_tables_are_removed_on_workspace_deletion(harness):
    harness.sign_up()
    assert harness.post('/api/readiness/support', {'category': 'other',
        'description': 'Testing full workspace deletion cleanup.'}).status_code == 201
    assert harness.post('/api/readiness/event', {'event': 'client_error'}).status_code == 200
    assert harness.post('/api/team/account/delete', {'confirm': 'My Restaurant'}).status_code == 200
    with Session(saas.engine) as db:
        assert db.scalars(select(readiness.WorkspaceProductSignal)).all() == []
        assert db.scalars(select(readiness.SupportTicket)).all() == []
        assert db.scalars(select(readiness.WorkspacePreviewAck)).all() == []


def test_unverified_brief_cannot_record_insight_and_events_have_allowlist(harness):
    harness.sign_up()
    assert harness.post('/api/readiness/event', {'event':'first_insight_view'}).status_code == 409
    assert harness.post('/api/readiness/event', {'event':'customer_email'}).status_code == 422
    first = harness.post('/api/readiness/event', {'event':'client_error'})
    again = harness.post('/api/readiness/event', {'event':'client_error'})
    assert first.json()['recorded'] is True and again.json()['recorded'] is False
    with Session(saas.engine) as db:
        items = db.scalars(select(readiness.WorkspaceProductSignal)).all()
        assert len(items) == 1 and items[0].signal == 'client_error'
