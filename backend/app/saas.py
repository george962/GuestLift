"""Account, workspace, billing TEST mode and evidence-backed analyst.

Not a production merchant service. All workspace orders are synthetic and seeded from packaged fixtures.
Authentication requires Supabase credentials; no local bypass or magic demo token exists.
"""
from __future__ import annotations
import csv
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import String, Integer, Text, ForeignKey, UniqueConstraint, select, delete
from sqlalchemy.orm import Mapped, mapped_column, Session

from .database import Base, engine
from .adapters import parse
from .insights import analyze_orders, answer_question

router=APIRouter(prefix='/api/saas',tags=['SaaS foundation (test mode)'])
security=HTTPBearer(auto_error=False)

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


def _now()->str:return datetime.now(timezone.utc).isoformat()

async def authenticated_subject(credentials:Annotated[HTTPAuthorizationCredentials|None,Depends(security)]) -> str:
    """Validate bearer token remotely against Supabase Auth; never trust decoded JWT without verification."""
    url=os.getenv('SUPABASE_URL','').rstrip('/')
    key=os.getenv('SUPABASE_PUBLISHABLE_KEY','')
    if not url or not key:
        raise HTTPException(status_code=503,detail='Account services not configured. Public sandbox still works.')
    if credentials is None or credentials.scheme.lower()!='bearer':
        raise HTTPException(status_code=401,detail='Sign in required')
    try:
        async with httpx.AsyncClient(timeout=8.0,follow_redirects=False) as client:
            res=await client.get(url+'/auth/v1/user',headers={'apikey':key,'Authorization':'Bearer '+credentials.credentials})
    except httpx.RequestError:
        raise HTTPException(status_code=503,detail='Authentication provider unavailable')
    if res.status_code!=200:
        raise HTTPException(status_code=401,detail='Invalid or expired access token')
    sub=res.json().get('id')
    if not isinstance(sub,str) or not sub:
        raise HTTPException(status_code=401,detail='No verified account subject')
    return sub


def _get_workspace(db:Session,owner_sub:str) -> Workspace:
    w=db.scalar(select(Workspace).where(Workspace.owner_sub==owner_sub))
    if w is None:
        w=Workspace(id=str(uuid.uuid4()),owner_sub=owner_sub,created_at=_now())
        db.add(w);db.commit();db.refresh(w)
        _seed_workspace(db,w.id)
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
      'source_mode':'fictional_workspace_seed','payments_live':False}


def _scoped_summary(db:Session,w:Workspace)->dict:
    rows=db.scalars(select(WorkspaceOrder).where(WorkspaceOrder.workspace_id==w.id)).all()
    return analyze_orders([{'provider':o.provider,'location_id':o.location_id,'source_order_id':o.source_order_id,
       'created_at':o.created_at,'status':o.status,'customer_id':o.customer_id,'net_sales_minor':o.net_sales_minor,
       'discount_minor':o.discount_minor,'campaign_code':o.campaign_code,
       'campaign_discount_minor':o.campaign_discount_minor} for o in rows])

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
def reset_demo(sub:str=Depends(authenticated_subject)):
    """Reset only own synthetic rows. Never touch other workspaces or legacy demo tables."""
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        db.execute(delete(WorkspaceOrder).where(WorkspaceOrder.workspace_id==w.id));db.commit()
        inserted=_seed_workspace(db,w.id)
        return {'seeded':inserted,'source_mode':'fictional_workspace_seed'}

