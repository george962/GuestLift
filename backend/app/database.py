"""Local-only demo persistence. No credentials, real merchants or customer PII."""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, Text, UniqueConstraint, select, delete, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./guestlift_demo.db')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)

class Base(DeclarativeBase):
    pass

class OrderRecord(Base):
    __tablename__ = 'canonical_orders'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(20))
    source_order_id: Mapped[str] = mapped_column(String(120))
    location_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[str] = mapped_column(String(80))
    customer_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    net_sales_minor: Mapped[int] = mapped_column(Integer)
    discount_minor: Mapped[int] = mapped_column(Integer)
    refund_minor: Mapped[int] = mapped_column(Integer)
    payload_json: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('provider', 'source_order_id', name='uq_provider_order'),)

class ImportRun(Base):
    __tablename__ = 'import_runs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(20))
    processed_at: Mapped[str] = mapped_column(String(40))
    inserted: Mapped[int] = mapped_column(Integer)
    duplicates: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))

class CampaignRecord(Base):
    __tablename__ = 'campaigns'
    campaign_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(160))
    offer_type: Mapped[str] = mapped_column(String(30))
    start_date: Mapped[str] = mapped_column(String(10))
    end_date: Mapped[str] = mapped_column(String(10))
    variable_cost_minor: Mapped[int] = mapped_column(Integer)  # additional fulfillment or reward cost per redemption
    fixed_cost_minor: Mapped[int] = mapped_column(Integer)  # scenario marketing expense
    description: Mapped[str] = mapped_column(Text, default='')

class RedemptionRecord(Base):
    __tablename__ = 'campaign_redemptions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    redemption_id: Mapped[str] = mapped_column(String(120), unique=True)
    campaign_id: Mapped[str] = mapped_column(String(80), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    source_order_id: Mapped[str] = mapped_column(String(120))
    redeemed_at: Mapped[str] = mapped_column(String(40))
    discount_minor: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint('provider', 'source_order_id', name='uq_one_campaign_per_demo_order'),)

class CampaignImportRun(Base):
    __tablename__ = 'campaign_import_runs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    processed_at: Mapped[str] = mapped_column(String(40))
    campaigns_inserted: Mapped[int] = mapped_column(Integer)
    redemptions_inserted: Mapped[int] = mapped_column(Integer)
    duplicates: Mapped[int] = mapped_column(Integer)
    rejected: Mapped[int] = mapped_column(Integer)
    issues_json: Mapped[str] = mapped_column(Text)


def init_db() -> None:
    """Additive migration for people upgrading an existing v0.3 SQLite/Postgres database."""
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    if 'canonical_orders' in inspector.get_table_names():
        columns = {x['name'] for x in inspector.get_columns('canonical_orders')}
        if 'customer_id' not in columns:
            with engine.begin() as connection:
                connection.exec_driver_sql('ALTER TABLE canonical_orders ADD COLUMN customer_id VARCHAR(120)')


def reset_db() -> None:
    with Session(engine) as db:
        # Delete children first. This endpoint is meant only for the local demo.
        for model in (CampaignImportRun, RedemptionRecord, CampaignRecord, ImportRun, OrderRecord):
            db.execute(delete(model))
        db.commit()


def persist(orders: list) -> tuple[int, int, int, str]:
    inserted = duplicates = 0
    with Session(engine) as db:
        for order in orders:
            exists = db.scalar(select(OrderRecord).where(OrderRecord.provider == order.provider, OrderRecord.source_order_id == order.source_order_id))
            if exists:
                duplicates += 1
                continue
            db.add(OrderRecord(provider=order.provider, source_order_id=order.source_order_id,
                location_id=order.location_id, created_at=order.created_at, customer_id=order.customer_id,
                net_sales_minor=order.net_sales_minor, discount_minor=order.discount_minor,
                refund_minor=order.refund_minor, payload_json=order.model_dump_json()))
            inserted += 1
        run = ImportRun(provider=orders[0].provider if orders else 'unknown', processed_at=datetime.now(timezone.utc).isoformat(),
            inserted=inserted, duplicates=duplicates, status='completed' if inserted else 'replayed')
        db.add(run)
        db.commit()
        db.refresh(run)
        return inserted, duplicates, run.id, run.status


def metrics(provider: str | None = None) -> dict:
    with Session(engine) as db:
        query = select(OrderRecord)
        if provider:
            query = query.where(OrderRecord.provider == provider)
        rows = db.scalars(query.order_by(OrderRecord.id)).all()
        count = len(rows)
        by_location = {}
        for row in rows:
            key = (row.provider, row.location_id)
            cur = by_location.setdefault(key, {'location_id':row.location_id, 'provider':row.provider, 'orders':0, 'net_sales_minor':0,'discounts_minor':0,'refunds_minor':0})
            cur['orders'] += 1
            cur['net_sales_minor'] += row.net_sales_minor
            cur['discounts_minor'] += row.discount_minor
            cur['refunds_minor'] += row.refund_minor
        total = sum(o.net_sales_minor for o in rows)
        return {'order_count':count,'net_sales_minor':total,
            'discounts_minor':sum(o.discount_minor for o in rows),'refunds_minor':sum(o.refund_minor for o in rows),
            'average_order_minor':round(total / count) if count else 0,
            'locations':sorted(by_location.values(),key=lambda x:(x['provider'],x['location_id'])),
            'orders':[json.loads(o.payload_json) for o in rows]}


