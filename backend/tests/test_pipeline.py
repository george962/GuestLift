"""Assertions are against bundled fictional sample inputs only."""
from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from fastapi.testclient import TestClient
from app.adapters import FIXTURE_DIR, cents, parse, parse_toast, parse_square
from app import database
from app.main import app


def test_toast_multirow_order_not_multiplied():
    rows=parse_toast()
    assert len(rows)==28
    third=next(x for x in rows if x.source_order_id=='9100003')
    assert len(third.payments)==2
    assert len(third.items)>=1
    assert third.net_sales_minor == third.gross_minor-third.discount_minor-third.refund_minor
    assert sum(x.net_sales_minor for x in rows)==59470


def test_square_uses_same_contract():
    rows=parse_square()
    assert len(rows)==28
    assert all(x.provider=='square' for x in rows)
    assert sum(x.net_sales_minor for x in rows)==65080
    assert all(x.net_sales_minor == x.gross_minor-x.discount_minor-x.refund_minor for x in rows)
    assert len({x.source_order_id for x in rows})==28


def test_cents_use_exact_decimal_not_float():
    assert cents('0.29')==29
    assert cents('2.05')==205
    assert cents('100.99')==10099
    with pytest.raises(ValueError):cents('not money')


def test_missing_column_gives_clear_error(tmp_path:Path):
    folder=tmp_path/'toast';folder.mkdir()
    for source in (FIXTURE_DIR/'toast').glob('*.csv'):
        (folder/source.name).write_bytes(source.read_bytes())
    path=folder/'OrderDetails.csv'
    path.write_text(path.read_text().replace('Order Id','Bad Name'),encoding='utf-8')
    with pytest.raises(ValueError,match='missing headers: Order Id'):
        parse_toast(folder)


def test_duplicate_toast_id_fails_before_persistence(tmp_path:Path):
    folder=tmp_path/'toast';folder.mkdir()
    for source in (FIXTURE_DIR/'toast').glob('*.csv'):
        (folder/source.name).write_bytes(source.read_bytes())
    path=folder/'OrderDetails.csv'
    rows=list(csv.DictReader(path.open(newline='',encoding='utf-8')))
    rows.append(dict(rows[0]))
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    with pytest.raises(ValueError,match='duplicate order IDs'):
        parse_toast(folder)


def test_square_bad_currency_rejected(tmp_path:Path):
    folder=tmp_path/'square';folder.mkdir()
    for source in (FIXTURE_DIR/'square').glob('*.json'):
        (folder/source.name).write_bytes(source.read_bytes())
    path=folder/'orders.json'
    payload=json.loads(path.read_text());payload['orders'][0]['line_items'][0]['gross_sales_money']['currency']='EUR'
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='USD'):
        parse_square(folder)


def test_sql_persistence_replay_and_metrics(tmp_path:Path,monkeypatch):
    engine=create_engine(f'sqlite:///{tmp_path/"test.db"}',connect_args={'check_same_thread':False})
    monkeypatch.setattr(database,'engine',engine)
    with TestClient(app) as client:
        assert client.get('/api/health').json()['status']=='ok'
        p=client.get('/api/preview/toast')
        assert p.status_code==200 and p.json()['summary']['orders']==28
        assert client.get('/api/preview/unknown').status_code==404
        initial=client.get('/api/metrics').json()
        assert initial['order_count']==0
        a=client.post('/api/import/toast').json()
        assert (a['inserted'],a['duplicates'])==(28,0)
        b=client.post('/api/import/toast').json()
        assert (b['inserted'],b['duplicates'])==(0,28)
        c=client.post('/api/import/square').json()
        assert (c['inserted'],c['duplicates'])==(28,0)
        m=client.get('/api/metrics').json()
        assert m['order_count']==56
        assert m['net_sales_minor']==59470+65080
        assert sum(x['net_sales_minor'] for x in m['orders'])==m['net_sales_minor']
        assert sum(x['discount_minor'] for x in m['orders'])==m['discounts_minor']
        assert client.get('/api/metrics?provider=toast').json()['order_count']==28
        assert client.get('/api/imports').json()['runs'][0]['provider']=='square'
        assert client.post('/api/reset').json()['status']=='reset'
        assert client.get('/api/metrics').json()['order_count']==0
    engine.dispose()



def test_upload_toast_and_replay_in_local_sql(tmp_path: Path, monkeypatch):
    local_engine = create_engine(f'sqlite:///{tmp_path/"uploaded.db"}', connect_args={'check_same_thread': False})
    monkeypatch.setattr(database, 'engine', local_engine)
    with TestClient(app) as client:
        sources = [("files", (p.name, p.read_bytes(), 'text/csv')) for p in sorted((FIXTURE_DIR/'toast').glob('*.csv'))]
        result = client.post('/api/upload/toast', files=sources)
        assert result.status_code == 200, result.text
        payload = result.json()
        assert payload['inserted'] == 28 and payload['duplicates'] == 0
        assert payload['metrics']['net_sales_minor'] == 59470
        replay = client.post('/api/upload/toast', files=sources)
        assert replay.status_code == 200
        assert replay.json()['inserted'] == 0
        assert replay.json()['duplicates'] == 28
        assert client.get('/api/metrics').json()['order_count'] == 28
    local_engine.dispose()


def test_upload_bad_csv_rejected_without_persistence(tmp_path: Path, monkeypatch):
    local_engine = create_engine(f'sqlite:///{tmp_path/"bad.db"}', connect_args={'check_same_thread': False})
    monkeypatch.setattr(database, 'engine', local_engine)
    with TestClient(app) as client:
        sources = [("files", (p.name, (p.read_bytes().replace(b'Order Id', b'Bad Header') if p.name=='OrderDetails.csv' else p.read_bytes()), 'text/csv')) for p in sorted((FIXTURE_DIR/'toast').glob('*.csv'))]
        bad = client.post('/api/upload/toast', files=sources)
        assert bad.status_code == 422
        assert 'Order Id' in bad.json()['detail']
        assert client.get('/api/metrics').json()['order_count'] == 0
        too_many = client.post('/api/upload/toast', files=[('files',('OrderDetails.csv',b'x','text/csv'))])
        assert too_many.status_code == 422
    local_engine.dispose()


def test_upload_square_and_financial_totals(tmp_path: Path, monkeypatch):
    local_engine = create_engine(f'sqlite:///{tmp_path/"square.db"}', connect_args={'check_same_thread': False})
    monkeypatch.setattr(database, 'engine', local_engine)
    with TestClient(app) as client:
        sources = [('files', (p.name, p.read_bytes(), 'application/json')) for p in sorted((FIXTURE_DIR/'square').glob('*.json'))]
        result = client.post('/api/upload/square', files=sources)
        assert result.status_code == 200, result.text
        assert result.json()['inserted'] == 28
        assert result.json()['metrics']['net_sales_minor'] == 65080
    local_engine.dispose()
