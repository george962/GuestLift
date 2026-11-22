"""M1 contract: every required field the frontend's TypeScript types declare is present in the API response.

The types are parsed straight from the frontend source, so renaming a field on
either side without the other fails CI. Optional (`?`) fields are not required.
"""
import re
from pathlib import Path

import pytest

from journey_support import harness  # noqa: F401

FRONTEND = Path(__file__).resolve().parents[2] / 'frontend'


def ts_fields(file: str, type_name: str) -> dict[str, str]:
    """Top-level required fields of `type Name={...}` -> their TS type text."""
    src = (FRONTEND / file).read_text()
    m = re.search(r'type\s+' + type_name + r'\s*=\s*\{', src)
    assert m, f'{type_name} not found in {file}'
    i, depth, start = m.end(), 1, m.end()
    while depth:
        depth += {'{': 1, '}': -1}.get(src[i], 0)
        i += 1
    body, fields, depth, buf = src[start:i - 1], {}, 0, ''
    for ch in body + ';':
        if ch in '{[(<':
            depth += 1
        elif ch in '}])>':
            depth -= 1
        if ch == ';' and depth == 0:
            if ':' in buf:
                key, val = buf.split(':', 1)
                key = key.strip()
                if key and not key.endswith('?'):
                    fields[key] = val.strip()
            buf = ''
        else:
            buf += ch
    return fields


def assert_matches(payload: dict, file: str, type_name: str, where: str):
    missing = sorted(set(ts_fields(file, type_name)) - set(payload))
    assert not missing, f'{where} is missing fields the frontend type {type_name} ({file}) requires: {missing}'


def first(items, where):
    assert items, f'{where} returned no items to check'
    return items[0]


@pytest.fixture
def synced(harness):
    harness.sign_up(); harness.connect_oauth(); harness.select_eligible()
    assert harness.post('/api/integrations/square/sync').status_code == 200
    return harness


def test_account_summary_contract(synced):
    me = synced.get('/api/saas/me').json()
    f = 'components/private-dashboard.tsx'
    assert_matches(me, f, 'Account', '/api/saas/me')
    assert_matches(me['workspace'], f, 'Workspace', '/api/saas/me workspace')
    assert_matches(me['summary'], f, 'Summary', '/api/saas/me summary')
    assert_matches(first(me['summary']['locations'], 'locations'), f, 'LocationMetric', 'summary.locations[]')
    assert_matches(first(me['summary']['daily'], 'daily'), f, 'DailyMetric', 'summary.daily[]')


def test_connection_contract(synced):
    f = 'app/connections/page.tsx'
    status = synced.get('/api/integrations/square/status').json()
    assert_matches(status, f, 'Connection', '/api/integrations/square/status')
    assert_matches(first(status['runs'], 'runs'), f, 'Run', 'status.runs[]')
    assert_matches(synced.get('/api/integrations/square/locations').json(), f, 'SandboxLocations',
                   '/api/integrations/square/locations')


def test_brief_contract(synced):
    f = 'app/analyst/page.tsx'
    brief = synced.get('/api/intelligence/brief').json()
    assert_matches(brief, f, 'Brief', '/api/intelligence/brief')
    assert_matches(first(brief['nodes'], 'nodes'), f, 'Node', 'brief.nodes[]')
    assert_matches(first(brief['findings'], 'findings'), f, 'Finding', 'brief.findings[]')
    if brief['edges']:
        assert_matches(brief['edges'][0], f, 'Edge', 'brief.edges[]')


def test_opportunities_and_plans_contract(synced):
    data = synced.get('/api/decisions/opportunities').json()
    assert_matches(data, 'app/opportunities/page.tsx', 'Data', '/api/decisions/opportunities')
    assert_matches(first(data['opportunities'], 'opportunities'), 'app/opportunities/page.tsx', 'Opportunity',
                   'opportunities[]')
    created = synced.post('/api/decisions/plans', {
        'title': 'Win back lapsed regulars', 'objective': 'returning_guests', 'offer_type': 'percent',
        'offer_value': 10, 'target_redemptions': 40, 'reference_basket_minor': 2500,
        'assumed_margin_percent': 35, 'notes': 'contract test'})
    assert created.status_code == 201, created.text
    plan = first(synced.get('/api/decisions/plans').json()['plans'], 'plans')
    assert_matches(plan, 'app/experiments/page.tsx', 'Plan', '/api/decisions/plans')


def test_parser_reads_nested_and_optional_fields():
    assert set(ts_fields('app/connections/page.tsx', 'SandboxLocations')) == {
        'enabled', 'selected_count', 'selected_location_ids', 'notice', 'locations'}