def recent_runs() -> list[dict]:
    with Session(engine) as db:
        return [{'id':r.id,'provider':r.provider,'processed_at':r.processed_at,'inserted':r.inserted,'duplicates':r.duplicates,'status':r.status} for r in db.scalars(select(ImportRun).order_by(ImportRun.id.desc()).limit(12))]


def customer_summary(orders: list[dict] | None = None) -> dict:
    """Provider-scoped synthetic IDs only; no identity stitching across systems."""
    if orders is None:
        with Session(engine) as db:
            orders = [json.loads(o.payload_json) for o in db.scalars(select(OrderRecord)).all()]
    known = defaultdict(list)
    for o in orders:
        if o.get('customer_id') and o.get('status') not in ('VOIDED', 'CANCELED'):
            known[(o['provider'], o['customer_id'])].append(o)
    known_order_count = sum(map(len, known.values()))
    repeats = sum(1 for xs in known.values() if len(xs) >= 2)
    customers = len(known)
    return {
        'total_orders':len(orders), 'identified_orders':known_order_count,
        'customer_coverage_percent':round(100 * known_order_count / len(orders), 1) if orders else 0,
        'identified_customers':customers, 'repeat_customers':repeats,
        'repeat_customer_rate_percent':round(100 * repeats / customers, 1) if customers else 0,
        'anonymous_orders':len(orders) - known_order_count,
        'methodology':'Synthetic, provider-scoped customer IDs; at least two observed non-voided orders define repeat. No cross-provider matching.',
    }


def campaign_reports(margin_percent: int = 35) -> dict:
    if not 0 <= margin_percent <= 95:
        raise ValueError('Margin assumption must be from 0 to 95')
    with Session(engine) as db:
        campaigns = db.scalars(select(CampaignRecord).order_by(CampaignRecord.campaign_id)).all()
        redemptions = db.scalars(select(RedemptionRecord).order_by(RedemptionRecord.id)).all()
        orders = db.scalars(select(OrderRecord)).all()
        order_map = {(o.provider,o.source_order_id):o for o in orders}
        full_orders = [json.loads(o.payload_json) for o in orders]
        customer_counts = defaultdict(int)
        for o in full_orders:
            if o.get('customer_id') and o.get('status') not in ('VOIDED', 'CANCELED'):
                customer_counts[(o['provider'], o['customer_id'])] += 1
        grouped = defaultdict(list)
        for r in redemptions:
            order = order_map.get((r.provider, r.source_order_id))
            if order:
                grouped[r.campaign_id].append((r,order))
        results = []
        for c in campaigns:
            matches = grouped[c.campaign_id]
            sales = sum(order.net_sales_minor for _,order in matches)
            discount = sum(r.discount_minor for r,_ in matches)
            refunded = sum(order.refund_minor for _,order in matches)
            variable = c.variable_cost_minor * len(matches)
            # The order's net sales already subtract POS discounts. Do not subtract those again.
            modeled = round(sales * margin_percent / 100) - variable - c.fixed_cost_minor
            location_map = {}
            for r,order in matches:
                k=(order.provider,order.location_id)
                line=location_map.setdefault(k,{'provider':order.provider,'location_id':order.location_id,'redeemed_orders':0,'net_sales_minor':0,'recorded_discount_minor':0})
                line['redeemed_orders']+=1
                line['net_sales_minor']+=order.net_sales_minor
                line['recorded_discount_minor']+=r.discount_minor
            customers = {(order.provider,order.customer_id) for _,order in matches if order.customer_id}
            repeat = sum(1 for x in customers if customer_counts[x] >= 2)
            result = {
                'campaign_id':c.campaign_id,'name':c.name,'code':c.code,'offer_type':c.offer_type,
                'description':c.description, 'start_date':c.start_date,'end_date':c.end_date,
                'redeemed_orders':len(matches),'attributed_net_sales_minor':sales,
                'recorded_discount_minor':discount,'recorded_refund_minor':refunded,
                'variable_campaign_cost_minor':variable,'fixed_campaign_cost_minor':c.fixed_cost_minor,
                'modeled_contribution_minor':modeled,
                'identified_redeemers':len(customers),'repeat_redeemers':repeat,
                'anonymous_redemptions':sum(1 for _,o in matches if not o.customer_id),
                'locations':sorted(location_map.values(),key=lambda x:(x['provider'],x['location_id'])),
                'order_matches':[
                    {'redemption_id':r.redemption_id,'provider':order.provider,'source_order_id':order.source_order_id,
                     'location_id':order.location_id,'customer_id':order.customer_id,
                     'net_sales_minor':order.net_sales_minor,'recorded_discount_minor':r.discount_minor,
                     'refund_minor':order.refund_minor, 'redeemed_at':r.redeemed_at} for r,order in matches
                ]
            }
            results.append(result)
        return {
            'campaigns':results,'margin_assumption_percent':margin_percent,
            'customer_summary':customer_summary(full_orders),
            'total_redemptions':len(redemptions),
            'disclaimer':'Synthetic and descriptive. Attributed sales are not incremental sales; modeled contribution uses an assumed margin and is not causal ROI. POS discounts already reduce net sales.',
        }
