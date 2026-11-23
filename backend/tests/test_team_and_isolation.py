"""M2: roles, invites, account deletion, and a cross-tenant check on every signed-in route.

`ISOLATION` must list every route that depends on `authenticated_subject`. Adding a
route without listing it here fails `test_every_private_route_has_an_isolation_case`.
"""
from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import membership, saas
from app.local_auth import authenticated_subject
from app.main import app
from journey_support import Harness, harness  # noqa: F401

PLAN = {'title': 'ALPHA-PLAN-MARKER', 'objective': 'returning_guests', 'offer_type': 'percent', 'offer_value': 10,
        'target_redemptions': 40, 'reference_basket_minor': 2500, 'assumed_margin_percent': 35, 'notes': 'alpha'}

# "METHOD path": JSON body the *other* tenant sends (None = no body). {plan_id}/{invite_id}/{member_id}
# are filled with tenant A's real ids, so these must be refused.
ISOLATION = {
    'GET /api/saas/me': None, 'GET /api/saas/onboarding': None,
    'POST /api/saas/onboarding': {'stage': 2, 'plan_choice': 'sandbox'},
    'POST /api/saas/profile': {'name': 'Beta Diner', 'restaurant_type': 'cafe', 'goal': 'sales_visibility'},
    'POST /api/saas/demo-reset': None, 'POST /api/saas/analyst': {'question': 'Summarize my sales'},
    'GET /api/saas/billing/quote': None, 'POST /api/saas/billing/checkout': None,
    'POST /api/saas/billing/reconcile': {}, 'POST /api/saas/billing/portal': None,
    'GET /api/integrations/square/locations': None,
    'POST /api/integrations/square/locations/selection': {'location_ids': ['LOC_HARBOR']},
    'GET /api/integrations/square/status': None,
    'GET /api/integrations/square/health': None, 'GET /api/integrations/square/reconciliation': None,
    'POST /api/integrations/square/connect-developer-sandbox': None,
    'POST /api/integrations/square/oauth/start': None, 'POST /api/integrations/square/sync': None,
    'POST /api/integrations/square/disconnect': None,
    'POST /api/integrations/square/assisted-setup': {'provider': 'square', 'note': 'beta'},
    'GET /api/decisions/opportunities': None, 'GET /api/decisions/plans': None,
    'POST /api/decisions/plans': {**PLAN, 'title': 'Beta plan'},
    'POST /api/decisions/plans/{plan_id}/status': {'status': 'reviewed'},
    'GET /api/intelligence/brief': None, 'POST /api/intelligence/ask': {'question': 'What changed?'},
    'GET /api/launch/readiness': None, 'GET /api/team': None,
    'POST /api/team/invites': {'email': 'beta-friend@beta.test'},
    'POST /api/team/invites/{invite_id}/revoke': None,
    'POST /api/team/invites/accept': {'token': 'not-a-real-invite-token-000000'},
    'POST /api/team/members/{member_id}/remove': None,
    'POST /api/team/account/delete': {'confirm': 'Beta Diner'},
}


def _routes(routes):
    for r in routes:
        if isinstance(r, APIRoute):
            yield r
        elif hasattr(r, 'original_router'):
            yield from _routes(r.original_router.routes)


def _needs_auth(dependant) -> bool:
    return any(d.call is authenticated_subject or _needs_auth(d) for d in dependant.dependencies)


def test_every_private_route_has_an_isolation_case():
    private = {f'{sorted(r.methods)[0]} {r.path}' for r in _routes(app.routes) if _needs_auth(r.dependant)}
    assert private - set(ISOLATION) == set(), 'Add these signed-in routes to ISOLATION: ' + str(sorted(private - set(ISOLATION)))
    assert set(ISOLATION) - private == set(), 'Stale ISOLATION entries: ' + str(sorted(set(ISOLATION) - private))


def _setup_alpha(h: Harness) -> dict:
    h.sign_up('alpha@alpha.test')
    assert h.post('/api/saas/profile', {'name': 'Alpha Marker Bistro', 'restaurant_type': 'full_service',
                                        'goal': 'customer_retention'}).status_code == 200
    h.connect_oauth(); h.select_eligible()
    assert h.post('/api/integrations/square/sync').status_code == 200
    plan = h.post('/api/decisions/plans', PLAN).json()['plan']
    invite = h.post('/api/team/invites', {'email': 'alpha-manager@alpha.test'}).json()
    me = h.get('/api/team').json()
    return {'plan_id': plan['id'], 'invite_id': invite['id'], 'invite_url': invite['invite_url'],
            'member_id': me['members'][0]['id'], 'summary': h.get('/api/saas/me').json()['summary']}


def _snapshot(h: Harness) -> dict:
    return {'summary': h.get('/api/saas/me').json()['summary'],
            'connected': h.get('/api/integrations/square/status').json()['connected'],
            'plans': [(p['title'], p['status']) for p in h.get('/api/decisions/plans').json()['plans']],
            'team': h.get('/api/team').json()}


