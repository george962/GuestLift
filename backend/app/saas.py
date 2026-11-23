"""Account, workspace, billing TEST mode and evidence-backed analyst.

Not a production merchant service. Square Sandbox transactions only; real seller uploads disabled.
Authentication is via local PostgreSQL sessions. No developer bypass or magic token exists.
"""
from __future__ import annotations
import csv
import os
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, String, Integer, Text, ForeignKey, UniqueConstraint, select, delete, false as sa_false
from sqlalchemy.orm import Mapped, mapped_column, Session

from . import config
from .database import Base, engine
from .adapters import parse
from .insights import analyze_orders, answer_question
from .local_auth import authenticated_subject
from .membership import owner_subject
from .billing import entitlement, paid_subject
from .rate_limit import ai_question_subject

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
    # M5 billing state (see app/billing.py)
    trial_started_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    trial_ends_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    current_period_end:Mapped[int|None]=mapped_column(Integer,nullable=True)
    cancel_at_period_end:Mapped[bool]=mapped_column(Boolean,default=False,server_default=sa_false())
    payment_failed_at:Mapped[str|None]=mapped_column(String(40),nullable=True)

class OnboardingProgress(Base):
    __tablename__ = 'tablesignal_onboarding_progress'
    workspace_id:Mapped[str]=mapped_column(ForeignKey('saas_workspaces.id'),primary_key=True)
    stage:Mapped[int]=mapped_column(Integer,default=1)
    plan_choice:Mapped[str]=mapped_column(String(20),default='not_chosen')
    updated_at:Mapped[str]=mapped_column(String(40))

class OnboardingUpdate(BaseModel):
    stage:int=Field(ge=1,le=3)
    plan_choice:str=Field(pattern='^(not_chosen|sandbox|growth)$')

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
    """The caller's workspace (as owner or member); created on first sign-in. See membership.resolve."""
    from .membership import resolve
    return resolve(db,owner_sub)[0]


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
    access=entitlement(w)
    enabled=access['access']=='full'
    return {'entitlement':access,'workspace_id':w.id,'name':w.name,'restaurant_type':w.restaurant_type,'goal':w.goal,
      'plan':w.subscription_plan,'subscription_status':w.subscription_status,'ai_enabled':enabled,
      'source_mode':'square_sandbox_api_or_empty','payments_live':False,
      'has_billing_customer':bool(w.stripe_customer_id)}


