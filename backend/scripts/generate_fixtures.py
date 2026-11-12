"""Generate only fictional demo records, not real vendor exports."""
import csv
import json
import random
from pathlib import Path
from datetime import datetime,timedelta,timezone
from decimal import Decimal

root=Path(__file__).resolve().parent.parent/'fixtures'
random.seed(219)
menus=[('Crispy tofu bowl',1290),('Spicy chicken bowl',1490),('Sesame noodle cup',890),('Miso garden salad',1050),('Citrus sparkling tea',490),('Sweet potato fries',650),('Matcha iced latte',620),('Korean BBQ rice',1690)]
locations_t=['Northline · Downtown','Northline · Lakeside','Northline · Market','Northline · Eastside']
locations_s=['sq-downtown','sq-lakeside','sq-market','sq-eastside']
start=datetime(2026,10,27,11,10,tzinfo=timezone.utc)

def dec(v):return f'{v/100:.2f}'

toast_orders=[];toast_items=[];toast_payments=[]
sq_orders=[];sq_payments=[];sq_refunds=[]
for provider in ['toast','square']:
 for idx in range(1,29):
  loc=(idx-1)%4
  order_id=(f'910{idx:04d}' if provider=='toast' else f'sq-order-{idx:04d}')
  dt=start+timedelta(days=(idx*3)%21,hours=idx%8,minutes=idx*7)
  selected=random.sample(menus,k=random.choice([1,2,2,3]))
  selected_items=[]
  gross=0
  for j,(name,unit) in enumerate(selected,1):
   qty=random.choice([1,1,1,2]); amount=unit*qty; gross+=amount
   selected_items.append((j,name,qty,amount))
  discount=random.choice([0,0,0,150,250,300]); discount=min(discount,gross)
  refund=300 if idx in [7,18,26] else 0
  tax=round((gross-discount)*0.085)
  net=gross-discount-refund
  paid=gross-discount+tax
  if provider=='toast':
   toast_orders.append({'Location':locations_t[loc],'Order Id':order_id,'Order #':str(idx),'Opened':dt.strftime('%m/%d/%Y %H:%M:%S'),'Discount Amount':dec(discount),'Tax':dec(tax),'Tip':dec(0),'Total':dec((gross-discount)+tax),'Voided':'False'})
   for j,name,qty,amount in selected_items:
    toast_items.append({'Location':locations_t[loc], 'Order Id':order_id,'Item Selection Id':str(int(order_id)*10+j),'Menu Item':name,'Qty':str(qty),'Gross Price':dec(amount),'Discnt':dec(discount if j==1 else 0),'Void?':'False'})
   if idx==3:
    # Two-part payment, one order. Split on cash/card, demonstrating one-to-many joins.
    portions=[paid//2,paid-paid//2]
   else:portions=[paid]
   for k,port in enumerate(portions,1):
    toast_payments.append({'Location':locations_t[loc], 'Order Id':order_id,'Payment Id':f'{order_id}{k}',
      'Amount':dec(port),'Tip':'0.00','Status':'PAID','Refund Amount':dec(refund if k==1 else 0)})
  else:
   line_items=[{'uid':f'li-{idx:04d}-{j}', 'name':name,'quantity':str(qty),
               'gross_sales_money':{'amount':amount,'currency':'USD'},
               'total_discount_money':{'amount':discount if j==1 else 0,'currency':'USD'}} for j,name,qty,amount in selected_items]
   sq_orders.append({'id':order_id,'location_id':locations_s[loc], 'created_at':dt.isoformat(), 'state':'COMPLETED',
                     'line_items':line_items, 'total_discount_money':{'amount':discount,'currency':'USD'},
                     'total_tax_money':{'amount':tax,'currency':'USD'}, 'total_tip_money':{'amount':0,'currency':'USD'},
                     'total_money':{'amount':gross-discount+tax,'currency':'USD'}})
   payment_id=f'sq-payment-{idx:04d}'
   sq_payments.append({'id':payment_id,'order_id':order_id,'status':'COMPLETED','amount_money':{'amount':gross-discount+tax,'currency':'USD'}})
   if refund:
    sq_refunds.append({'id':f'sq-refund-{idx:04d}', 'payment_id':payment_id, 'status':'COMPLETED', 'amount_money':{'amount':refund,'currency':'USD'}})

toast=root/'toast';toast.mkdir(parents=True,exist_ok=True)
for fn,rows in [('OrderDetails.csv',toast_orders),('ItemSelectionDetails.csv',toast_items),('PaymentDetails.csv',toast_payments)]:
 with (toast/fn).open('w',encoding='utf-8',newline='') as h:
  writer=csv.DictWriter(h,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
sq=root/'square';sq.mkdir(parents=True,exist_ok=True)
for fn,data in [('orders.json',{'orders':sq_orders}),('payments.json',{'payments':sq_payments}),('refunds.json',{'refunds':sq_refunds})]:
 (sq/fn).write_text(json.dumps(data,indent=2),encoding='utf-8')
print('generated',len(toast_orders),'Toast and',len(sq_orders),'Square orders; synthetic sample input only')