def test_other_tenant_cannot_read_or_change_anything(harness):
    alpha = harness
    ids = _setup_alpha(alpha)
    before = _snapshot(alpha)
    beta = Harness(TestClient(app), alpha.square)
    beta.sign_up('beta@beta.test')
    markers = ['Alpha Marker Bistro', 'ALPHA-PLAN-MARKER', 'alpha-manager@alpha.test', 'MOCK_MERCHANT_1',
               ids['plan_id'], ids['invite_id'], ids['member_id']]
    for route, body in ISOLATION.items():
        method, path = route.split(' ', 1)
        path = path.format(**ids)
        r = beta.get(path) if method == 'GET' else beta.post(path, body)
        if '{' in route.split(' ', 1)[1]:
            assert r.status_code in (403, 404), f'{route} with tenant A ids returned {r.status_code}'
        text = r.text
        leaked = [m for m in markers if m in text]
        assert not leaked, f'{route} leaked tenant A data to tenant B: {leaked}'
    assert _snapshot(alpha) == before, "Tenant B's requests changed tenant A's data"


def test_manager_can_use_but_not_administer(harness):
    owner = harness
    ids = _setup_alpha(owner)
    manager = Harness(TestClient(app), owner.square)
    manager.sign_up('manager@alpha.test')
    token = parse_qs(urlparse(ids['invite_url']).query)['token'][0]
    joined = manager.post('/api/team/invites/accept', {'token': token})
    assert joined.status_code == 200 and joined.json()['role'] == 'manager'
    # Same workspace, same numbers.
    assert manager.get('/api/saas/me').json()['summary'] == ids['summary']
    assert manager.post('/api/integrations/square/sync').status_code == 200
    assert manager.post('/api/decisions/plans', {**PLAN, 'title': 'Manager plan'}).status_code == 201
    for path, body in [('/api/integrations/square/disconnect', None), ('/api/integrations/square/oauth/start', None),
                       ('/api/integrations/square/locations/selection', {'location_ids': ['LOC_HARBOR']}),
                       ('/api/saas/billing/checkout', None), ('/api/saas/billing/portal', None),
                       ('/api/saas/profile', {'name': 'Hijacked', 'restaurant_type': 'cafe', 'goal': 'sales_visibility'}),
                       ('/api/team/invites', {'email': 'x@x.test'}),
                       (f"/api/team/members/{ids['member_id']}/remove", None)]:
        assert manager.post(path, body).status_code == 403, path
    # The invite link is single-use.
    third = Harness(TestClient(app), owner.square)
    third.sign_up('third@alpha.test')
    assert third.post('/api/team/invites/accept', {'token': token}).status_code == 404
    # Owner sees the manager and can remove them.
    team = owner.get('/api/team').json()
    mgr = next(m for m in team['members'] if m['role'] == 'manager')
    assert mgr['email'] == 'alpha-manager@alpha.test'
    assert owner.post(f"/api/team/members/{mgr['id']}/remove").status_code == 200
    assert manager.get('/api/saas/me').json()['summary']['orders'] == 0  # back to an empty workspace of their own


def test_joining_is_refused_when_you_already_have_data(harness):
    owner = harness
    ids = _setup_alpha(owner)
    token = parse_qs(urlparse(ids['invite_url']).query)['token'][0]
    other = Harness(TestClient(app), owner.square)
    other.sign_up('busy@other.test')
    other.post('/api/decisions/plans', PLAN)  # 409 without data, so give it a plan another way:
    other.post('/api/integrations/square/assisted-setup', {'provider': 'square', 'note': 'has data'})
    assert other.post('/api/team/invites/accept', {'token': token}).status_code == 409


def test_owner_deletes_workspace_and_everything_in_it(harness):
    h = harness
    _setup_alpha(h)
    assert h.post('/api/team/account/delete', {'confirm': 'wrong name'}).status_code == 422
    with Session(saas.engine) as db:
        w = db.scalar(select(saas.Workspace))
        w.subscription_status = 'active'; db.commit()
    assert h.post('/api/team/account/delete', {'confirm': 'Alpha Marker Bistro'}).status_code == 409
    with Session(saas.engine) as db:
        w = db.scalar(select(saas.Workspace)); w.subscription_status = 'canceled'; db.commit()
    r = h.post('/api/team/account/delete', {'confirm': 'Alpha Marker Bistro'})
    assert r.status_code == 200, r.text
    with Session(saas.engine) as db:
        for table in membership._workspace_tables() + [saas.Workspace.__table__]:
            assert db.scalar(select(func.count()).select_from(table)) == 0, f'{table.name} still has rows'
        from app.local_auth import LocalUser
        assert db.scalar(select(func.count()).select_from(LocalUser)) == 0
    # The session is gone with the account.
    assert h.get('/api/saas/me').status_code == 401


def test_concurrent_first_requests_share_one_workspace(tmp_path):
    """A new user's first page fires parallel requests; they must not create two workspaces or fail."""
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool
    from app.database import Base
    engine = create_engine('sqlite:///' + str(tmp_path / 'race.sqlite'), poolclass=NullPool,
                           connect_args={'check_same_thread': False, 'timeout': 10})
    Base.metadata.create_all(engine)

    def first_request(_):
        with Session(engine) as db:
            return membership.resolve(db, 'oidc:brand-new-user')[0].id

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(first_request, range(8)))
    assert len(set(ids)) == 1
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(saas.Workspace)) == 1
        assert db.scalar(select(func.count()).select_from(membership.WorkspaceMember)) == 1
