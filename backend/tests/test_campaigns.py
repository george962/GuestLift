"""Campaign and loyalty reporting tests use only generated fictional data."""
from __future__ import annotations

import csv
import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from app import database
from app.adapters import parse
from app.campaigns import import_campaign_csvs
from app.main import app

ROOT=Path(__file__).resolve().parents[1] / 'fixtures' / 'campaigns'


def _client(tmp_path, monkeypatch):
    engine=create_engine(f'sqlite:///{tmp_path / "campaign-test.sqlite"}',connect_args={'check_same_thread':False})
    monkeypatch.setattr(database, 'engine', engine)
    return TestClient(app),engine


def _files():
    return {'campaigns_file':('Campaigns.csv',(ROOT/'Campaigns.csv').read_bytes(),'text/csv'),
            'redemptions_file':('Redemptions.csv',(ROOT/'Redemptions.csv').read_bytes(),'text/csv')}


def test_campaign_requires_imported_orders(tmp_path,monkeypatch):
    client,engine=_client(tmp_path,monkeypatch)
    with client:
        result=client.post('/api/campaigns/upload',files=_files())
        assert result.status_code==200
        info=result.json()
        assert info['campaigns_inserted']==2
        assert info['redemptions_inserted']==0
        assert info['rejected']==21
        assert any('import POS orders first' in i for i in info['issues'])
    engine.dispose()


def test_campaign_reports_match_orders_and_are_idempotent(tmp_path,monkeypatch):
    client,engine=_client(tmp_path,monkeypatch)
    with client:
        result=client.post('/api/campaigns/demo/load')
        assert result.status_code==200,result.text
        info=result.json()
        assert info['campaigns_inserted']==2
        assert info['redemptions_inserted']==21
        assert info['rejected']==0,info['issues']
        payload=client.get('/api/campaigns/report').json()
        assert payload['total_redemptions']==21
        assert len(payload['campaigns'])==2
        assert sum(c['redeemed_orders'] for c in payload['campaigns'])==21
        assert sum(c['recorded_discount_minor'] for c in payload['campaigns'])>0
        assert sum(c['attributed_net_sales_minor'] for c in payload['campaigns'])>0
        assert payload['customer_summary']['identified_orders']>0
        assert payload['customer_summary']['repeat_customers']>0
        assert payload['customer_summary']['anonymous_orders']>0
        assert client.post('/api/campaigns/demo/load').json()['redemptions_inserted']==0
        assert client.get('/api/campaigns/report').json()['total_redemptions']==21
        assert client.get('/api/metrics').json()['order_count']==56
    engine.dispose()


def test_campaign_net_sales_not_subtracted_twice(tmp_path,monkeypatch):
    client,engine=_client(tmp_path,monkeypatch)
    with client:
        client.post('/api/campaigns/demo/load')
        r=client.get('/api/campaigns/report?margin_percent=50').json()['campaigns']
        for c in r:
            expected=round(c['attributed_net_sales_minor']*.5)-c['variable_campaign_cost_minor']-c['fixed_campaign_cost_minor']
            assert c['modeled_contribution_minor']==expected
        assert client.get('/api/campaigns/report?margin_percent=-1').status_code==422
        assert client.get('/api/campaigns/report?margin_percent=101').status_code==422
    engine.dispose()


def test_upload_replays_and_preserves_order_totals(tmp_path,monkeypatch):
    client,engine=_client(tmp_path,monkeypatch)
    with client:
        client.post('/api/import/toast')
        client.post('/api/import/square')
        before=client.get('/api/metrics').json()['net_sales_minor']
        first=client.post('/api/campaigns/upload',files=_files()).json()
        assert first['redemptions_inserted']==21
        second=client.post('/api/campaigns/upload',files=_files()).json()
        assert second['redemptions_inserted']==0
        assert second['duplicates']==23
        assert client.get('/api/metrics').json()['net_sales_minor']==before
    engine.dispose()


def test_invalid_rows_are_reported_without_silent_sales(tmp_path,monkeypatch):
    client,engine=_client(tmp_path,monkeypatch)
    with client:
        client.post('/api/campaigns/demo/load')
        filedata={'campaigns_file':('Campaigns.csv',(ROOT/'Campaigns.csv').read_bytes(),'text/csv'),
                 'redemptions_file':('Redemptions.csv',(ROOT/'Redemptions-broken.csv').read_bytes(),'text/csv')}
        result=client.post('/api/campaigns/upload',files=filedata)
        assert result.status_code==200
        assert result.json()['redemptions_inserted']==0
        assert result.json()['rejected']==2
        assert any('exceeds POS order discount' in x for x in result.json()['issues'])
        assert any('not imported' in x for x in result.json()['issues'])
    engine.dispose()


def test_bad_header_returns_422(tmp_path,monkeypatch):
    client,engine=_client(tmp_path,monkeypatch)
    with client:
        filedata=_files()
        b=(ROOT/'Redemptions.csv').read_bytes().replace(b'campaign_id',b'bad_name')
        filedata['redemptions_file']=('Redemptions.csv',b,'text/csv')
        r=client.post('/api/campaigns/upload',files=filedata)
        assert r.status_code==422
        assert 'campaign_id' in r.json()['detail']
    engine.dispose()


def test_no_duplicate_campaign_on_order_even_with_other_redemption_id(tmp_path,monkeypatch):
    client,engine=_client(tmp_path,monkeypatch)
    with client:
        client.post('/api/campaigns/demo/load')
        b=(ROOT/'Redemptions.csv').read_text().splitlines()
        cols=b[0].split(',')
        entry=dict(zip(cols,b[1].split(',')))
        entry['redemption_id']='ANOTHER-ON-SAME-ORDER'
        sink=io.StringIO();w=csv.DictWriter(sink,fieldnames=cols);w.writeheader();w.writerow(entry)
        r=client.post('/api/campaigns/upload',files={
            'campaigns_file':('Campaigns.csv',(ROOT/'Campaigns.csv').read_bytes(),'text/csv'),
            'redemptions_file':('Redemptions.csv',sink.getvalue().encode(),'text/csv')})
        assert r.status_code==200
        assert r.json()['rejected']==1
        assert 'already has' in r.json()['issues'][0]
    engine.dispose()


def test_legacy_schema_adds_nullable_customer_id(tmp_path,monkeypatch):
    legacy=create_engine(f'sqlite:///{tmp_path / "legacy.sqlite"}')
    with legacy.begin() as conn:
        conn.execute(text('CREATE TABLE canonical_orders (id INTEGER PRIMARY KEY, provider VARCHAR(20), source_order_id VARCHAR(120), location_id VARCHAR(120), created_at VARCHAR(80), net_sales_minor INTEGER, discount_minor INTEGER, refund_minor INTEGER, payload_json TEXT)'))
    monkeypatch.setattr(database,'engine',legacy)
    database.init_db()
    assert 'customer_id' in {c['name'] for c in inspect(legacy).get_columns('canonical_orders')}
    database.init_db() # repeated safe
    legacy.dispose()


def test_customer_ids_are_optional_and_scoped():
    orders=parse('toast')+parse('square')
    assert any(o.customer_id is None for o in orders)
    assert all(not o.customer_id or o.customer_id.startswith('TEST-') for o in orders)
    summary=database.customer_summary([o.model_dump() for o in orders])
    assert summary['repeat_customers']>0
    assert 0<summary['customer_coverage_percent']<100