def _scoped_summary(db: Session, w: Workspace) -> dict:
    """Only orders imported from this account's own authenticated Square Sandbox connection."""
    from .connections import SquareOrder, SquareConnection
    connection = db.scalar(select(SquareConnection).where(SquareConnection.workspace_id == w.id))
    if os.getenv('TABLESIGNAL_SANDBOX_LOCATION_BILLING', '0') == '1':
        from .location_entitlements import selected_rows
        selected = [x.location_id for x in selected_rows(db, w.id, connection.merchant_id)] if connection else []
        rows = db.scalars(select(SquareOrder).where(
            SquareOrder.workspace_id == w.id, SquareOrder.location_id.in_(selected))).all() if selected else []
    else:
        rows = db.scalars(select(SquareOrder).where(SquareOrder.workspace_id == w.id)).all()
    from .square_sync import SquareRefund
    location_ids = {o.location_id for o in rows} if os.getenv('TABLESIGNAL_SANDBOX_LOCATION_BILLING', '0') != '1' else set(selected)
    refund_rows = db.scalars(select(SquareRefund).where(SquareRefund.workspace_id == w.id)).all()
    refunds = [{'location_id': f.location_id, 'local_date': f.local_date, 'amount_minor': f.amount_minor}
               for f in refund_rows if not location_ids or f.location_id in location_ids]
    data = [{'provider': 'square', 'location_id': o.location_id,
             'source_order_id': o.source_order_id, 'created_at': o.created_at, 'local_date': o.local_date,
             'status': o.status, 'customer_id': o.customer_id,
             'net_sales_minor': o.net_sales_minor, 'discount_minor': o.discount_minor,
             'campaign_code': None, 'campaign_discount_minor': 0} for o in rows]
    summary = analyze_orders(data, refunds)
    summary['data_origin'] = 'square_api' if connection else 'no_connected_data'
    summary['has_connected_source'] = bool(connection)
    summary['methodology']['sales'] = (
        'Completed Square orders: order total less tax, tips and service charges, minus completed refunds '
        'on the day they happened. Days follow each location\'s time zone. Gift cards and comps are not separated.'
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

@router.get('/onboarding')
def read_onboarding(sub:str=Depends(authenticated_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        progress=db.get(OnboardingProgress,w.id)
        if progress:
            return {'stage':progress.stage,'plan_choice':progress.plan_choice}
        # Existing v0.9 profiles get a sensible starting point.
        return {'stage':2 if w.name!='My Restaurant' else 1,'plan_choice':'not_chosen'}

@router.post('/onboarding')
def save_onboarding(payload:OnboardingUpdate,sub:str=Depends(owner_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        if payload.stage>1 and w.name=='My Restaurant':
            raise HTTPException(status_code=409,detail='Save your restaurant profile first.')
        if payload.stage==3 and payload.plan_choice=='not_chosen':
            raise HTTPException(status_code=422,detail='Choose a plan first.')
        progress=db.get(OnboardingProgress,w.id)
        if not progress:
            progress=OnboardingProgress(workspace_id=w.id,stage=payload.stage,
                   plan_choice=payload.plan_choice,updated_at=_now());db.add(progress)
        else:
            progress.stage=payload.stage;progress.plan_choice=payload.plan_choice;progress.updated_at=_now()
        db.commit()
        return {'stage':progress.stage,'plan_choice':progress.plan_choice}

@router.post('/profile')
def profile(profile:ProfileUpdate,sub:str=Depends(owner_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        w.name=profile.name.strip();w.restaurant_type=profile.restaurant_type;w.goal=profile.goal
        progress=db.get(OnboardingProgress,w.id)
        if not progress:
            db.add(OnboardingProgress(workspace_id=w.id,stage=2,plan_choice='not_chosen',updated_at=_now()))
        elif progress.stage<2:
            progress.stage=2;progress.updated_at=_now()
        db.commit();db.refresh(w)
        return {'workspace':_workspace_json(w)}

@router.post('/demo-reset')
def reset_demo(sub: str = Depends(authenticated_subject)):
    """Deprecated: private accounts never receive fake sample orders."""
    raise HTTPException(status_code=410,
                        detail='Private workspaces no longer contain demo fixtures. Use the public free demo at /workspace.')

@router.post('/analyst')
def analyst(data:AnalystRequest,_paid:str=Depends(paid_subject),sub:str=Depends(ai_question_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
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


def _stripe_payload(value):
    if isinstance(value, dict): return value
    converter=getattr(value, 'to_dict', None)
    if callable(converter):
        result=converter()
        if isinstance(result, dict): return result
    raise HTTPException(status_code=502, detail='Unexpected Stripe API response format.')

def _object_id(value):
    if isinstance(value, str): return value
    if value is None: return None
    return _stripe_payload(value).get('id')


def _subscription_has_growth_price(subscription) -> bool:
    expected = os.getenv('STRIPE_GROWTH_PRICE_ID', '')
    if not expected.startswith('price_'):
        return False
    items = (subscription.get('items') or {}).get('data') or []
    return any(_object_id(line.get('price')) == expected for line in items)


def _apply_verified_subscription(db: Session, w: Workspace, subscription, customer_id: str):
    subscription=_stripe_payload(subscription)
    sub_id = _object_id(subscription.get('id'))
    if not sub_id or not sub_id.startswith('sub_'):
        raise HTTPException(status_code=409, detail='Stripe did not return a subscription identifier.')
    if subscription.get('livemode') is not False:
        raise HTTPException(status_code=409, detail='Only Stripe test subscriptions are accepted.')
    if (subscription.get('metadata') or {}).get('workspace_id') != w.id:
        raise HTTPException(status_code=409, detail='The subscription does not belong to this workspace.')
    if not _subscription_has_growth_price(subscription):
        raise HTTPException(status_code=409, detail='Subscription is not for the configured Growth price.')
    if os.getenv('TABLESIGNAL_SANDBOX_LOCATION_BILLING', '0') == '1':
        from .connections import _connection
        from .location_entitlements import snapshot
        conn = _connection(db, w.id)
        if not conn:
            raise HTTPException(status_code=409, detail='A connected Sandbox merchant is required for billing verification.')
        item = snapshot(db, w.id, conn.merchant_id)
        meta = subscription.get('metadata') or {}
        lines = (subscription.get('items') or {}).get('data') or []
        expected_price = os.getenv('STRIPE_GROWTH_PRICE_ID', '')
        verified_qty = sum(int(line.get('quantity') or 0) for line in lines
                           if _object_id(line.get('price')) == expected_price)
        if (not item['quantity'] or meta.get('sandbox_location_digest') != item['digest']
                or str(item['quantity']) != str(meta.get('sandbox_location_quantity'))
                or verified_qty != item['quantity']
                or any(_object_id(line.get('price')) != expected_price for line in lines)):
            raise HTTPException(status_code=409, detail='Stripe TEST quantity or selected locations do not match the server-verified Sandbox selection.')
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
    w.subscription_plan = 'growth' if status in ('active', 'trialing', 'past_due') else 'sandbox'
    w.cancel_at_period_end = bool(subscription.get('cancel_at_period_end'))
    # Newer Stripe API versions report the period on each subscription item.
    ends = [subscription.get('current_period_end')] + [line.get('current_period_end') for line in
            ((subscription.get('items') or {}).get('data') or [])]
    ends = [int(x) for x in ends if isinstance(x, int)]
    w.current_period_end = max(ends) if ends else w.current_period_end
    if status in ('active', 'trialing'):
        w.payment_failed_at = None
    elif status == 'past_due' and not w.payment_failed_at:
        w.payment_failed_at = _now()
    db.commit()
    db.refresh(w)
    return {'verified': True, 'workspace': _workspace_json(w),
            'access_granted': status in ('active', 'trialing')}


def _reconcile_checkout(db: Session, w: Workspace, stripe, session_id: str):
    if not session_id.startswith('cs_test_'):
        raise HTTPException(status_code=422, detail='A Stripe test Checkout session is required.')
    try:
        session = _stripe_payload(stripe.checkout.Session.retrieve(session_id))
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
        subscription = _stripe_payload(stripe.Subscription.retrieve(sub_id))
    except Exception as exc:
        raise HTTPException(status_code=502, detail='Could not verify subscription with Stripe. Try again.') from exc
    return _apply_verified_subscription(db, w, subscription, customer_id)


def _recent_owner_checkouts(stripe, workspace_id: str):
    """Find recent server-issued Checkout sessions for this local test workspace."""
    try:
        sessions = _stripe_payload(stripe.checkout.Session.list(limit=100))
    except Exception as exc:
        raise HTTPException(status_code=502, detail='Could not check existing Stripe purchases. Retry before paying again.') from exc
    return [entry for entry in (sessions.get('data') or [])
            if entry.get('client_reference_id') == workspace_id
            and entry.get('mode') == 'subscription'
            and entry.get('status') == 'complete'
            and entry.get('livemode') is False]


@router.get('/billing/quote')
def sandbox_location_quote(sub: str = Depends(authenticated_subject)):
    """Read-only test selection preview; actual Stripe TEST price is configured separately."""
    from .location_entitlements import selection_enabled, snapshot
    from .location_billing_rules import MONTHLY_LOCATION_PRICE_MINOR
    from .connections import _connection
    unit, source = MONTHLY_LOCATION_PRICE_MINOR, 'proposal'
    if os.getenv('STRIPE_SECRET_KEY', '').startswith('sk_test_') and os.getenv('STRIPE_GROWTH_PRICE_ID', '').startswith('price_'):
        try:
            unit, source = _growth_unit_price(_stripe_client()), 'stripe'
        except HTTPException:
            pass  # fall back to the proposal price; checkout still uses Stripe's
    with Session(engine) as db:
        w = _get_workspace(db, sub)
        conn = _connection(db, w.id)
        item = snapshot(db, w.id, conn.merchant_id) if conn else {'quantity': 0, 'ids': []}
        return {'enabled': selection_enabled(), 'environment': 'sandbox',
                'selected_quantity': item['quantity'] if selection_enabled() else 0,
                'selected_location_ids': item['ids'] if selection_enabled() else [],
                'proposed_monthly_subtotal_minor': item['quantity'] * unit if selection_enabled() else 0,
                'unit_amount_minor': unit, 'price_source': source,
                'currency': 'USD', 'real_payments_enabled': False,
                'notice': 'Price per monitored location per month, from Stripe.' if source == 'stripe'
                          else 'Proposed price; Stripe is not configured here. No live charges are enabled.'}


@router.post('/billing/checkout')
def checkout(sub: str = Depends(owner_subject)):
    stripe = _stripe_client()
    price = os.getenv('STRIPE_GROWTH_PRICE_ID', '')
    base = config.app_url()
    if not price.startswith('price_'):
        raise HTTPException(status_code=503, detail='Stripe Growth test price is not configured.')
    with Session(engine) as db:
        w = _get_workspace(db, sub)
        if entitlement(w)['state'] in ('active', 'canceling', 'past_due'):
            raise HTTPException(status_code=409, detail='Already subscribed; use Manage billing to change your plan or card.')
        # Protect local testers from duplicate subscriptions after a missed webhook.
        # Verify the existing Checkout first; a verified canceled subscription may be renewed.
        for recent in _recent_owner_checkouts(stripe, w.id):
            previous = _reconcile_checkout(db, w, stripe, recent['id'])
            if previous.get('access_granted') or previous.get('pending'):
                raise HTTPException(status_code=409,
                    detail='A previous Stripe Checkout already exists. Refresh Billing or use Find my completed test checkout instead of paying twice.')
            break  # The most recent completed test Checkout was canceled/ineligible.
        quantity = 1
        billing_meta = {'workspace_id': w.id}
        if os.getenv('TABLESIGNAL_SANDBOX_LOCATION_BILLING', '0') == '1':
            from .connections import _connection, _refresh_oauth, _merchant_from_locations
            from .location_entitlements import snapshot, eligible_location
            conn = _connection(db, w.id)
            if conn is None:
                raise HTTPException(409, 'Connect Square Sandbox and select locations before checkout.')
            token = _refresh_oauth(conn, db)
            merchant, provider_locations = _merchant_from_locations(token)
            if merchant != conn.merchant_id:
                raise HTTPException(409, 'Sandbox merchant changed. Reconnect before checkout.')
            item = snapshot(db, w.id, merchant)
            eligible_ids = {str(loc['id']) for loc in provider_locations if eligible_location(loc)}
            if item['quantity'] == 0 or not set(item['ids']).issubset(eligible_ids):
                raise HTTPException(409, 'Select eligible Sandbox locations before checkout.')
            quantity = item['quantity']
            billing_meta.update(sandbox_location_digest=item['digest'],
                                sandbox_location_quantity=str(quantity))
        kwargs = {
            'mode': 'subscription',
            'line_items': [{'price': price, 'quantity': quantity}],
            # Stripe replaces this literal placeholder with its own session ID.
            'success_url': base + '/billing?checkout=return&session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': base + '/billing?checkout=canceled',
            'client_reference_id': w.id,
            'subscription_data': {'metadata': billing_meta},
        }
        if w.stripe_customer_id:
            kwargs['customer'] = w.stripe_customer_id
        try:
            session = stripe.checkout.Session.create(**kwargs)
        except Exception as exc:
            raise HTTPException(status_code=502, detail='Stripe could not start checkout. Please retry.') from exc
    return {'url': session.url, 'mode': 'stripe_test'}


@router.post('/billing/reconcile')
def reconcile_checkout(payload: CheckoutReconcileRequest, sub: str = Depends(owner_subject)):
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
def portal(sub: str = Depends(owner_subject)):
    stripe = _stripe_client()
    with Session(engine) as db:
        w = _get_workspace(db, sub)
        if not w.stripe_customer_id:
            raise HTTPException(status_code=404, detail='No verified Stripe customer is linked to this workspace.')
        try:
            session = stripe.billing_portal.Session.create(
                customer=w.stripe_customer_id,
                return_url=config.app_url() + '/billing')
        except Exception as exc:
            raise HTTPException(status_code=502, detail='Could not open the Stripe customer portal.') from exc
    return {'url': session.url}


class LocationChange(BaseModel):
    location_ids: list[str] = Field(min_length=1, max_length=25)
    proration_date: int | None = None


def _growth_unit_price(stripe) -> int:
    try:
        price = _stripe_payload(stripe.Price.retrieve(os.getenv('STRIPE_GROWTH_PRICE_ID', '')))
    except Exception as exc:
        raise HTTPException(502, 'Could not read the plan price from Stripe.') from exc
    return int(price.get('unit_amount') or 0)


def _display_unit_price() -> int:
    """Stripe's price when Stripe is configured, else the proposed price (for showing, never charging)."""
    from .location_billing_rules import MONTHLY_LOCATION_PRICE_MINOR
    if os.getenv('STRIPE_SECRET_KEY', '').startswith('sk_test_') and os.getenv('STRIPE_GROWTH_PRICE_ID', '').startswith('price_'):
        try:
            return _growth_unit_price(_stripe_client())
        except HTTPException:
            pass
    return MONTHLY_LOCATION_PRICE_MINOR


def _subscription_item(stripe, w: Workspace) -> tuple[dict, dict]:
    try:
        sub = _stripe_payload(stripe.Subscription.retrieve(w.stripe_subscription_id))
    except Exception as exc:
        raise HTTPException(502, 'Could not read your subscription from Stripe.') from exc
    items = [i for i in ((sub.get('items') or {}).get('data') or []) if _object_id(i.get('price')) == os.getenv('STRIPE_GROWTH_PRICE_ID')]
    if len(items) != 1:
        raise HTTPException(409, 'Your subscription has an unexpected set of items. Contact support.')
    return sub, items[0]


@router.post('/billing/locations/preview')
def preview_location_change(payload: LocationChange, sub: str = Depends(owner_subject)):
    """What a new set of monitored locations costs, including Stripe's proration, before anything changes."""
    from .connections import validated_selection
    from .location_entitlements import snapshot
    with Session(engine) as db:
        w = _get_workspace(db, sub)
        merchant, _ = validated_selection(db, w.id, payload.location_ids)
        before = snapshot(db, w.id, merchant)['quantity']
        subscribed = entitlement(w)['state'] in ('active', 'canceling', 'past_due')
        stripe = _stripe_client() if subscribed else None
        unit = _growth_unit_price(stripe) if stripe else _display_unit_price()
        quantity = len(payload.location_ids)
        base = {'quantity_before': before, 'quantity_after': quantity, 'unit_amount_minor': unit,
                'monthly_total_minor': unit * quantity, 'currency': 'usd'}
        if not subscribed:
            return {**base, 'subscribed': False, 'prorated_change_minor': 0, 'next_invoice_total_minor': None,
                    'proration_date': None, 'message': 'Nothing is charged until you subscribe.'}
        subscription, item = _subscription_item(stripe, w)
        when = int(time.time())
        try:
            preview = _stripe_payload(stripe.Invoice.create_preview(
                customer=w.stripe_customer_id, subscription=w.stripe_subscription_id,
                subscription_details={'items': [{'id': item['id'], 'quantity': quantity}],
                                      'proration_behavior': 'create_prorations', 'proration_date': when}))
        except Exception as exc:
            raise HTTPException(502, 'Stripe could not preview the change. Try again.') from exc
        lines = (preview.get('lines') or {}).get('data') or []
        def is_proration(line):
            details = ((line.get('parent') or {}).get('subscription_item_details') or {})
            return bool(line.get('proration') or details.get('proration'))
        prorated = sum(int(l.get('amount') or 0) for l in lines if is_proration(l))
        return {**base, 'subscribed': True, 'quantity_before': int(item.get('quantity') or before),
                'prorated_change_minor': prorated, 'next_invoice_total_minor': int(preview.get('total') or 0),
                'proration_date': when,
                'message': ('Adding locations adds a prorated charge to your next invoice.' if prorated > 0 else
                            'Removing locations adds a prorated credit to your next invoice.' if prorated < 0 else
                            'No change to your bill.')}


@router.post('/billing/locations/confirm')
def confirm_location_change(payload: LocationChange, sub: str = Depends(owner_subject)):
    """Apply the previewed change: Stripe quantity and the monitored set change together."""
    from .connections import queue_import_if_added, validated_selection, write_selection
    from .location_entitlements import snapshot
    with Session(engine) as db:
        w = _get_workspace(db, sub)
        subscribed = entitlement(w)['state'] in ('active', 'canceling', 'past_due')
        merchant, authorized = validated_selection(db, w.id, payload.location_ids)
        if not subscribed:
            added = write_selection(db, w.id, merchant, payload.location_ids, authorized)
            db.commit()
            queue_import_if_added(db, w.id, added)
            return {'saved': True, 'subscribed': False, 'selected_count': len(payload.location_ids)}
        if not payload.proration_date or abs(time.time() - payload.proration_date) > 600:
            raise HTTPException(409, 'The price preview expired. Preview the change again.')
        stripe = _stripe_client()
        subscription, item = _subscription_item(stripe, w)
        added = write_selection(db, w.id, merchant, payload.location_ids, authorized)
        snap = snapshot(db, w.id, merchant)
        meta = {**(subscription.get('metadata') or {}), 'workspace_id': w.id,
                'sandbox_location_digest': snap['digest'], 'sandbox_location_quantity': str(snap['quantity'])}
        try:
            updated = stripe.Subscription.modify(w.stripe_subscription_id,
                items=[{'id': item['id'], 'quantity': snap['quantity']}], metadata=meta,
                proration_behavior='create_prorations', proration_date=payload.proration_date)
        except Exception as exc:
            db.rollback()  # the monitored set only changes if Stripe accepted the new quantity
            raise HTTPException(502, 'Stripe did not accept the change. Nothing was changed.') from exc
        db.commit()
        queue_import_if_added(db, w.id, added)
        result = _apply_verified_subscription(db, w, updated, w.stripe_customer_id)
        return {'saved': True, 'subscribed': True, 'selected_count': snap['quantity'], 'workspace': result['workspace']}


@router.post('/billing/webhook')
async def webhook(request: Request):
    secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    if not secret:
        raise HTTPException(status_code=503, detail='Stripe webhook secret is not configured.')
    stripe = _stripe_client()
    payload = await request.body()
    sig = request.headers.get('stripe-signature', '')
    try:
        event = _stripe_payload(stripe.Webhook.construct_event(payload, sig, secret))
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
        elif kind in ('invoice.payment_failed', 'invoice.paid', 'invoice.payment_succeeded'):
            customer_id = _object_id(obj.get('customer'))
            w = db.scalar(select(Workspace).where(Workspace.stripe_customer_id == customer_id)) if customer_id else None
            if w and w.stripe_subscription_id:
                if kind == 'invoice.payment_failed':
                    w.payment_failed_at = w.payment_failed_at or _now()
                db.commit()
                try:
                    current = stripe.Subscription.retrieve(w.stripe_subscription_id)
                except Exception as exc:
                    raise HTTPException(status_code=502, detail='Unable to verify Stripe subscription.') from exc
                _apply_verified_subscription(db, w, current, customer_id)
        db.add(BillingEvent(stripe_event_id=event_id, processed_at=_now()))
        db.commit()
    return {'received': True}