@router.post('/analyst')
def analyst(data:AnalystRequest,sub:str=Depends(authenticated_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        if not (w.subscription_plan=='growth' and w.subscription_status in ('active','trialing')):
            raise HTTPException(status_code=402,detail='Growth subscription required for account-based analyst. Free synthetic demo available without sign-in.')
        summary=_scoped_summary(db,w)
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
                instructions=('You are a read-only restaurant analyst. The user is looking at FICTIONAL SYNTHETIC data. '
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

@router.post('/billing/checkout')
def checkout(sub:str=Depends(authenticated_subject)):
    secret=os.getenv('STRIPE_SECRET_KEY','')
    price=os.getenv('STRIPE_GROWTH_PRICE_ID','')
    base=os.getenv('GUESTLIFT_APP_URL','http://localhost:3000').rstrip('/')
    if not secret.startswith('sk_test_') or not price.startswith('price_'):
        raise HTTPException(status_code=503,detail='Stripe TEST-mode billing not configured')
    import stripe
    stripe.api_key=secret
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        if w.subscription_plan=='growth' and w.subscription_status in ('active','trialing'):
            raise HTTPException(status_code=409,detail='Already subscribed; use billing portal')
        kwargs={'mode':'subscription','line_items':[{'price':price,'quantity':1}],
                'success_url':base+'/billing?checkout=return',
                'cancel_url':base+'/pricing?billing=cancel',
                'client_reference_id':w.id,
                'subscription_data':{'metadata':{'workspace_id':w.id}}}
        if w.stripe_customer_id:kwargs['customer']=w.stripe_customer_id
        session=stripe.checkout.Session.create(**kwargs)
    return {'url':session.url,'mode':'stripe_test','price_id':price}

@router.post('/billing/portal')
def portal(sub:str=Depends(authenticated_subject)):
    secret=os.getenv('STRIPE_SECRET_KEY','')
    if not secret.startswith('sk_test_'):
        raise HTTPException(status_code=503,detail='Stripe TEST-mode billing not configured')
    import stripe
    stripe.api_key=secret
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        if not w.stripe_customer_id:
            raise HTTPException(status_code=404,detail='No Stripe customer on this workspace')
        s=stripe.billing_portal.Session.create(customer=w.stripe_customer_id,
            return_url=os.getenv('GUESTLIFT_APP_URL','http://localhost:3000').rstrip('/')+'/billing')
    return {'url':s.url}

@router.post('/billing/webhook')
async def webhook(request:Request):
    secret=os.getenv('STRIPE_WEBHOOK_SECRET','')
    key=os.getenv('STRIPE_SECRET_KEY','')
    if not secret or not key.startswith('sk_test_'):
        raise HTTPException(status_code=503,detail='Stripe test webhook not configured')
    import stripe
    stripe.api_key=key
    payload=await request.body()
    sig=request.headers.get('stripe-signature','')
    try:event=stripe.Webhook.construct_event(payload,sig,secret)
    except (ValueError,stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400,detail='Invalid Stripe webhook signature')
    event_id=event['id'];kind=event['type'];obj=event['data']['object']
    with Session(engine) as db:
        if db.get(BillingEvent,event_id):return {'received':True,'duplicate':True}
        if kind=='checkout.session.completed' and obj.get('mode')=='subscription':
            w=db.get(Workspace,obj.get('client_reference_id'))
            if w:
                w.stripe_customer_id=str(obj.get('customer')) if obj.get('customer') else w.stripe_customer_id
                w.stripe_subscription_id=str(obj.get('subscription')) if obj.get('subscription') else w.stripe_subscription_id
                # Checkout redirect alone does not grant entitlement. Await subscription status event.
        elif kind in ('customer.subscription.created','customer.subscription.updated','customer.subscription.deleted'):
            meta=obj.get('metadata',{}) or {}
            workspace_id=meta.get('workspace_id')
            customer=obj.get('customer')
            w=(db.get(Workspace,workspace_id) if workspace_id else None)
            if not w and customer:
                w=db.scalar(select(Workspace).where(Workspace.stripe_customer_id==str(customer)))
            if w:
                current_sub=w.stripe_subscription_id
                event_sub=str(obj.get('id',''))
                if current_sub and event_sub!=current_sub:
                    # Ignore events for a different subscription; review account before merging subscriptions.
                    pass
                else:
                    w.stripe_subscription_id=event_sub
                    w.stripe_customer_id=str(customer) if customer else w.stripe_customer_id
                    status=obj.get('status','unknown')
                    w.subscription_status=status
                    w.subscription_plan='growth' if status in ('active','trialing') else 'sandbox'
        db.add(BillingEvent(stripe_event_id=event_id,processed_at=_now()))
        db.commit()
    return {'received':True}
