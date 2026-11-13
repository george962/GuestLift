"""Account, workspace, billing TEST mode and evidence-backed analyst.

Not a production merchant service. Square Sandbox transactions only; real seller uploads disabled.
Authentication is via local PostgreSQL sessions. No developer bypass or magic token exists.
"""
from __future__ import annotations
import csv
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import String, Integer, Text, ForeignKey, UniqueConstraint, select, delete
from sqlalchemy.orm import Mapped, mapped_column, Session

from .database import Base, engine
from .adapters import parse
from .insights import analyze_orders, answer_question
from .local_auth import authenticated_subject

router=APIRouter(prefix='/api/saas',tags=['SaaS foundation (test mode)'])

class Workspace(Base):
    __tablename__='saas_workspaces'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    owner_sub:Mapped[str]=mapped_column(String(160),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(120),default='My Restaurant')
    restaurant_type:Mapped[str]=mapped_column(String(35),default='fast_casual')
    goal:Mapped[str]=mapped_column(String(40),default='customer_retention')
    subscription_plan:Mapped[str]=mapped_column(String(20),default='sandbox')
    subscription_status:Mapped[str]=mapped_column(String(35),default='none')
    stripe_customer_id:Mapped[str|None]=mapped_column(String(120),nullable=True,unique=True)
    stripe_subscription_id:Mapped[str|None]=mapped_column(String(120),nullable=True,unique=True)
    created_at:Mapped[str]=mapped_column(String(40))

class WorkspaceOrder(Base):
    __tablename__='saas_workspace_demo_orders'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    workspace_id:Mapped[str]=mapped_column(ForeignKey('saas_workspaces.id'),index=True)
    provider:Mapped[str]=mapped_column(String(20))
    source_order_id:Mapped[str]=mapped_column(String(140))
    location_id:Mapped[str]=mapped_column(String(120))
    created_at:Mapped[str]=mapped_column(String(80))
    status:Mapped[str]=mapped_column(String(35))
    customer_id:Mapped[str|None]=mapped_column(String(140),nullable=True)
    net_sales_minor:Mapped[int]=mapped_column(Integer)
    discount_minor:Mapped[int]=mapped_column(Integer)
    campaign_code:Mapped[str|None]=mapped_column(String(100),nullable=True)
    campaign_discount_minor:Mapped[int]=mapped_column(Integer,default=0)
    __table_args__=(UniqueConstraint('workspace_id','provider','source_order_id',name='uq_saas_demo_order'),)

class BillingEvent(Base):
    __tablename__='saas_billing_events'
    stripe_event_id:Mapped[str]=mapped_column(String(160),primary_key=True)
    processed_at:Mapped[str]=mapped_column(String(40))

