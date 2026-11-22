"""M1: the Square pipeline against the mock Square API, checked against its ground truth."""
from journey_support import harness  # noqa: F401  (pytest fixture)


def _summary(h):
    return h.get('/api/saas/me').json()['summary']


def test_oauth_connect_select_and_sync_match_square_truth(harness):
    h, truth = harness, harness.truth()
    h.sign_up(); h.connect_oauth()
    assert sorted(h.select_eligible()) == sorted(truth['eligible_location_ids'])
    run = h.post('/api/integrations/square/sync')
    assert run.status_code == 200, run.text
    body = run.json()
    assert body['inserted'] == truth['importable_orders']
    assert body['skipped'] == truth['skipped_open_orders']
    s = _summary(h)
    assert s['has_connected_source'] is True
    assert s['orders'] == truth['completed_orders']
    assert s['net_sales_minor'] == truth['completed_net_sales_minor']
    assert s['identified_orders'] == truth['identified_completed_orders']
    assert s['identified_customers'] == truth['distinct_customers']


def test_resync_is_idempotent(harness):
    h = harness
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    h.post('/api/integrations/square/sync')
    before = _summary(h)
    again = h.post('/api/integrations/square/sync').json()
    assert again['inserted'] == 0
    assert _summary(h) == before


def test_rate_limit_mid_sync_imports_nothing_then_recovers(harness):
    h, truth = harness, harness.truth()
    h.sign_up(); h.connect_oauth(); h.select_eligible()
    # Locations + first payments page succeed, then Square returns 429.
    h.square.post('/__mock/faults', json={'status': 429, 'count': 1, 'after': 2})
    failed = h.post('/api/integrations/square/sync')
    assert failed.status_code == 503
    assert _summary(h)['orders'] == 0  # no partial import
    status = h.get('/api/integrations/square/status').json()
    assert status['last_error'] and status['runs'][0]['status'] == 'failed'
    assert h.post('/api/integrations/square/sync').status_code == 200
    assert _summary(h)['orders'] == truth['completed_orders']


def test_ineligible_locations_cannot_be_selected(harness):
    h = harness
    h.sign_up(); h.connect_oauth()
    for loc in ('LOC_ONLINE', 'LOC_CLOSED'):
        r = h.post('/api/integrations/square/locations/selection', {'location_ids': [loc]})
        assert r.status_code in (409, 422), (loc, r.status_code)


def test_square_merchant_cannot_be_claimed_by_two_workspaces(harness):
    h = harness
    h.sign_up('first@harbor.test'); h.connect_oauth()
    h.post('/api/local-auth/logout')
    h.api.cookies.clear()
    h.sign_up('second@harbor.test')
    start = h.post('/api/integrations/square/oauth/start').json()['url']
    from urllib.parse import parse_qs, urlparse
    u = urlparse(start)
    q = parse_qs(urlparse(h.square.get(u.path + '?' + u.query, follow_redirects=False).headers['location']).query)
    cb = h.api.get('/api/integrations/square/oauth/callback', params={'code': q['code'][0], 'state': q['state'][0]},
                   follow_redirects=False)
    assert cb.status_code == 409
