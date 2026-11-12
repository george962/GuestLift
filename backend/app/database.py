"""Local SQL persistence; SQLite by default, PostgreSQL when DATABASE_URL set."""
from __future__ import annotations
import os
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, Text, UniqueConstraint, select, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

DATABASE_URL=os.getenv('DATABASE_URL', 'sqlite:///./guestlift_demo.db')
engine=create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)

class Base(DeclarativeBase): pass

class OrderRecord(Base):
    __tablename__='canonical_orders'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    provider: Mapped[str]=mapped_column(String(20))
    source_order_id: Mapped[str]=mapped_column(String(120))
    location_id: Mapped[str]=mapped_column(String(120))
    created_at: Mapped[str]=mapped_column(String(80))
    net_sales_minor: Mapped[int]=mapped_column(Integer)
    discount_minor: Mapped[int]=mapped_column(Integer)
    refund_minor: Mapped[int]=mapped_column(Integer)
    payload_json: Mapped[str]=mapped_column(Text)
    __table_args__=(UniqueConstraint('provider','source_order_id', name='uq_provider_order'),)

class ImportRun(Base):
    __tablename__='import_runs'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    provider: Mapped[str]=mapped_column(String(20))
    processed_at: Mapped[str]=mapped_column(String(40))
    inserted: Mapped[int]=mapped_column(Integer)
    duplicates: Mapped[int]=mapped_column(Integer)
    status: Mapped[str]=mapped_column(String(30))


def init_db() -> None:
    Base.metadata.create_all(engine)


def reset_db() -> None:
    with Session(engine) as db:
        db.execute(delete(ImportRun))
        db.execute(delete(OrderRecord))
        db.commit()


def persist(orders: list) -> tuple[int,int,int,str]:
    inserted=0; duplicates=0
    with Session(engine) as db:
        for order in orders:
            exists=db.scalar(select(OrderRecord).where(OrderRecord.provider == order.provider, OrderRecord.source_order_id==order.source_order_id))
            if exists:
                # Repeat imports do not replace paid sales or duplicate records.
                duplicates+=1
                continue
            db.add(OrderRecord(provider=order.provider, source_order_id=order.source_order_id, location_id=order.location_id,
                created_at=order.created_at, net_sales_minor=order.net_sales_minor, discount_minor=order.discount_minor,
                refund_minor=order.refund_minor,payload_json=order.model_dump_json()))
            inserted+=1
        run=ImportRun(provider=orders[0].provider if orders else 'unknown',processed_at=datetime.now(timezone.utc).isoformat(),
                      inserted=inserted,duplicates=duplicates,status='completed' if inserted else 'replayed')
        db.add(run)
        db.commit();db.refresh(run)
        return inserted,duplicates,run.id,run.status


def metrics(provider: str | None=None) -> dict:
    with Session(engine) as db:
        query=select(OrderRecord)
        if provider:query=query.where(OrderRecord.provider==provider)
        rows=db.scalars(query.order_by(OrderRecord.id)).all()
        count=len(rows)
        by_location={}
        for row in rows:
            cur=by_location.setdefault(row.location_id,{'location_id':row.location_id,'provider':row.provider,'orders':0,'net_sales_minor':0,'discounts_minor':0,'refunds_minor':0})
            cur['orders']+=1;cur['net_sales_minor']+=row.net_sales_minor;cur['discounts_minor']+=row.discount_minor;cur['refunds_minor']+=row.refund_minor
        return {'order_count':count,'net_sales_minor':sum(o.net_sales_minor for o in rows),
                'discounts_minor':sum(o.discount_minor for o in rows),'refunds_minor':sum(o.refund_minor for o in rows),
                'average_order_minor':(round(sum(o.net_sales_minor for o in rows)/count) if count else 0),
                'locations':sorted(by_location.values(),key=lambda x: x['location_id']),
                'orders':[json.loads(o.payload_json) for o in rows]}


def recent_runs() -> list[dict]:
    with Session(engine) as db:
        return [{'id':r.id,'provider':r.provider,'processed_at':r.processed_at,'inserted':r.inserted,'duplicates':r.duplicates,'status':r.status} for r in db.scalars(select(ImportRun).order_by(ImportRun.id.desc()).limit(12))]
