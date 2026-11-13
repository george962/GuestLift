import Link from 'next/link';
import {ArrowRight,Check,HelpCircle,LockKeyhole,ShieldCheck,Sparkles,X} from 'lucide-react';

const features=[
 ['Explore a complete fictional restaurant','Included','Included'],
 ['Your own connected POS data','No','One location; supported provider'],
 ['Scheduled refresh and source health','No','Included after live launch'],
 ['Verified sales, guest and discount evidence','Sample only','Your business'],
 ['AI analyst: ask natural-language questions','Sample scripted responses','Model-powered answers from scoped aggregates'],
 ['Connect-the-dots evidence relationships','Sample only','Account-specific'],
 ['Compare offer-cost scenarios','Sample only','Included'],
 ['Save decisions and review experiments','No','Included'],
 ['Send marketing campaigns / guaranteed ROI','No','Not included'],
];
export default function Pricing(){return <main className="ts-public-page ts-pricing-page">
 <div className="ts-page-hero ts-centered"><span className="ts-kicker">TABLESIGNAL · CLEAR PRODUCT VALUE</span>
  <h1>Know why customers return.<br/>Decide what to do next.</h1>
  <p>One focused restaurant intelligence product. No complicated tiers or paying just to unlock more charts. See how it works free; the paid plan will analyze your own data.</p>
 </div>
 <div className="ts-plans ts11-pricing-plans">
  <section className="ts-plan"><span>AVAILABLE TODAY</span><h2>Explore</h2><div className="ts-plan-price">$0</div><p>Try the full experience using an illustrative restaurant—no business credentials or credit card needed.</p>
   <ul>{['Interactive fictional restaurant','Example sales and returning guest analysis','Sample evidence-based answers','Offer-cost scenario preview'].map(x=><li key={x}><Check size={17}/>{x}</li>)}</ul>
   <Link className="ts-btn-outline" href="/workspace">Try the free demo <ArrowRight size={16}/></Link><small>Always free · Fictional data only</small>
  </section>
  <section className="ts-plan featured"><span>PROPOSED PILOT PRICE · NOT ON SALE YET</span><h2>Growth</h2><div className="ts-plan-price">$99<small> / location / month</small></div><p>An always-current picture of your own restaurant, prioritized decisions, and an AI analyst grounded in real evidence.</p>
   <ul>{['Secure connection to an approved POS','Automated data refresh after live integration','Evidence graph for sales, guests, and discounts','Ask the AI analyst follow-up questions','Compare opportunities and save experiments','Account-scoped insights and data quality'].map(x=><li key={x}><Check size={17}/>{x}</li>)}</ul>
   <div className="ts11-price-cta"><LockKeyhole size={16}/> Production sign-ups are not enabled yet. The local Stripe checkout uses test cards only.</div>
   <Link className="ts-btn-outline" href="/product">See how Growth works <ArrowRight size={16}/></Link><small>Proposed founding-customer offer: pilot first, billing after verified launch. No live charges today.</small>
  </section>
 </div>
 <section className="ts11-feature-comparison"><div><span className="ts-kicker">WHAT YOU ACTUALLY RECEIVE</span><h2>A clear difference between free and paid.</h2><p>Paid access is about continuously finding opportunities in your own operational data—not access to a generic chat box.</p></div>
  <div className="ts11-table-wrap"><table><thead><tr><th>Capability</th><th>Explore · Free</th><th>Growth · $99/location</th></tr></thead><tbody>{features.map(([feature,free,paid])=><tr key={feature}><td>{feature}</td><td>{free==='No'?<><X size={16}/> Not included</>:free}</td><td>{paid==='Not included'?<><X size={16}/> Not included</>:<><Check size={16}/> {paid}</>}</td></tr>)}</tbody></table></div>
 </section>
 <div className="ts-caution"><ShieldCheck size={22}/><div><b>Important: pricing is not live yet.</b><p>Your current $149 Stripe Sandbox Growth checkout is a test subscription, not a real payment. A proposed $99 live price requires an actual commercial Stripe Price ID, merchant onboarding security review, data processing/legal terms, and successful live integration testing before we can start billing customers.</p></div></div>
 </main>}
