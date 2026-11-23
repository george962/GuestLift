"""M5 against Stripe's real TEST mode, with a test clock to move time.

Runs only with RUN_STRIPE_TESTS=1 and a sk_test_ key (STRIPE_SECRET_KEY, STRIPE_GROWTH_PRICE_ID).
Creates a test clock, customer and subscription in the Stripe test account and deletes the clock
(and everything attached) at the end. Webhooks aren't delivered here; the test uses the same
retrieve-then-verify path the webhook handler uses.
"""
from __future__ import annotations

import os
import time

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import billing, connections, saas
from journey_support import harness  # noqa: F401

pytestmark = pytest.mark.skipif(
    os.getenv('RUN_STRIPE_TESTS') != '1' or not os.getenv('STRIPE_SECRET_KEY', '').startswith('sk_test_'),
    reason='set RUN_STRIPE_TESTS=1 with Stripe TEST keys to run against Stripe')


def _wait_ready(stripe, clock_id):
    for _ in range(90):
        if stripe.test_helpers.TestClock.retrieve(clock_id).status == 'ready':
            return
        time.sleep(2)
    raise AssertionError('Stripe test clock did not finish advancing')


def _state(stripe, sub_id, customer_id):
    with Session(saas.engine) as db:
        w = db.scalar(select(saas.Workspace))
        saas._apply_verified_subscription(db, w, stripe.Subscription.retrieve(sub_id), customer_id)
        return billing.entitlement(w)


def test_subscription_lifecycle_on_stripe_test_clock(harness, monkeypatch):
    import stripe
    stripe.api_key = os.environ['STRIPE_SECRET_KEY']
    price = os.environ['STRIPE_GROWTH_PRICE_ID']
    h = harness
    h.sign_up(); h.connect_oauth(); ids = h.select_eligible()
    assert h.post('/api/integrations/square/sync').status_code == 200
    from app.location_entitlements import snapshot
    clock = stripe.test_helpers.TestClock.create(frozen_time=int(time.time()), name='tablesignal-m5-ci')
    try:
        customer = stripe.Customer.create(test_clock=clock.id, payment_method='pm_card_visa',
                                          invoice_settings={'default_payment_method': 'pm_card_visa'})
        with Session(saas.engine) as db:
            w = db.scalar(select(saas.Workspace))
            snap = snapshot(db, w.id, db.scalar(select(connections.SquareConnection)).merchant_id)
            w.stripe_customer_id = customer.id
            db.commit()
            wid = w.id
        sub = stripe.Subscription.create(customer=customer.id, items=[{'price': price, 'quantity': snap['quantity']}],
                                         metadata={'workspace_id': wid, 'sandbox_location_digest': snap['digest'],
                                                   'sandbox_location_quantity': str(snap['quantity'])})
        assert sub.status == 'active'
        assert _state(stripe, sub.id, customer.id)['state'] == 'active'

        # Remove a location: preview shows a prorated credit, confirm changes Stripe and our selection together.
        preview = h.post('/api/saas/billing/locations/preview', {'location_ids': ids[:1]})
        assert preview.status_code == 200, preview.text
        p = preview.json()
        assert p['subscribed'] and p['quantity_before'] == 2 and p['quantity_after'] == 1 and p['prorated_change_minor'] < 0
        confirm = h.post('/api/saas/billing/locations/confirm', {'location_ids': ids[:1], 'proration_date': p['proration_date']})
        assert confirm.status_code == 200, confirm.text
        assert stripe.Subscription.retrieve(sub.id)['items']['data'][0]['quantity'] == 1
        assert h.get('/api/integrations/square/locations').json()['selected_count'] == 1

        # Cancel at period end keeps access; undoing it restores a normal subscription.
        stripe.Subscription.modify(sub.id, cancel_at_period_end=True)
        assert _state(stripe, sub.id, customer.id)['state'] == 'canceling'
        stripe.Subscription.modify(sub.id, cancel_at_period_end=False)
        assert _state(stripe, sub.id, customer.id)['state'] == 'active'

        # The card starts failing. The location credit above pays the first renewal, so move two months
        # ahead: the second renewal fails and the grace period begins.
        failing = stripe.PaymentMethod.attach('pm_card_chargeCustomerFail', customer=customer.id)
        stripe.Customer.modify(customer.id, invoice_settings={'default_payment_method': failing.id})
        start = stripe.test_helpers.TestClock.retrieve(clock.id).frozen_time
        for days in (33, 64):  # a clock moves at most two billing periods per step
            stripe.test_helpers.TestClock.advance(clock.id, frozen_time=start + days * 86400)
            _wait_ready(stripe, clock.id)
        e = _state(stripe, sub.id, customer.id)
        assert e['state'] == 'past_due' and e['access'] == 'full', e

        # Canceled: numbers stay visible, paid features stop.
        stripe.Subscription.cancel(sub.id)
        e = _state(stripe, sub.id, customer.id)
        assert e['state'] == 'read_only' and e['access'] == 'read_only'
    finally:
        stripe.test_helpers.TestClock.delete(clock.id)
