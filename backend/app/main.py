from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .adapters import parse, source_payload, parse_toast, parse_square
from .database import init_db, reset_db, persist, metrics, recent_runs
from .saas import router as saas_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app=FastAPI(title='GuestLift Demo API',version='0.5.0',lifespan=lifespan,
    description='Local fictional restaurant analytics, account foundation and Stripe test-mode subscription tools. Never expose demo endpoints publicly.')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000','http://127.0.0.1:3000'], allow_methods=['GET','POST'], allow_headers=['*'])
app.include_router(saas_router)

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


# DELIBERATELY LOCAL-ONLY: synthetic fixture uploader, not a merchant-data service.
# Docker binds port 8000 to 127.0.0.1; never expose it on the public internet.
UPLOAD_FILES = {
    'toast': {'OrderDetails.csv', 'ItemSelectionDetails.csv', 'PaymentDetails.csv'},
    'square': {'orders.json', 'payments.json', 'refunds.json'},
}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # Per file, small demonstration fixtures only.

@app.post('/api/upload/{provider}')
async def import_uploaded_files(provider: str, files: list[UploadFile] = File(...)):
    """Parse, validate, normalize and persist three synthetic demo fixture files."""
    validate_provider(provider)
    expected = UPLOAD_FILES[provider]
    names = [f.filename for f in files]
    if len(names) != len(expected) or set(names) != expected or len(set(names)) != len(names):
        raise HTTPException(status_code=422, detail=f'{provider}: upload exactly {sorted(expected)}')
    with TemporaryDirectory(prefix='guestlift-fixture-') as tmp:
        folder = Path(tmp)
        for file in files:
            # Strict filename allowlist blocks traversal and unknown extensions.
            if file.filename not in expected:
                raise HTTPException(status_code=422, detail='Unexpected file name')
            data = await file.read(MAX_UPLOAD_BYTES + 1)
            if not data or len(data) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=422, detail=f'{file.filename}: file empty or exceeds 2 MB demo limit')
            try:
                data.decode('utf-8-sig')
            except UnicodeDecodeError:
                raise HTTPException(status_code=422, detail=f'{file.filename}: use UTF-8 text')
            (folder / file.filename).write_bytes(data)
        try:
            parsed = parse_toast(folder) if provider == 'toast' else parse_square(folder)
            if not parsed or len(parsed) > 2000:
                raise ValueError('Demo accepts between 1 and 2000 orders per import')
            inserted, duplicates, run_id, status = persist(parsed)
            return {
                'provider': provider,
                'import_id': str(run_id),
                'status': status,
                'inserted': inserted,
                'duplicates': duplicates,
                'rejected': 0,
                'issues': [f'{o.source_order_id}: {warn}' for o in parsed for warn in o.warnings],
                'orders': [o.model_dump() for o in parsed],
                'metrics': metrics(provider),
                'source_mode': 'uploaded_synthetic_demo_files',
            }
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail=f'Validation failed: {str(exc)}') from exc

# Campaigns and redemptions are synthetic and handled on localhost only.
from .campaigns import import_campaign_csvs, MAX_CSV_BYTES
from .database import campaign_reports, customer_summary

CAMPAIGN_FIXTURE_DIR = Path(__file__).resolve().parent.parent / 'fixtures' / 'campaigns'

@app.get('/api/campaigns/report')
def get_campaign_report(margin_percent: int = 35):
    try:
        return campaign_reports(margin_percent)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get('/api/customers/summary')
def get_customer_summary():
    return customer_summary()

@app.post('/api/campaigns/upload')
async def upload_campaigns(campaigns_file: UploadFile = File(...), redemptions_file: UploadFile = File(...)):
    if campaigns_file.filename != 'Campaigns.csv' or redemptions_file.filename != 'Redemptions.csv':
        raise HTTPException(status_code=422, detail='Upload Campaigns.csv and Redemptions.csv exactly')
    campaign_data = await campaigns_file.read(MAX_CSV_BYTES + 1)
    redemption_data = await redemptions_file.read(MAX_CSV_BYTES + 1)
    try:
        outcome = import_campaign_csvs(campaign_data, redemption_data)
        return {**outcome, 'report':campaign_reports(35)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.post('/api/campaigns/demo/load')
def load_fictional_campaigns():
    """Convenience: sample POS orders first, followed by sample coupon redemptions.

    Idempotent; no credential exchange and no real customer data. Uses packaged fixtures.
    """
    for provider in ('toast','square'):
        persist(parse(provider))
    try:
        outcome = import_campaign_csvs((CAMPAIGN_FIXTURE_DIR / 'Campaigns.csv').read_bytes(),
                                       (CAMPAIGN_FIXTURE_DIR / 'Redemptions.csv').read_bytes())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {**outcome, 'report':campaign_reports(35)}
