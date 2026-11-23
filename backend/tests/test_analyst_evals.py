"""M4 analyst evaluation suite: the verified-rules analyst must stay grounded and honest.

Each case is a realistic data situation plus a question. Every answer is scored on:
- grounded: every number in the answer comes from the verified summary (no invented figures)
- cites: evidence keys are given and exist in the summary
- honest: no causal language; insufficient data is said plainly
The suite must pass 100% for the rules engine. Any optional LLM layer is held to the same checks.
"""
import re

import pytest

from app.insights import analyze_orders, answer_question

CAUSAL = re.compile(r'\b(caused|causes|causing|drove|driven by|resulted in|led to|because of (the|your) (promo|discount|campaign))\b', re.I)


def orders(n, loc='L1', customer=lambda i: f'c{i % 10}', net=2000, discount=0, status='COMPLETED', day=lambda i: f'2026-11-{1 + i % 20:02d}'):
    return [{'provider': 'square', 'location_id': loc, 'source_order_id': f'{loc}-{i}', 'created_at': day(i) + 'T12:00:00Z',
             'local_date': day(i), 'status': status, 'customer_id': customer(i), 'net_sales_minor': net,
             'discount_minor': discount, 'campaign_code': None, 'campaign_discount_minor': 0} for i in range(n)]


CASES = {
    'typical': (orders(120) + orders(80, loc='L2'), []),
    'no_data': ([], []),
    'low_coverage': (orders(200, customer=lambda i: f'c{i}' if i % 10 == 0 else None), []),
    'skewed_locations': (orders(190, loc='Big') + orders(10, loc='Tiny'), []),
    'refunds': (orders(100), [{'location_id': 'L1', 'local_date': '2026-11-05', 'amount_minor': 15000}]),
    'heavy_discounts': (orders(100, discount=800), []),
    'all_anonymous': (orders(50, customer=lambda i: None), []),
}
QUESTIONS = ['Summarize my sales', 'What do we know about returning customers?', 'Which locations have the most sales?',
             'Did my discount work?', 'Why did sales go up?', 'What should I do next?']


def _numbers(text):
    return [float(x.replace(',', '').rstrip('%').lstrip('$')) for x in re.findall(r'\$?\d[\d,]*(?:\.\d+)?%?', text)]


def _allowed(summary):
    vals = {0.0, 1.0, 2.0}  # "at least twice", "one", etc.
    def walk(v, money=False):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            vals.update({float(v), round(float(v), 1), round(float(v))})
            if money:
                vals.update({round(v / 100, 2), round(v / 100)})
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(x, money or k.endswith('_minor'))
        elif isinstance(v, list):
            vals.add(float(len(v)))
            for x in v:
                walk(x, money)
    walk(summary)
    return vals


def _score(summary, question):
    r = answer_question(question, summary)
    text = r['answer']
    allowed = _allowed(summary)
    invented = [n for n in _numbers(text) if not any(abs(n - a) < 0.011 for a in allowed)]
    checks = {
        'grounded': not invented,
        'cites': bool(r.get('evidence_keys')) and all(k in summary for k in r['evidence_keys']),
        'no_causal_claims': not CAUSAL.search(text),
        'says_when_data_is_missing': summary['orders'] > 0 or bool(re.search(r'\b(no|not|cannot|insufficient)\b', text, re.I)),
    }
    return checks, text, invented


def test_analyst_eval_suite_passes_every_check():
    failures, total = [], 0
    for case, (rows, refunds) in CASES.items():
        summary = analyze_orders(rows, refunds)
        for q in QUESTIONS:
            checks, text, invented = _score(summary, q)
            total += len(checks)
            failures += [f'{case} / {q!r}: {name} failed. Answer: {text!r} Invented: {invented}'
                         for name, ok in checks.items() if not ok]
    score = 1 - len(failures) / total
    print(f'analyst eval: {score:.1%} of {total} checks passed')
    assert score == 1.0, '\n'.join(failures)


def test_low_coverage_is_disclosed_in_guest_answers():
    summary = analyze_orders(*CASES['low_coverage'])
    text = answer_question('What do we know about returning customers?', summary)['answer']
    assert 'coverage' in text.lower() and str(summary['identification_coverage_percent']) in text


def test_refunds_are_reflected_in_sales_answers():
    summary = analyze_orders(*CASES['refunds'])
    assert summary['net_sales_minor'] == 100 * 2000 - 15000
    text = answer_question('Summarize my sales', summary)['answer']
    assert '$1,850.00' in text or '1,850' in text, text


def test_skewed_locations_rank_correctly():
    summary = analyze_orders(*CASES['skewed_locations'])
    text = answer_question('Which locations have the most sales?', summary)['answer']
    assert text.index('Big') < text.index('Tiny') if 'Tiny' in text else 'Big' in text


def test_eval_catches_an_invented_number(monkeypatch):
    """The suite itself must fail on a fabricated figure (guards against a toothless eval)."""
    import app.insights as insights
    real = insights.answer_question

    def fabricating(question, summary):
        r = real(question, summary)
        r['answer'] += ' Sales rose 37.5% because of the promo.'
        return r
    summary = analyze_orders(*CASES['typical'])
    monkeypatch.setattr('tests.test_analyst_evals.answer_question', fabricating, raising=False)
    global answer_question
    saved, answer_question = answer_question, fabricating
    try:
        checks, _, invented = _score(summary, 'Summarize my sales')
    finally:
        answer_question = saved
    assert not checks['grounded'] and 37.5 in invented and not checks['no_causal_claims']
