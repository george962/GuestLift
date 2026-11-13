"""Source adapters for documented vendor-shaped *synthetic* fixture inputs.

Money: gross is pretax menu-item gross; discounts and refunds reduce net sales.
Neither Square order total_money nor Toast order Total is used as a pretax sale.
All Decimal amounts are converted to integer cents, without floats.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from .models import CanonicalOrder, Item, Payment

FIXTURE_DIR = Path(__file__).resolve().parent.parent / 'fixtures'


def cents(value: str | int | Decimal) -> int:
    try:
        return int((Decimal(str(value)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f'invalid decimal monetary amount: {value!r}') from exc


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        actual = set(reader.fieldnames or [])
        missing = required - actual
        if missing:
            raise ValueError(f'{path.name} missing headers: {", ".join(sorted(missing))}')
        return list(reader)


def _unique(rows: list[dict], key: str, kind: str) -> None:
    ids = [r[key] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f'duplicate {kind} IDs in source file')


def parse_toast(folder: Path | None = None) -> list[CanonicalOrder]:
    folder = folder or FIXTURE_DIR / 'toast'
    orders = read_csv(folder / 'OrderDetails.csv', {'Order Id', 'Location', 'Opened', 'Discount Amount', 'Tax', 'Tip', 'Total', 'Voided'})
    items = read_csv(folder / 'ItemSelectionDetails.csv', {'Order Id', 'Item Selection Id', 'Menu Item', 'Qty', 'Gross Price', 'Discnt', 'Void?'})
    payments = read_csv(folder / 'PaymentDetails.csv', {'Order Id', 'Payment Id', 'Amount', 'Tip', 'Status', 'Refund Amount'})
    _unique(orders, 'Order Id', 'order')
    _unique(items, 'Item Selection Id', 'item selection')
    _unique(payments, 'Payment Id', 'payment')
    items_by_order: dict[str, list[dict]] = defaultdict(list)
    pays_by_order: dict[str, list[dict]] = defaultdict(list)
    for line in items:
        items_by_order[line['Order Id']].append(line)
    for p in payments:
        pays_by_order[p['Order Id']].append(p)
    known = {o['Order Id'] for o in orders}
    orphan = (set(items_by_order) | set(pays_by_order)) - known
    if orphan:
        raise ValueError(f'orphan item/payment order refs: {sorted(orphan)}')
    output: list[CanonicalOrder] = []
    for o in orders:
        oid = o['Order Id']
        active = [i for i in items_by_order[oid] if i['Void?'].strip().lower() != 'true']
        if not active:
            raise ValueError(f'order {oid} contains no non-voided items')
        mapped_items = [Item(item_id=i['Item Selection Id'], name=i['Menu Item'], quantity=float(i['Qty']), gross_minor=cents(i['Gross Price']), discount_minor=cents(i['Discnt'])) for i in active]
        gross = sum(i.gross_minor for i in mapped_items)
        discount = cents(o['Discount Amount'])
        item_discount = sum(i.discount_minor for i in mapped_items)
        warnings=[]
        if item_discount != discount:
            warnings.append(f'Order discount {discount} cents differs from item discount total {item_discount} cents; using order discount.')
        refund = sum(cents(p['Refund Amount'] or '0') for p in pays_by_order[oid])
        net = gross - discount - refund
        if net < 0:
            raise ValueError(f'order {oid} has refunds + discounts exceeding gross')
        if not pays_by_order[oid]:
            warnings.append('No payment rows; payment coverage unknown.')
        output.append(CanonicalOrder(
            provider='toast', source_order_id=oid, location_id=o['Location'], created_at=o['Opened'],
            status='VOIDED' if o['Voided'].strip().lower() == 'true' else 'CLOSED',
            customer_id=(o.get('GuestLift Test Customer Id') or None),
            gross_minor=gross, discount_minor=discount, refund_minor=refund, net_sales_minor=net,
            tax_minor=cents(o['Tax'] or '0'), tip_minor=cents(o['Tip'] or '0'),
            items=mapped_items, payments=[Payment(payment_id=p['Payment Id'], amount_minor=cents(p['Amount']), status=p['Status']) for p in pays_by_order[oid]],
            lineage={'order_file':'OrderDetails.csv', 'item_file':'ItemSelectionDetails.csv', 'payment_file':'PaymentDetails.csv'}, warnings=warnings
        ))
    return output


def money(obj: dict[str, Any] | None, label: str, required: bool = True) -> int | None:
    if obj is None:
        if required:
            raise ValueError(f'{label} is missing')
        return None
    if obj.get('currency') != 'USD' or not isinstance(obj.get('amount'), int):
        raise ValueError(f'{label} must be USD integer cents')
    if obj['amount'] < 0:
        raise ValueError(f'{label} must not be negative')
    return obj['amount']


def parse_square(folder: Path | None = None) -> list[CanonicalOrder]:
    folder = folder or FIXTURE_DIR / 'square'
    orders = json.loads((folder / 'orders.json').read_text())['orders']
    payments = json.loads((folder / 'payments.json').read_text())['payments']
    refunds = json.loads((folder / 'refunds.json').read_text())['refunds']
    _unique(orders, 'id', 'square order')
    _unique(payments, 'id', 'square payment')
    by_order: dict[str, list[dict]] = defaultdict(list)
    payment_to_order = {}
    for p in payments:
        by_order[p['order_id']].append(p)
        payment_to_order[p['id']] = p['order_id']
    refunds_by_order: dict[str, list[dict]] = defaultdict(list)
    for ref in refunds:
        if ref['payment_id'] not in payment_to_order:
            raise ValueError(f"refund {ref['id']} references missing payment")
        refunds_by_order[payment_to_order[ref['payment_id']]].append(ref)
    known = {o['id'] for o in orders}
    orphan = set(by_order) - known
    if orphan:
        raise ValueError(f'orphan payment order refs: {sorted(orphan)}')
    output=[]
    for o in orders:
        oid=o['id']
        line_items=[]
        for i in o.get('line_items', []):
            line_items.append(Item(item_id=i['uid'], name=i['name'], quantity=float(i['quantity']),
                                   gross_minor=money(i.get('gross_sales_money'), f'{oid} item gross'),
                                   discount_minor=money(i.get('total_discount_money'), f'{oid} item discount', required=False) or 0))
        if not line_items:
            raise ValueError(f'order {oid} has no line items')
        gross=sum(i.gross_minor for i in line_items)
        discount=money(o.get('total_discount_money'), 'order discount', required=False) or 0
        refund=sum(money(r.get('amount_money'), 'refund.amount_money') for r in refunds_by_order[oid] if r.get('status') == 'COMPLETED')
        if discount + refund > gross:
            raise ValueError(f'order {oid} has refunds + discounts exceeding gross')
        warnings=[]
        if not by_order[oid]:
            warnings.append('No matching payment in separate payment fixture.')
        output.append(CanonicalOrder(
            provider='square', source_order_id=oid, location_id=o['location_id'], created_at=o['created_at'], status=o.get('state', 'UNKNOWN'), customer_id=o.get('customer_id') or None,
            gross_minor=gross, discount_minor=discount, refund_minor=refund, net_sales_minor=gross-discount-refund,
            tax_minor=money(o.get('total_tax_money'), 'total_tax_money', required=False),
            tip_minor=money(o.get('total_tip_money'), 'total_tip_money', required=False),
            items=line_items, payments=[Payment(payment_id=p['id'],amount_minor=money(p.get('amount_money'),'payment amount'),status=p.get('status','UNKNOWN')) for p in by_order[oid]],
            lineage={'order_file':'orders.json', 'payment_file':'payments.json', 'refund_file':'refunds.json'}, warnings=warnings
        ))
    return output


def source_payload(provider: str) -> dict[str, str]:
    folder=FIXTURE_DIR/provider
    if provider == 'toast':
        return {p.name:p.read_text(encoding='utf-8') for p in sorted(folder.glob('*.csv'))}
    if provider == 'square':
        return {p.name:p.read_text(encoding='utf-8') for p in sorted(folder.glob('*.json'))}
    raise ValueError('Unknown provider')


def parse(provider: str) -> list[CanonicalOrder]:
    if provider == 'toast':return parse_toast()
    if provider == 'square':return parse_square()
    raise ValueError('Unknown provider')
