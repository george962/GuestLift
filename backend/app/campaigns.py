"""Safe coupon/campaign CSV imports, intended ONLY for fictional local demonstration data."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import database
from .database import OrderRecord, CampaignRecord, RedemptionRecord, CampaignImportRun

CAMPAIGN_COLUMNS = ['campaign_id','code','name','offer_type','start_date','end_date','variable_cost_minor','fixed_cost_minor','description']
REDEMPTION_COLUMNS = ['redemption_id','campaign_id','provider','source_order_id','redeemed_at','discount_minor']
MAX_CSV_BYTES = 2 * 1024 * 1024


def _parse_csv(contents: bytes, filename: str, required: list[str]) -> list[dict]:
    if not contents or len(contents) > MAX_CSV_BYTES:
        raise ValueError(f'{filename}: empty or over the 2 MB demo limit')
    try:
        text = contents.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError(f'{filename}: expected UTF-8') from exc
    reader = csv.DictReader(io.StringIO(text, newline=''))
    headers = reader.fieldnames or []
    if len(set(headers)) != len(headers):
        raise ValueError(f'{filename}: duplicate CSV headers')
    missing = set(required) - set(headers)
    if missing:
        raise ValueError(f'{filename}: missing columns: {", ".join(sorted(missing))}')
    rows = list(reader)
    if len(rows) > 2000:
        raise ValueError(f'{filename}: 2000 rows maximum')
    if any(None in r for r in rows):
        raise ValueError(f'{filename}: extra fields found in a CSV row')
    return rows


def _nonempty(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f'{field} is required')
    val=value.strip()
    if len(val)>160:
        raise ValueError(f'{field} exceeds 160 characters')
    return val


def _cents(value: str, field: str) -> int:
    val=_nonempty(value,field)
    if not val.isdigit() or len(val)>11:
        raise ValueError(f'{field} must be nonnegative integer cents')
    return int(val)


def _campaign(raw: dict) -> dict:
    item={k:_nonempty(raw.get(k),k) for k in ['campaign_id','code','name','offer_type','start_date','end_date']}
    item['description']=(raw.get('description') or '').strip()
    if item['offer_type'] not in ('percent','fixed','free_item','other'):
        raise ValueError('offer_type must be percent, fixed, free_item or other')
    try:
        first=date.fromisoformat(item['start_date'])
        last=date.fromisoformat(item['end_date'])
    except ValueError as exc:
        raise ValueError('start_date and end_date must be YYYY-MM-DD') from exc
    if first>last:
        raise ValueError('campaign start_date occurs after end_date')
    item['variable_cost_minor']=_cents(raw.get('variable_cost_minor',''), 'variable_cost_minor')
    item['fixed_cost_minor']=_cents(raw.get('fixed_cost_minor',''), 'fixed_cost_minor')
    return item


def _redemption(raw: dict) -> dict:
    item={k:_nonempty(raw.get(k),k) for k in ['redemption_id','campaign_id','provider','source_order_id','redeemed_at']}
    if item['provider'] not in ('toast','square'):
        raise ValueError('provider must be toast or square')
    try:
        dt=datetime.fromisoformat(item['redeemed_at'].replace('Z','+00:00'))
        if dt.tzinfo is None:
            raise ValueError('timezone missing')
    except ValueError as exc:
        raise ValueError('redeemed_at must be ISO 8601 with timezone') from exc
    item['discount_minor']=_cents(raw.get('discount_minor',''), 'discount_minor')
    return item


def import_campaign_csvs(campaign_bytes: bytes, redemption_bytes: bytes) -> dict:
    """Reject invalid rows with line-number reason; allow valid rows through. Replay is idempotent.

    This sample deliberately permits only ONE campaign redemption per order. Real
    multi-discount accounting requires a separately designed financial allocation model.
    """
    campaign_rows=_parse_csv(campaign_bytes,'Campaigns.csv',CAMPAIGN_COLUMNS)
    redemption_rows=_parse_csv(redemption_bytes,'Redemptions.csv',REDEMPTION_COLUMNS)
    added_campaigns=added=duplicates=0
    issues=[]
    with Session(database.engine) as db:
        available={(o.provider,o.source_order_id):o for o in db.scalars(select(OrderRecord)).all()}
        known_campaigns={x.campaign_id:x for x in db.scalars(select(CampaignRecord)).all()}
        existing_redemptions={x.redemption_id:x for x in db.scalars(select(RedemptionRecord)).all()}
        occupied={(x.provider,x.source_order_id) for x in existing_redemptions.values()}
        for line,raw in enumerate(campaign_rows,2):
            try:
                item=_campaign(raw)
                cid=item['campaign_id']
                previous=known_campaigns.get(cid)
                if previous:
                    if any(getattr(previous,k)!=v for k,v in item.items()):
                        raise ValueError(f'campaign {cid} already exists with different settings; no silent overwrite')
                    duplicates+=1
                    continue
                row=CampaignRecord(**item)
                db.add(row)
                known_campaigns[cid]=row
                added_campaigns+=1
            except ValueError as exc:
                issues.append(f'Campaigns.csv row {line}: {exc}')
        seen_ids=set()
        for line,raw in enumerate(redemption_rows,2):
            try:
                item=_redemption(raw)
                rid=item['redemption_id']
                if rid in seen_ids:
                    raise ValueError(f'repeated redemption ID {rid} within this file')
                seen_ids.add(rid)
                c=known_campaigns.get(item['campaign_id'])
                if c is None:
                    raise ValueError(f'campaign {item["campaign_id"]} not found')
                order=available.get((item['provider'],item['source_order_id']))
                if order is None:
                    raise ValueError(f'order {item["provider"]}:{item["source_order_id"]} not imported; import POS orders first')
                payload = __import__('json').loads(order.payload_json)
                if payload.get('status') in ('VOIDED','CANCELED'):
                    raise ValueError('a voided/canceled order cannot redeem')
                if not c.start_date <= item['redeemed_at'][:10] <= c.end_date:
                    raise ValueError('redemption outside campaign date range')
                if item['discount_minor'] > order.discount_minor:
                    raise ValueError(f'recorded discount {item["discount_minor"]} exceeds POS order discount {order.discount_minor}')
                prev=existing_redemptions.get(rid)
                if prev:
                    if any(getattr(prev,k)!=v for k,v in item.items()):
                        raise ValueError(f'redemption {rid} exists with different data; corrections unsupported in this prototype')
                    duplicates+=1
                    continue
                if (item['provider'],item['source_order_id']) in occupied:
                    raise ValueError('order already has a campaign redemption; one per order in this demo')
                row=RedemptionRecord(**item)
                db.add(row)
                existing_redemptions[rid]=row
                occupied.add((item['provider'],item['source_order_id']))
                added+=1
            except ValueError as exc:
                issues.append(f'Redemptions.csv row {line}: {exc}')
        run=CampaignImportRun(processed_at=datetime.now(timezone.utc).isoformat(),campaigns_inserted=added_campaigns,
            redemptions_inserted=added,duplicates=duplicates,rejected=len(issues),issues_json=__import__('json').dumps(issues))
        db.add(run)
        db.commit()
        db.refresh(run)
        return {'import_id':run.id,'campaigns_inserted':added_campaigns,'redemptions_inserted':added,
                'duplicates':duplicates,'rejected':len(issues),'issues':issues,'mode':'synthetic_local_demo'}
