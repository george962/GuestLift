"""Weekly brief and decision outcomes (docs/PRODUCT_PLAN.md M4).

Honesty rules, enforced here rather than in copy:
- A change is reported only when it is large relative to normal week-to-week movement
  (|z| >= 2 "clear", >= 1 "possible"). Otherwise the brief says nothing notable changed.
- Every finding carries its evidence: this week's value, the 4-week baseline, the change,
  the sample size, and the weekly variability it was judged against.
- Nothing claims a cause. Outcome readouts say "after the change" and, when last year's
  data exists, how much of the movement is the usual seasonal pattern.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, pstdev

METRICS = {
    'net_sales': 'Net sales',
    'orders': 'Orders',
    'average_order': 'Average order',
    'discount_spend': 'Discount spend',
    'returning_share': 'Share of known guests who came back',
}
MONEY = {'net_sales', 'average_order', 'discount_spend'}


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Monday


def last_complete_week(today: date) -> date:
    return week_start(today) - timedelta(days=7)


def _weekly(rows: list[dict], refunds: list[dict], start: date, weeks: int, location: str | None = None) -> list[dict]:
    """Per-week metrics for `weeks` weeks beginning at `start` (local dates)."""
    out = []
    for i in range(weeks):
        lo, hi = start + timedelta(days=7 * i), start + timedelta(days=7 * (i + 1))
        week = [r for r in rows if lo.isoformat() <= r['local_date'] < hi.isoformat()
                and (location is None or r['location_id'] == location)]
        ref = sum(f['amount_minor'] for f in refunds if lo.isoformat() <= f['local_date'] < hi.isoformat()
                  and (location is None or f['location_id'] == location))
        net = sum(r['net_sales_minor'] for r in week) - ref
        seen_before = {r['customer_id'] for r in rows if r['customer_id'] and r['local_date'] < lo.isoformat()
                       and (location is None or r['location_id'] == location)}
        guests = {r['customer_id'] for r in week if r['customer_id']}
        out.append({'week_start': lo.isoformat(), 'orders': len(week), 'net_sales': net,
                    'average_order': round(net / len(week)) if week else 0,
                    'discount_spend': sum(r['discount_minor'] for r in week),
                    'returning_share': round(100 * len(guests & seen_before) / len(guests), 1) if guests else None,
                    'identified_share': round(100 * sum(1 for r in week if r['customer_id']) / len(week), 1) if week else 0})
    return out


def _judge(current: float | None, history: list[float | None]) -> dict | None:
    values = [h for h in history if h is not None]
    if current is None or len(values) < 3:
        return None
    base, spread = mean(values), pstdev(values)
    if base == 0:
        return None
    change = (current - base) / abs(base)
    z = (current - base) / spread if spread > 0 else (math.inf if current != base else 0.0)
    confidence = 'clear' if abs(z) >= 2 else 'possible' if abs(z) >= 1 else None
    return {'baseline': round(base, 1), 'change_percent': round(100 * change, 1), 'z': round(z, 2) if math.isfinite(z) else None,
            'weekly_spread': round(spread, 1), 'confidence': confidence}


def _fmt(metric: str, v: float) -> str:
    if metric in MONEY:
        return f'${v / 100:,.2f}'
    if metric == 'returning_share':
        return f'{v:.1f}%'
    return f'{int(round(v)):,}'


def build_brief(rows: list[dict], refunds: list[dict], locations: dict[str, str], today: date) -> dict:
    """The Monday brief: last complete week vs the 4 weeks before, overall and per location."""
    start = last_complete_week(today)
    base_start = start - timedelta(days=28)
    findings = []
    scopes = [(None, 'All locations')] + sorted(locations.items(), key=lambda kv: kv[1])
    totals = None
    for loc, label in scopes:
        weeks = _weekly(rows, refunds, base_start, 5, loc)
        history, current = weeks[:4], weeks[4]
        if loc is None:
            totals = {'this_week': current, 'baseline_weeks': history}
        if len([w for w in history if w['orders']]) < 3:
            continue  # not enough history to judge
        for metric in ('net_sales', 'orders', 'average_order', 'discount_spend', 'returning_share'):
            verdict = _judge(current[metric], [w[metric] for w in history])
            if not verdict or not verdict['confidence']:
                continue
            if loc is None and metric in ('net_sales', 'orders') and len(locations) > 1:
                pass  # keep the overall view too; per-location findings explain where
            direction = 'up' if verdict['change_percent'] > 0 else 'down'
            impact = abs(current[metric] - verdict['baseline']) if metric in ('net_sales', 'discount_spend') else \
                abs(current['net_sales'] - mean(w['net_sales'] for w in history))
            findings.append({
                'id': f"{loc or 'all'}:{metric}", 'scope': label, 'location_id': loc, 'metric': metric,
                'title': f"{label}: {METRICS[metric].lower()} {direction} {abs(verdict['change_percent']):.0f}%",
                'detail': (f"{_fmt(metric, current[metric])} last week vs a 4-week average of {_fmt(metric, verdict['baseline'])}. "
                           + ('A change this size is well outside normal week-to-week movement.' if verdict['confidence'] == 'clear'
                              else 'A change this size happens sometimes by chance; watch next week.')),
                'confidence': verdict['confidence'], 'impact_minor': int(impact),
                'evidence': {'this_week': current[metric], 'baseline': verdict['baseline'],
                             'change_percent': verdict['change_percent'], 'weekly_spread': verdict['weekly_spread'],
                             'z': verdict['z'], 'orders_this_week': current['orders'],
                             'week_start': current['week_start'], 'baseline_from': history[0]['week_start']},
            })
    findings.sort(key=lambda f: (f['confidence'] != 'clear', -f['impact_minor']))
    coverage = totals['this_week']['identified_share'] if totals else 0
    caveats = []
    if coverage < 50:
        caveats.append(f'Only {coverage:.0f}% of last week\'s orders were linked to a known guest, so guest figures describe that share only.')
    if not findings:
        headline = 'Nothing changed more than usual last week.'
    else:
        top = findings[0]
        headline = top['title'] + ('.' if top['confidence'] == 'clear' else ' (possible change).')
    return {'week_start': start.isoformat(), 'week_end': (start + timedelta(days=6)).isoformat(),
            'headline': headline, 'findings': findings[:6], 'totals': totals, 'caveats': caveats,
            'method': 'Last complete week (Mon-Sun, local time) vs the average of the 4 weeks before. A change is shown '
                      'only when it is at least one weekly standard deviation from that average ("possible"), or two ("clear"). '
                      'These are changes, not causes.'}


def metric_value(rows: list[dict], refunds: list[dict], lo: date, hi: date, metric: str, location: str | None) -> tuple[float | None, int]:
    days = (hi - lo).days
    weeks = _weekly(rows, refunds, lo, max(1, days // 7), location)
    if not weeks:
        return None, 0
    n = sum(w['orders'] for w in weeks)
    if metric == 'average_order':
        net = sum(w['net_sales'] for w in weeks)
        return (net / n if n else None), n
    values = [w[metric] for w in weeks if w[metric] is not None]
    return (mean(values) if values else None), n


def outcome(rows: list[dict], refunds: list[dict], metric: str, location: str | None, start: date,
            follow_up: date, earliest: date | None) -> dict:
    """Before vs after a decision, with last year's same weeks when available."""
    span = max(7, ((follow_up - start).days // 7) * 7)
    before_lo, after_hi = start - timedelta(days=span), start + timedelta(days=span)
    after, n_after = metric_value(rows, refunds, start, after_hi, metric, location)
    before, n_before = metric_value(rows, refunds, before_lo, start, metric, location)
    if after is None or before is None or not n_before or not n_after or before == 0:
        return {'available': False, 'message': 'Not enough data before and after the change to compare yet.'}
    change = 100 * (after - before) / abs(before)
    weekly = [w[metric] for w in _weekly(rows, refunds, before_lo, span // 7, location) if w[metric] is not None]
    spread = 100 * pstdev(weekly) / abs(mean(weekly)) if len(weekly) >= 2 and mean(weekly) else None
    seasonal = None
    if earliest and earliest <= before_lo - timedelta(days=364):
        ly_after, _ = metric_value(rows, refunds, start - timedelta(days=364), after_hi - timedelta(days=364), metric, location)
        ly_before, _ = metric_value(rows, refunds, before_lo - timedelta(days=364), start - timedelta(days=364), metric, location)
        if ly_after is not None and ly_before:
            seasonal = 100 * (ly_after - ly_before) / abs(ly_before)
    beyond = change - seasonal if seasonal is not None else None
    judged = abs(beyond if beyond is not None else change)
    if spread is None:
        verdict = 'unclear'
    elif judged >= 2 * spread:
        verdict = 'clear'
    elif judged >= spread:
        verdict = 'possible'
    else:
        verdict = 'no_clear_change'
    words = {'clear': 'A clear change after your decision.', 'possible': 'Possibly a change; it is within the range that sometimes happens by chance.',
             'no_clear_change': 'No change bigger than normal week-to-week movement.', 'unclear': 'Too little history to judge how unusual this is.'}
    parts = [f"{METRICS[metric]} averaged {_fmt(metric, after)} per week after the change vs {_fmt(metric, before)} in the {span // 7} weeks before ({change:+.1f}%)."]
    if seasonal is not None:
        parts.append(f"The same weeks last year moved {seasonal:+.1f}%, so the change beyond the usual seasonal pattern is about {beyond:+.1f} points.")
    else:
        parts.append('There is no data from the same weeks last year, so seasonal effects can\'t be separated out.')
    if spread is not None:
        parts.append(f"Weeks normally vary by about {spread:.1f}%.")
    parts.append('This shows what happened after the decision, not proof that it caused the change.')
    return {'available': True, 'metric': metric, 'location_id': location, 'weeks': span // 7,
            'before': round(before, 1), 'after': round(after, 1), 'change_percent': round(change, 1),
            'seasonal_change_percent': round(seasonal, 1) if seasonal is not None else None,
            'beyond_seasonal_points': round(beyond, 1) if beyond is not None else None,
            'weekly_variation_percent': round(spread, 1) if spread is not None else None,
            'verdict': verdict, 'headline': words[verdict], 'explanation': ' '.join(parts),
            'orders_before': n_before, 'orders_after': n_after}