class ProfileUpdate(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    restaurant_type:str=Field(pattern='^(fast_casual|full_service|cafe|other)$')
    goal:str=Field(pattern='^(customer_retention|promotion_profit|sales_visibility)$')

class AnalystRequest(BaseModel):
    question:str=Field(min_length=3,max_length=500)

class CheckoutReconcileRequest(BaseModel):
    # Optional for purchases completed before v0.9.1 (old redirects lacked session IDs).
    session_id: str | None = Field(default=None, min_length=15, max_length=250, pattern=r'^cs_test_[a-zA-Z0-9_]+$')


def _now()->str:return datetime.now(timezone.utc).isoformat()



def _get_workspace(db:Session,owner_sub:str) -> Workspace:
    w=db.scalar(select(Workspace).where(Workspace.owner_sub==owner_sub))
    if w is None:
        w=Workspace(id=str(uuid.uuid4()),owner_sub=owner_sub,created_at=_now())
        db.add(w);db.commit();db.refresh(w)
        # No automatic demo seeding: a new account starts with zero connected data.
    return w


def _seed_workspace(db:Session,workspace_id:str) -> int:
    """Idempotent, uses exclusively packaged fictional fixture orders."""
    existing=db.scalar(select(WorkspaceOrder.id).where(WorkspaceOrder.workspace_id==workspace_id).limit(1))
    if existing is not None:return 0
    fixtures=Path(__file__).resolve().parent.parent/'fixtures'/'campaigns'/'Redemptions.csv'
    redemption_index={}
    with fixtures.open(newline='',encoding='utf-8') as handle:
        for r in csv.DictReader(handle):
            redemption_index[(r['provider'],r['source_order_id'])]=(r['campaign_id'],int(r['discount_minor']))
    inserted=0
    for provider in ('toast','square'):
        for o in parse(provider):
            match=redemption_index.get((provider,o.source_order_id))
            db.add(WorkspaceOrder(workspace_id=workspace_id,provider=provider,
                source_order_id=o.source_order_id,location_id=o.location_id,created_at=o.created_at,
                status=o.status,customer_id=o.customer_id,net_sales_minor=o.net_sales_minor,
                discount_minor=o.discount_minor,campaign_code=match[0] if match else None,
                campaign_discount_minor=match[1] if match else 0))
            inserted+=1
    db.commit()
    return inserted


def _workspace_json(w:Workspace)->dict:
    enabled=w.subscription_plan=='growth' and w.subscription_status in ('active','trialing')
    return {'workspace_id':w.id,'name':w.name,'restaurant_type':w.restaurant_type,'goal':w.goal,
      'plan':w.subscription_plan,'subscription_status':w.subscription_status,'ai_enabled':enabled,
      'source_mode':'square_sandbox_api_or_empty','payments_live':False,
      'has_billing_customer':bool(w.stripe_customer_id)}


def _scoped_summary(db: Session, w: Workspace) -> dict:
    """Only orders imported from this account's own authenticated Square Sandbox connection."""
    from .connections import SquareOrder, SquareConnection
    connection = db.scalar(select(SquareConnection).where(SquareConnection.workspace_id == w.id))
    rows = db.scalars(select(SquareOrder).where(SquareOrder.workspace_id == w.id)).all()
    data = [{'provider': 'square', 'location_id': o.location_id,
             'source_order_id': o.source_order_id, 'created_at': o.created_at,
             'status': o.status, 'customer_id': o.customer_id,
             'net_sales_minor': o.net_sales_minor, 'discount_minor': o.discount_minor,
             'campaign_code': None, 'campaign_discount_minor': 0} for o in rows]
    summary = analyze_orders(data)
    summary['data_origin'] = 'square_sandbox_api' if connection else 'no_connected_data'
    summary['has_connected_source'] = bool(connection)
    summary['methodology']['sales'] = (
        'Square Sandbox COMPLETED orders in the last 180 days: order total less recorded taxes/tips. '
        'Payments, refunds, and service charges are NOT fully reconciled; do not call this final net sales.'
    )
    summary['methodology']['repeat'] = (
        'Two or more observed completed orders with the same provider-scoped customer ID. '
        'Anonymous orders are excluded; no claim of measured retention or customer identity resolution.'
    )
    summary['methodology']['campaigns'] = 'No verified coupon attribution: Square Sandbox promotion import not connected.'
    return summary

@router.get('/config')
def public_configuration():
    """Report enabled integrations without disclosing credentials or account details."""
    stripe_key=os.getenv('STRIPE_SECRET_KEY','')
    price_id=os.getenv('STRIPE_GROWTH_PRICE_ID','')
    return {
        'auth_configured':True,
        'test_checkout_configured':stripe_key.startswith('sk_test_') and price_id.startswith('price_'),
        'test_webhook_configured':bool(os.getenv('STRIPE_WEBHOOK_SECRET')) and stripe_key.startswith('sk_test_'),
        'live_payments_enabled':False,
        'real_merchant_data_allowed':False,
        'mode':'local_postgres_auth_developer_only'
    }

@router.get('/me')
def me(sub:str=Depends(authenticated_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        return {'workspace':_workspace_json(w),'summary':_scoped_summary(db,w)}

@router.post('/profile')
def profile(profile:ProfileUpdate,sub:str=Depends(authenticated_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        w.name=profile.name.strip();w.restaurant_type=profile.restaurant_type;w.goal=profile.goal
        db.commit();db.refresh(w)
        return {'workspace':_workspace_json(w)}

@router.post('/demo-reset')
def reset_demo(sub: str = Depends(authenticated_subject)):
    """Deprecated: private accounts never receive fake sample orders."""
    raise HTTPException(status_code=410,
                        detail='Private workspaces no longer contain demo fixtures. Use the public free demo at /workspace.')

@router.post('/analyst')
def analyst(data:AnalystRequest,sub:str=Depends(authenticated_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        if not (w.subscription_plan=='growth' and w.subscription_status in ('active','trialing')):
            raise HTTPException(status_code=402,detail='Growth subscription required for account-based analyst. Free synthetic demo available without sign-in.')
        summary=_scoped_summary(db,w)
        if not summary['has_connected_source']:
            raise HTTPException(status_code=409, detail='Connect and sync Square Sandbox before using the account analyst.')
    result=answer_question(data.question,summary)
    # Optional actual language model uses aggregates only; never raw customer/order IDs.
    if os.getenv('GUESTLIFT_ENABLE_LLM')=='1' and os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL'):
        try:
            import json
            from openai import OpenAI
            client=OpenAI(timeout=15.0)
            safe={k:summary[k] for k in ('orders','net_sales_minor','discount_minor','identified_customers',
               'repeat_customers','repeat_customer_rate_percent','identification_coverage_percent','locations','campaigns')}
            response=client.responses.create(model=os.environ['OPENAI_MODEL'],store=False,
                instructions=('You are a read-only restaurant analyst analyzing SQUARE SANDBOX TEST data, never real merchant data. '
                 'Use ONLY supplied summary numbers. Never invent figures, infer identity, or claim causal lift. '
                 'Explain uncertainty and cite evidence keys verbatim. If data is insufficient, say so.'),
                input=json.dumps({'question':data.question,'verified_aggregate_metrics':safe,
                   'approved_rule_answer':result['answer']}))
            if response.output_text:
                result['answer']=response.output_text
                result['engine']='optional_llm_on_verified_aggregates'
        except Exception:
            result['llm_status']='unavailable; deterministic verified answer returned'
    return result

# The Stripe Checkout return is only a navigation event, not proof of payment.
# All paid entitlements are derived from server-to-server verification against
# Stripe test mode and the exact Price ID configured for this release.


def _stripe_client():
    secret = os.getenv('STRIPE_SECRET_KEY', '')
    if not secret.startswith('sk_test_'):
        raise HTTPException(status_code=503, detail='Stripe test mode is not configured.')
    import stripe
    stripe.api_key = secret
    return stripe


def _object_id(value):
    if isinstance(value, str):
        return value
    if value is not None and hasattr(value, 'get'):
        return value.get('id')
    return None


def _subscription_has_growth_price(subscription) -> bool:
    expected = os.getenv('STRIPE_GROWTH_PRICE_ID', '')
    if not expected.startswith('price_'):
        return False
    items = (subscription.get('items') or {}).get('data') or []
    return any(_object_id(line.get('price')) == expected for line in items)


def _apply_verified_subscription(db: Session, w: Workspace, subscription, customer_id: str):
    sub_id = _object_id(subscription.get('id'))
    if not sub_id or not sub_id.startswith('sub_'):
        raise HTTPException(status_code=409, detail='Stripe did not return a subscription identifier.')
    if subscription.get('livemode') is not False:
        raise HTTPException(status_code=409, detail='Only Stripe test subscriptions are accepted.')
    if (subscription.get('metadata') or {}).get('workspace_id') != w.id:
        raise HTTPException(status_code=409, detail='The subscription does not belong to this workspace.')
    if not _subscription_has_growth_price(subscription):
        raise HTTPException(status_code=409, detail='Subscription is not for the configured Growth price.')
    if not customer_id or _object_id(subscription.get('customer')) != customer_id:
        raise HTTPException(status_code=409, detail='Stripe customer does not match the subscription.')
    if w.stripe_customer_id and w.stripe_customer_id != customer_id:
        raise HTTPException(status_code=409, detail='A different Stripe customer is already linked to this workspace.')
    if (w.stripe_subscription_id and w.stripe_subscription_id != sub_id
            and w.subscription_status in ('active', 'trialing')):
        raise HTTPException(status_code=409, detail='An existing active subscription must be reviewed first.')
    status = subscription.get('status', 'unknown')
    w.stripe_customer_id = customer_id
    w.stripe_subscription_id = sub_id
    w.subscription_status = status
    w.subscription_plan = 'growth' if status in ('active', 'trialing') else 'sandbox'
    db.commit()
    db.refresh(w)
    return {'verified': True, 'workspace': _workspace_json(w),
            'access_granted': status in ('active', 'trialing')}


def _reconcile_checkout(db: Session, w: Workspace, stripe, session_id: str):
    if not session_id.startswith('cs_test_'):
        raise HTTPException(status_code=422, detail='A Stripe test Checkout session is required.')
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail='Could not verify Checkout with Stripe. Try again.') from exc
    if session.get('livemode') is not False or session.get('mode') != 'subscription':
        raise HTTPException(status_code=409, detail='Not a test-mode subscription Checkout.')
    if session.get('client_reference_id') != w.id:
        raise HTTPException(status_code=403, detail='This Checkout session belongs to another workspace.')
    if session.get('status') != 'complete':
        return {'verified': False, 'pending': True,
                'message': 'Checkout has not completed.', 'workspace': _workspace_json(w)}
    if session.get('payment_status') not in ('paid', 'no_payment_required'):
        return {'verified': False, 'pending': True,
                'message': 'Waiting for Stripe to confirm the payment.', 'workspace': _workspace_json(w)}
    customer_id = _object_id(session.get('customer'))
    sub_id = _object_id(session.get('subscription'))
    if not customer_id or not sub_id:
        return {'verified': False, 'pending': True,
                'message': 'Waiting for Stripe to create the subscription.', 'workspace': _workspace_json(w)}
    try:
        subscription = stripe.Subscription.retrieve(sub_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail='Could not verify subscription with Stripe. Try again.') from exc
    return _apply_verified_subscription(db, w, subscription, customer_id)


def _recent_owner_checkouts(stripe, workspace_id: str):
    """Find recent server-issued Checkout sessions for this local test workspace."""
    try:
        sessions = stripe.checkout.Session.list(limit=100)
    except Exception as exc:
        raise HTTPException(status_code=502, detail='Could not check existing Stripe purchases. Retry before paying again.') from exc
    return [entry for entry in (sessions.get('data') or [])
            if entry.get('client_reference_id') == workspace_id
            and entry.get('mode') == 'subscription'
            and entry.get('status') == 'complete'
            and entry.get('livemode') is False]


@router.post('/billing/checkout')
def checkout(sub: str = Depends(authenticated_subject)):
    stripe = _stripe_client()
    price = os.getenv('STRIPE_GROWTH_PRICE_ID', '')
    base = os.getenv('GUESTLIFT_APP_URL', 'http://localhost:3000').rstrip('/')
    if not price.startswith('price_'):
        raise HTTPException(status_code=503, detail='Stripe Growth test price is not configured.')
    with Session(engine) as db:
        w = _get_workspace(db, sub)
        if w.subscription_plan == 'growth' and w.subscription_status in ('active', 'trialing'):
            raise HTTPException(status_code=409, detail='Already subscribed; use the customer portal.')
        # Protect local testers from duplicate subscriptions after a missed webhook.
        # Verify the existing Checkout first; a verified canceled subscription may be renewed.
        for recent in _recent_owner_checkouts(stripe, w.id):
            previous = _reconcile_checkout(db, w, stripe, recent['id'])
            if previous.get('access_granted') or previous.get('pending'):
                raise HTTPException(status_code=409,
                    detail='A previous Stripe Checkout already exists. Refresh Billing or use Find my completed test checkout instead of paying twice.')
            break  # The most recent completed test Checkout was canceled/ineligible.
        kwargs = {
            'mode': 'subscription',
            'line_items': [{'price': price, 'quantity': 1}],
            # Stripe replaces this literal placeholder with its own session ID.
            'success_url': base + '/billing/success?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': base + '/billing?checkout=canceled',
            'client_reference_id': w.id,
            'subscription_data': {'metadata': {'workspace_id': w.id}},
        }
        if w.stripe_customer_id:
            kwargs['customer'] = w.stripe_customer_id
        try:
            session = stripe.checkout.Session.create(**kwargs)
        except Exception as exc:
            raise HTTPException(status_code=502, detail='Stripe could not start checkout. Please retry.') from exc
    return {'url': session.url, 'mode': 'stripe_test'}


@router.post('/billing/reconcile')
def reconcile_checkout(payload: CheckoutReconcileRequest, sub: str = Depends(authenticated_subject)):
    """Reconcile a completed test purchase against Stripe using the signed-in owner.

    The no-session-ID case repairs purchases made with the old redirect URL:
    find a matching recent Checkout by server-issued client_reference_id, then
    independently verify the subscription, price, merchant and current status.
    """
    stripe = _stripe_client()
    with Session(engine) as db:
        w = _get_workspace(db, sub)
        if payload.session_id:
            return _reconcile_checkout(db, w, stripe, payload.session_id)
        for session in _recent_owner_checkouts(stripe, w.id):
            return _reconcile_checkout(db, w, stripe, session['id'])
        raise HTTPException(status_code=404,
                            detail='No completed test Checkout for this account was found among the 100 most recent. Check that checkout used this same local account and Stripe Sandbox.')


@router.post('/billing/portal')
def portal(sub: str = Depends(authenticated_subject)):
    stripe = _stripe_client()
    with Session(engine) as db:
        w = _get_workspace(db, sub)
        if not w.stripe_customer_id:
            raise HTTPException(status_code=404, detail='No verified Stripe customer is linked to this workspace.')
        try:
            session = stripe.billing_portal.Session.create(
                customer=w.stripe_customer_id,
                return_url=os.getenv('GUESTLIFT_APP_URL', 'http://localhost:3000').rstrip('/') + '/billing')
        except Exception as exc:
            raise HTTPException(status_code=502, detail='Could not open the Stripe customer portal.') from exc
    return {'url': session.url}


@router.post('/billing/webhook')
async def webhook(request: Request):
    secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    if not secret:
        raise HTTPException(status_code=503, detail='Stripe webhook secret is not configured.')
    stripe = _stripe_client()
    payload = await request.body()
    sig = request.headers.get('stripe-signature', '')
    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail='Invalid Stripe webhook signature.') from exc
    if event.get('livemode') is not False:
        raise HTTPException(status_code=400, detail='Live events are not accepted.')
    event_id, kind, obj = event['id'], event['type'], event['data']['object']
    with Session(engine) as db:
        if db.get(BillingEvent, event_id):
            return {'received': True, 'duplicate': True}
        if kind == 'checkout.session.completed' and obj.get('mode') == 'subscription':
            w = db.get(Workspace, obj.get('client_reference_id'))
            if w:
                # Verify against Stripe's API rather than granting access on the event or redirect alone.
                _reconcile_checkout(db, w, stripe, obj['id'])
        elif kind in ('customer.subscription.created', 'customer.subscription.updated',
                      'customer.subscription.deleted'):
            meta = obj.get('metadata') or {}
            workspace_id = meta.get('workspace_id')
            customer_id = _object_id(obj.get('customer'))
            w = db.get(Workspace, workspace_id) if workspace_id else None
            if not w and customer_id:
                w = db.scalar(select(Workspace).where(Workspace.stripe_customer_id == customer_id))
            event_sub = _object_id(obj.get('id'))
            if w and event_sub and (w.stripe_subscription_id in (None, event_sub)
                                     or w.subscription_status not in ('active', 'trialing')):
                try:
                    # Current Stripe status avoids stale, out-of-order webhooks reactivating access.
                    current = stripe.Subscription.retrieve(event_sub)
                except Exception as exc:
                    raise HTTPException(status_code=502, detail='Unable to verify Stripe subscription.') from exc
                _apply_verified_subscription(db, w, current, customer_id)
        db.add(BillingEvent(stripe_event_id=event_id, processed_at=_now()))
        db.commit()
    return {'received': True}
