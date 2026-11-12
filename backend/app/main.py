from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .adapters import parse, source_payload
from .database import init_db, reset_db, persist, metrics, recent_runs

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app=FastAPI(title='GuestLift Demo API',version='0.1.0',lifespan=lifespan,
    description='Local demo using fabricated Toast and Square-shaped sample inputs; not a live POS integration.')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000','http://127.0.0.1:3000'], allow_methods=['GET','POST'], allow_headers=['*'])

def validate_provider(provider: str):
    if provider not in ('toast','square'):raise HTTPException(status_code=404,detail='Provider not supported')

@app.get('/api/health')
def health():return {'status':'ok','mode':'synthetic_demo'}

@app.get('/api/providers')
def providers():return [{'id':'toast','label':'Toast POS','mode':'fabricated CSV fixtures'},{'id':'square','label':'Square POS','mode':'Square-shaped JSON fixtures, not a live Sandbox session'}]

@app.get('/api/preview/{provider}')
def preview(provider: str):
    validate_provider(provider)
    try:
        rows=parse(provider)
        return {'provider':provider,'fixture_only':True,'files':source_payload(provider),
                'records':[r.model_dump() for r in rows],
                'summary':{'orders':len(rows),'items':sum(len(x.items) for x in rows),'payments':sum(len(x.payments) for x in rows),
                           'net_sales_minor':sum(x.net_sales_minor for x in rows),
                           'discounts_minor':sum(x.discount_minor for x in rows),'refunds_minor':sum(x.refund_minor for x in rows)}}
    except (OSError,KeyError,ValueError) as e:raise HTTPException(status_code=422,detail=str(e))

@app.post('/api/import/{provider}')
def import_sample(provider: str):
    validate_provider(provider)
    try:
        rows=parse(provider)
        inserted,duplicates,run_id,status=persist(rows)
        return {'provider':provider,'import_id':str(run_id),'status':status,'inserted':inserted,'duplicates':duplicates,'rejected':0,
                'issues':[message for row in rows for message in row.warnings],'orders':[r.model_dump() for r in rows]}
    except (OSError,KeyError,ValueError) as e:raise HTTPException(status_code=422,detail=str(e))

@app.get('/api/metrics')
def get_metrics(provider: str | None=None):
    if provider:validate_provider(provider)
    return metrics(provider)

@app.get('/api/imports')
def imports():return {'runs':recent_runs()}

@app.post('/api/reset')
def reset():
    reset_db()
    return {'status':'reset','warning':'All local demo import data cleared'}
