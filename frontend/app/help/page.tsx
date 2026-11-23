import Link from 'next/link';
import {ArrowRight,BookOpen,Database,ShieldCheck,LifeBuoy,Receipt,CalendarClock} from 'lucide-react';

const items:[string,string][]=[
 ['How do I connect Square?', 'Use Connections to authorize a Square Sandbox seller. Select active, physical test locations, then run Sync now. Real Square production access is deliberately disabled.'],
 ['Why does the import take time?', 'TableSignal fetches historical orders in weekly windows per location. A partial import stays marked importing. Wait for every monitored location to finish before interpreting trends.'],
 ['Why are my weekly findings paused?', 'A weekly comparison needs the complete current week and four complete baseline weeks for all monitored locations. Stale, partial, disconnected and failed syncs pause claims; missing orders must not look like a decline.'],
 ['How are sales, refunds and taxes counted?', 'Net sales exclude tax, tips and service charges; completed refunds are counted on their refund date. Square reports may differ for gift cards and comps. Use Check against Square to reconcile by location and local day.'],
 ['What can I trust about returning guests?', 'Only transactions with a Square customer ID can contribute to identified-guest and repeat metrics. Unknown guests are not linked to identities. Correlations are not evidence that promotions caused more visits.'],
 ['What is the price?', 'This preview uses a no-card trial or Stripe TEST checkout. The displayed location-based pricing is a proposal, not a live charge. Quantity is based on the monitored locations selected in Square Sandbox.'],
 ['Where are invoices and cancellation?', 'Go to Subscription & Billing. In the test environment you can review a test checkout, invoices/payment method in the configured portal, cancellation and read-only access after expiry. No live money moves.'],
 ['How do I export or delete my data?', 'The workspace owner can download a CSV ZIP under Restaurant Settings. The same page lets the owner delete the workspace after typing its name. Export first; deleting is permanent. Revoke the Square app in Square separately.'],
 ['Can I get technical support?', 'Signed-in users can log a developer-preview support request. It is stored locally for developer review; no email is sent and no response time is guaranteed. Never submit passwords, tokens, or guest information.'],
];
export default function Help(){return <main id="main-content" className="ts-public-page">
 <div className="ts-page-hero"><span className="ts-kicker">HELP CENTER · DEVELOPER PREVIEW</span><h1>Answers about your restaurant data.</h1><p>Set up Square Sandbox, understand what the numbers mean, and manage your workspace safely.</p></div>
 <div className="ts-action-cards">
  <Link href="/onboarding"><BookOpen/> Getting started <ArrowRight/></Link>
  <Link href="/connections"><Database/> Square Sandbox connection <ArrowRight/></Link>
  <Link href="/billing"><Receipt/> Test billing & cancellation <ArrowRight/></Link>
  <Link href="/support"><LifeBuoy/> Contact developer support <ArrowRight/></Link>
  <Link href="/settings"><ShieldCheck/> Export or delete data <ArrowRight/></Link>
 </div>
 <section className="ts-faq"><h2>Frequently asked questions</h2>{items.map(([question,answer])=><details key={question}>
   <summary>{question}</summary><p>{answer}</p></details>)}</section>
 <div className="ts-caution"><CalendarClock size={20}/><div><strong>Preview limitations</strong><p>Real merchant data, production payments, legally approved terms and guaranteed support are not yet available. See the <Link href="/privacy">draft Privacy Policy</Link>.</p></div></div>
 </main>}
