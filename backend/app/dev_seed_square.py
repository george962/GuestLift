"""Populate YOUR OWN Square Sandbox with paid fictional orders.

Developer CLI ONLY; never routed to public HTTP and never uses Square production.
Execute ONLY when you intentionally choose to create test transactions:

  docker compose exec backend env TABLESIGNAL_SEED_CONFIRM=YES python -m app.dev_seed_square

This script is an optional API integration exercise, not required for TableSignal tests.
"""
from __future__ import annotations
import os
import sys
import uuid
import httpx

BASE='https://connect.squareupsandbox.com'
HEADERS_VERSION='2026-09-16'


def main():
    if os.getenv('TABLESIGNAL_SEED_CONFIRM') != 'YES':
        raise SystemExit('Nothing created. Set TABLESIGNAL_SEED_CONFIRM=YES after reviewing this script.')
    token=os.getenv('SQUARE_SANDBOX_ACCESS_TOKEN','')
    if not token:
        raise SystemExit('SQUARE_SANDBOX_ACCESS_TOKEN is not configured in your local backend.')
    headers={'Authorization':f'Bearer {token}','Square-Version':HEADERS_VERSION,
             'Content-Type':'application/json'}
    with httpx.Client(timeout=20, follow_redirects=False,headers=headers) as client:
        def api(method,path,body=None):
            r=client.request(method,BASE+path,json=body)
            if r.status_code >= 400:
                # Don't log credentials or full response bodies.
                raise RuntimeError(f'Square Sandbox {path} returned HTTP {r.status_code}. Check API permissions or request schema.')
            return r.json()
        locations=api('GET','/v2/locations').get('locations',[])
        active=[loc for loc in locations if loc.get('status')=='ACTIVE' and loc.get('currency') in (None,'USD')]
        if not active:raise SystemExit('No active USD Square Sandbox location found.')
        loc=active[0]['id']
        print('Square Sandbox location selected. Creating fictional customers and paid orders.')
        test_customers=[]
        for name in ('Sandbox Alpha','Sandbox Bravo','Sandbox Charlie','Sandbox Delta'):
            response=api('POST','/v2/customers',{'given_name':name,'idempotency_key':str(uuid.uuid4())})
            test_customers.append(response['customer']['id'])
        amounts=[1250,1890,2325,1640,3350,1745,2890,1175]
        names=['Coffee & sandwich','Lunch bowl','Salad combo','Breakfast special',
               'Dinner bowl','Coffee & cookie','Lunch special','Soup & tea']
        customer_indices=[0,1,0,2,1,0,3,2]
        paid=0
        for i,(amount,name) in enumerate(zip(amounts,names)):
            customer=test_customers[customer_indices[i]]
            order_response=api('POST','/v2/orders',{
                'idempotency_key':str(uuid.uuid4()),
                'order':{'location_id':loc,'customer_id':customer,
                         'line_items':[{'quantity':'1','name':name,
                                        'base_price_money':{'amount':amount,'currency':'USD'}}]},
            })
            order=order_response['order']
            payment_response=api('POST','/v2/payments',{
                'idempotency_key':str(uuid.uuid4()),'source_id':'cnon:card-nonce-ok',
                'amount_money':{'amount':amount,'currency':'USD'},'location_id':loc,
                'order_id':order['id'],'customer_id':customer,'autocomplete':False,
            })
            payment=payment_response['payment']
            api('POST',f"/v2/orders/{order['id']}/pay",{
                'idempotency_key':str(uuid.uuid4()), 'payment_ids':[payment['id']],
            })
            paid+=1
            print(f'Created Sandbox paid order {paid}/8 (fictional).')
        print(f'Finished: {paid} Square Sandbox paid orders for 4 fictional customer profiles.')
        print('Now return to TableSignal Connections and choose Sync last 180 days.')


if __name__=='__main__':
    try:main()
    except (KeyError, ValueError, httpx.RequestError, RuntimeError) as exc:
        print(f'Sandbox seeding stopped: {exc}',file=sys.stderr)
        sys.exit(1)
