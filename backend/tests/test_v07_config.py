"""Test-only config discovery must never disclose secrets or enable live payment mode."""
from fastapi.testclient import TestClient
from app.main import app

def test_public_configuration_says_live_charges_are_disabled(monkeypatch):
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_test_fake')
    monkeypatch.setenv('STRIPE_GROWTH_PRICE_ID','price_fake')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_fake')
    monkeypatch.setenv('SUPABASE_URL','https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY','sb_publishable_fake')
    with TestClient(app) as client:
        r=client.get('/api/saas/config')
    assert r.status_code==200
    body=r.json()
    assert body['auth_configured'] is True
    assert body['test_checkout_configured'] is True
    assert body['test_webhook_configured'] is True
    assert body['live_payments_enabled'] is False
    assert body['real_merchant_data_allowed'] is False
    assert 'sk_test_fake' not in str(body) and 'whsec_fake' not in str(body)

def test_live_key_does_not_activate_test_checkout(monkeypatch):
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_should_not_be_accepted')
    monkeypatch.setenv('STRIPE_GROWTH_PRICE_ID','price_fake')
    with TestClient(app) as client:
        r=client.get('/api/saas/config')
        checkout=client.post('/api/saas/billing/checkout')
    assert r.json()['test_checkout_configured'] is False
    assert checkout.status_code in (401,503)
