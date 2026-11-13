"""Small, deterministic, evidence-first restaurant insights. No autonomous SQL or PII in outputs."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime


def analyze_orders(orders: list[dict]) -> dict:
    """Summarize already tenant-scoped orders. All financial amounts are integer cents."""
    clean = [o for o in orders if o.get('status') not in ('VOIDED', 'CANCELED')]
    locations = defaultdict(lambda: {'orders': 0, 'net_sales_minor': 0, 'discount_minor': 0})
    customers = defaultdict(int)
    daily = defaultdict(lambda: {'orders': 0, 'net_sales_minor': 0})
    campaigns = defaultdict(lambda: {'redemptions': 0, 'net_sales_minor': 0, 'recorded_discount_minor': 0})
    known_orders = 0
    for o in clean:
        loc = f"{o['provider']}:{o['location_id']}"
        row = locations[loc]
        row['orders'] += 1
        row['net_sales_minor'] += int(o['net_sales_minor'])
        row['discount_minor'] += int(o.get('discount_minor', 0))
        date = str(o.get('created_at', ''))[:10]
        if date:
            daily[date]['orders'] += 1
            daily[date]['net_sales_minor'] += int(o['net_sales_minor'])
        if o.get('customer_id'):
            known_orders += 1
            customers[(o['provider'],o['customer_id'])] += 1
        campaign = o.get('campaign_code')
        if campaign:
            campaigns[campaign]['redemptions'] += 1
            campaigns[campaign]['net_sales_minor'] += int(o['net_sales_minor'])
            campaigns[campaign]['recorded_discount_minor'] += int(o.get('campaign_discount_minor', 0))
    total = sum(int(o['net_sales_minor']) for o in clean)
    discounts = sum(int(o.get('discount_minor',0)) for o in clean)
    repeats = sum(1 for visits in customers.values() if visits >= 2)
    result = {
        'data_origin': 'fictional_workspace_seed',
        'orders': len(clean),
        'net_sales_minor': total,
        'discount_minor': discounts,
        'average_order_minor': round(total/len(clean)) if clean else 0,
        'identified_orders': known_orders,
        'anonymous_orders':len(clean)-known_orders,
        'identification_coverage_percent': round(100*known_orders/len(clean),1) if clean else 0,
        'identified_customers': len(customers),
        'repeat_customers': repeats,
        'repeat_customer_rate_percent': round(100*repeats/len(customers),1) if customers else None,
        'locations': [{'location': k,**v} for k,v in sorted(locations.items())],
        'daily': [{'date': k, **v} for k,v in sorted(daily.items())],
        'campaigns': [{'code': k,'name': k,'discount_minor':v['recorded_discount_minor'],
                       'modeled_contribution_minor': None,**v} for k,v in sorted(campaigns.items())],
        'methodology': {
            'sales': 'Sum of net sales on non-voided synthetic orders, cents; not incremental revenue.',
            'repeat': 'At least 2 observed orders for the same provider-scoped synthetic customer ID. Anonymous orders excluded.',
            'campaigns': 'Recorded discounts on matched synthetic redemptions; not incremental profit.',
            'coverage': 'Identified orders / observed non-voided orders. No cross-provider customer merging.'
        },
    }
    return result


def answer_question(question: str, summary: dict) -> dict:
    """Select a small approved read-only metric tool; never generate SQL from free text."""
    q = question.lower().strip()[:500]
    if not q:
        raise ValueError('Question is required')
    source = str(summary.get('data_origin', 'fictional_workspace_seed')) + ' / normalized orders'
    fmt = lambda n: f"${n/100:,.2f}"
    if any(k in q for k in ('customer','repeat','loyal','retention','return','lapse')):
        n=summary['identified_customers']; rate=summary['repeat_customer_rate_percent']
        answer = (f"Among {n} identified customers in this limited sample, {summary['repeat_customers']} purchased at least twice "
                  f"({rate}% of identified customers). Identity coverage is {summary['identification_coverage_percent']}% of orders. "
                  "This observed-sample repeat rate is not a retention experiment; anonymous customers are excluded.") if n else 'No usable customer identifiers are present, so repeat purchasing cannot be estimated.'
        tool='repeat_customer_analysis'; evidence=['identified_customers','repeat_customers','repeat_customer_rate_percent','identification_coverage_percent']
        next_step='Compare the same customer cohorts over equal observation windows once historical data is available.'
    elif any(k in q for k in ('coupon','discount','campaign','promotion','offer')):
        offers=summary['campaigns']
        total_redemptions=sum(o['redemptions'] for o in offers)
        campaign_discounts=sum(o['recorded_discount_minor'] for o in offers)
        answer=(f"The available dataset contains {total_redemptions} matched redemptions across {len(offers)} campaigns, "
                f"with {fmt(campaign_discounts)} in recorded campaign discounts. "
                "This is descriptive attribution, not proof the offers created additional sales or profit.")
        tool='promotion_performance';evidence=['campaigns','discount_minor'];next_step='Run a randomized holdout and measure contribution per eligible customer.'
    elif any(k in q for k in ('location','store','branch','best','worst')):
        locs=sorted(summary['locations'],key=lambda o:o['net_sales_minor'],reverse=True)
        if locs:
            a=locs[0];answer=(f"In the observed sample, {a['location']} has the highest observed net sales "
            f"({fmt(a['net_sales_minor'])} from {a['orders']} orders). Store size, hours, and coverage differ; this is not a performance ranking after adjustment.")
        else:answer='There are no location records to compare.'
        tool='location_comparison';evidence=['locations'];next_step='Compare normalized, same-period sales with operating hours and traffic before making a location decision.'
    else:
        answer=(f"I can verify {summary['orders']} observed orders and {fmt(summary['net_sales_minor'])} in net sales "
                f"(average {fmt(summary['average_order_minor'])} per order). "
                "To explain a cause, we would need comparison periods, operational context, and suitable evidence.")
        tool='sales_overview';evidence=['orders','net_sales_minor','average_order_minor'];next_step='Ask about returning customers, campaign discounts, or individual locations.'
    return {'question':question[:500], 'answer':answer,'tool':tool,'evidence_keys':evidence,
            'source':source,'recommended_next_step':next_step,
            'causal_claim':False,'data_origin':summary.get('data_origin', 'synthetic'),'engine':'verified_rules',
            'disclaimer':'Sandbox/development analysis only. No independent causal inference; see metric limitations.'}
