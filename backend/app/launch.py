"""Truthful product-readiness indicators; no live credentials or merchant data accepted."""
import os
from fastapi import APIRouter, Depends
from .local_auth import authenticated_subject

router = APIRouter(prefix='/api/launch', tags=['Launch readiness'])


@router.get('/readiness')
def readiness(sub: str = Depends(authenticated_subject)):
    """Feature flags describe tested capabilities, not a security certification."""
    return {
        'release':'0.11.0',
        'development_mode':True,
        'can_accept_real_merchant_data':False,
        'can_accept_real_payments':False,
        'components':[
            {'id':'square_sandbox','name':'Square Sandbox API','state':'development','note':'OAuth/dev-token connection, manual sync of test orders'},
            {'id':'square_live','name':'Live Square OAuth','state':'blocked','note':'Requires production app approval, HTTPS, tenant security review, migration and real-seller integration tests'},
            {'id':'toast_live','name':'Toast live API','state':'blocked','note':'Partner/API access and merchant authorization not implemented'},
            {'id':'stripe_test','name':'Stripe test billing','state':'development','note':'Server-verified Checkout, webhook, recovery and customer portal'},
            {'id':'stripe_live','name':'Stripe live billing','state':'blocked','note':'No live keys accepted; needs hardened account platform, legal/tax setup and webhook verification'},
            {'id':'ai_analyst','name':'OpenAI evidence-based analyst','state':'development' if os.getenv('GUESTLIFT_ENABLE_LLM')=='1' and os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL') else 'configuration_required',
             'note':'Read-only, aggregate-only model context; API key and approved model supplied by operator'},
            {'id':'auth','name':'Production identity and security','state':'blocked','note':'Local developer sessions are not a production identity service'},
            {'id':'privacy','name':'Privacy, retention and deletion','state':'blocked','note':'Merchant agreements, consent scope, deletion requests, incident response and backups require review'},
        ],
        'next_milestone':'Secure hosted staging environment and production Square OAuth end-to-end verification with a consenting pilot restaurant.'
    }
