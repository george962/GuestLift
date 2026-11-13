"""Account-scoped restaurant decision planning with explicit assumptions.

Synthetic Square Sandbox only. Plans do NOT send messages, create Square discounts,
or claim promotional causality. Every decision belongs to the authenticated workspace.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import uuid
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from .database import Base, engine
from .local_auth import authenticated_subject
from .saas import Workspace, _get_workspace, _scoped_summary
from .connections import SquareOrder

router = APIRouter(prefix='/api/decisions', tags=['Private restaurant decisions'])

class DecisionPlan(Base):
    __tablename__ = 'tablesignal_decision_plans'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    objective: Mapped[str] = mapped_column(String(40), nullable=False)
    offer_type: Mapped[str] = mapped_column(String(30), nullable=False)
    offer_value: Mapped[int] = mapped_column(Integer, nullable=False)
    target_redemptions: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_basket_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    assumed_margin_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_budget_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    modeled_contribution_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='draft')
    notes: Mapped[str] = mapped_column(Text, nullable=False, default='')
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)

class PlanCreate(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    objective: str = Field(pattern='^(returning_guests|discount_review)$')
    offer_type: str = Field(pattern='^(percent|fixed|no_offer)$')
    offer_value: int = Field(ge=0, le=10000)
    target_redemptions: int = Field(ge=1, le=10000)
    reference_basket_minor: int = Field(ge=100, le=1000000)
    assumed_margin_percent: int = Field(ge=1, le=95)
    notes: str = Field(default='', max_length=1200)

class StatusUpdate(BaseModel):
    status: str = Field(pattern='^(draft|planned|reviewed)$')


def _now(): return datetime.now(timezone.utc).isoformat()


def scenario(offer_type: str, offer_value: int, redemptions: int, basket_minor: int, margin: int) -> dict:
    if offer_type == 'percent':
        if not 1 <= offer_value <= 80:
            raise HTTPException(status_code=422, detail='Percent offer must be between 1 and 80%.')
        discount_each = basket_minor * offer_value // 100
    elif offer_type == 'fixed':
        if not 1 <= offer_value <= basket_minor:
            raise HTTPException(status_code=422, detail='Fixed discount must be greater than zero and no larger than basket value.')
        discount_each = offer_value
    elif offer_type == 'no_offer':
        if offer_value != 0: raise HTTPException(status_code=422, detail='No-offer scenario must have value 0.')
        discount_each = 0
    else: raise HTTPException(status_code=422, detail='Unknown offer type.')
    gross = basket_minor * redemptions
    spend = discount_each * redemptions
    return {
        'scenario_orders': redemptions,
        'hypothetical_sales_minor': gross,
        'discount_per_order_minor': discount_each,
        'discount_budget_minor': spend,
        'modeled_contribution_minor': (gross * margin // 100) - spend,
        'assumed_margin_percent': margin,
        'disclaimer': 'Assumes these purchases occur; NOT incremental sales, profit, campaign lift, or a forecast. Does not include fixed campaign costs or tax. No offer is sent.'
    }


def _serialize(p: DecisionPlan) -> dict:
    return {key: getattr(p, key) for key in ('id','title','objective','offer_type','offer_value',
       'target_redemptions','reference_basket_minor','assumed_margin_percent','discount_budget_minor',
       'modeled_contribution_minor','status','notes','created_at','updated_at')}


def opportunity_summary(db: Session, workspace: Workspace) -> dict:
    s = _scoped_summary(db, workspace)
    orders = db.scalars(select(SquareOrder).where(SquareOrder.workspace_id == workspace.id)).all()
    observed = [o for o in orders if o.status not in ('VOIDED','CANCELED')]
    identified = defaultdict(list)
    dates = []
    for o in observed:
        try:
            timestamp = datetime.fromisoformat(o.created_at.replace('Z','+00:00'))
            if timestamp.tzinfo is None: timestamp = timestamp.replace(tzinfo=timezone.utc)
            dates.append(timestamp)
            if o.customer_id: identified[o.customer_id].append(timestamp)
        except (ValueError, AttributeError): continue
    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=30)
    candidates = [key for key, visits in identified.items()
                  if len(visits) >= 2 and max(visits) < lookback]
    span = (max(dates)-min(dates)).days if dates else 0
    adequate = len(observed) >= 20 and len(identified) >= 5 and span >= 30
    cards = [
        {'id':'returning_guests','title':'Which known guests may be overdue for another visit?',
         'status':'ready' if adequate else 'needs_more_history',
         'value':len(candidates) if adequate else None,
         'description':('Previously observed repeat purchasers without an observed order in 30 days. '
                       'This is not proof they stopped visiting; unidentified purchases are excluded.'),
         'evidence':f'{len(identified)} identified customers, {len(observed)} observed orders, {span} days of available order dates.',
         'action':'Compare an offer-cost scenario' if adequate else 'Collect more history before targeting guests'},
        {'id':'discount_review','title':'What could a discount cost our restaurant?',
         'status':'ready' if observed else 'needs_orders',
         'value':s['discount_minor'] if observed else None,
         'description':'Observed discounts on imported orders. Compare an assumed 10% versus fixed-dollar offer, without claiming any incremental lift.',
         'evidence':f'{len(observed)} orders; observed discounts ${s["discount_minor"]/100:,.2f}.',
         'action':'Compare discount scenarios' if observed else 'Connect and sync orders'},
        {'id':'identity_coverage','title':'Can we actually recognize returning guests?',
         'status':'needs_attention' if s['identification_coverage_percent'] < 70 else 'observed',
         'value':s['identification_coverage_percent'] if observed else None,
         'description':'Percent of orders with a usable customer ID. Anonymous orders cannot be assigned to a guest; never infer identity.',
         'evidence':f'{s["identified_orders"]} identifiable orders out of {s["orders"]}.',
         'action':'Review Square customer-ID coverage'}
    ]
    return {'workspace': workspace.name, 'data_origin':s['data_origin'], 'has_connected_source':s['has_connected_source'],
            'observed_orders':len(observed), 'identified_customers':len(identified),
            'reference_basket_minor':max(100,s['average_order_minor']),
            'observed_repeat_candidates':len(candidates) if adequate else None,
            'opportunities':cards,'limitations':['Square Sandbox test data only.','No campaign redemptions or verified causal lift.',
            'Identity and historical coverage may be incomplete.']}

@router.get('/opportunities')
def opportunities(sub: str = Depends(authenticated_subject)):
    with Session(engine) as db:
        return opportunity_summary(db, _get_workspace(db,sub))

@router.get('/plans')
def plans(sub: str = Depends(authenticated_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        records=db.scalars(select(DecisionPlan).where(DecisionPlan.workspace_id==w.id)
                           .order_by(DecisionPlan.created_at.desc())).all()
        return {'plans':[_serialize(p) for p in records]}

@router.post('/plans',status_code=201)
def create_plan(payload:PlanCreate,sub:str=Depends(authenticated_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        summary=_scoped_summary(db,w)
        if not summary['has_connected_source'] or not summary['orders']:
            raise HTTPException(status_code=409,detail='Connect Square Sandbox and sync completed orders before saving a plan.')
        calc=scenario(payload.offer_type,payload.offer_value,payload.target_redemptions,
                      payload.reference_basket_minor,payload.assumed_margin_percent)
        at=_now()
        item=DecisionPlan(id=str(uuid.uuid4()),workspace_id=w.id,title=payload.title.strip(),
            objective=payload.objective,offer_type=payload.offer_type,offer_value=payload.offer_value,
            target_redemptions=payload.target_redemptions,reference_basket_minor=payload.reference_basket_minor,
            assumed_margin_percent=payload.assumed_margin_percent,
            discount_budget_minor=calc['discount_budget_minor'],
            modeled_contribution_minor=calc['modeled_contribution_minor'],
            status='draft',notes=payload.notes.strip(),created_at=at,updated_at=at)
        db.add(item);db.commit()
        return {'plan':_serialize(item),'scenario':calc,'message':'Draft saved to this restaurant. No campaign was launched.'}

@router.post('/plans/{plan_id}/status')
def update_plan(plan_id:str,payload:StatusUpdate,sub:str=Depends(authenticated_subject)):
    with Session(engine) as db:
        w=_get_workspace(db,sub)
        p=db.get(DecisionPlan,plan_id)
        if not p or p.workspace_id!=w.id:
            raise HTTPException(status_code=404,detail='Decision not found in this workspace.')
        p.status=payload.status;p.updated_at=_now();db.commit();db.refresh(p)
        return {'plan':_serialize(p),'message':'Tracking status updated; no marketing campaign was sent.'}
