'use client';
import {useEffect,useMemo,useState, type CSSProperties} from 'react';
import Link from 'next/link';
import {
 ArrowRight,ArrowUpRight,Check,CheckCircle2,ChevronRight,CreditCard,
 Database,FileCheck2,HelpCircle,LockKeyhole,MousePointer2,PlayCircle,
 ShieldCheck,Sparkles,Store,TicketPercent,TrendingUp,Users,Wallet
} from 'lucide-react';
import {MotionTour} from '@/components/motion-tour';
import source from '@/lib/demo-fallback.json';
import sample from '@/lib/campaign-demo.json';
import type {Order} from '@/lib/types';
import {usd} from '@/lib/types';
import {evaluateCampaigns} from '@/lib/campaign-model.mjs';
import {askWorkspace,discoverPatterns,summarizeWorkspace} from '@/lib/workspace-analytics.mjs';

const sampleOrders=[...(source.toast.records as Order[]),...(source.square.records as Order[])];
const campaigns=evaluateCampaigns(sampleOrders,sample.campaigns_csv,sample.redemptions_csv,35);
const summary=summarizeWorkspace(sampleOrders,campaigns.campaigns);
const signals=discoverPatterns(summary);
const flow=[
 {n:'01',title:'Your restaurant',subtitle:'Establish the business context',detail:'Choose your restaurant type, goals, and locations. This helps the platform distinguish useful trends from misleading comparisons.',pill:'Business profile',icon:Store},
 {n:'02',title:'Your transactions',subtitle:'Turn source records into one view',detail:'The synthetic demo takes Toast-shaped or Square-shaped records through one normalized order format, with validation and explicit unknowns.',pill:'Verified source data',icon:Database},
 {n:'03',title:'Your customers',subtitle:'Understand who returns',detail:'Connect known customer IDs to purchasing frequency. See identification coverage so anonymous orders are never mistaken for new guests.',pill:'Guest intelligence',icon:Users},
 {n:'04',title:'Your next decision',subtitle:'Ask a better question',detail:'Compare promotion costs, investigate customer behavior and design a test. The read-only analyst points to evidence instead of inventing a lift number.',pill:'Evidence-backed guidance',icon:Sparkles}
];
const questions=[
 'How often are customers returning?',
 'What do our promotions cost?',
 'Which location has the most sales?'
];

function useReveal(){
 useEffect(()=>{
  const nodes=document.querySelectorAll<HTMLElement>('[data-reveal]');
  if(!('IntersectionObserver' in window)){nodes.forEach(n=>n.classList.add('is-visible'));return}
  const reduce=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  if(reduce){nodes.forEach(n=>n.classList.add('is-visible'));return}
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{
   if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target)}
  }),{rootMargin:'0px 0px -50px 0px',threshold:.08});
  nodes.forEach(n=>observer.observe(n));return()=>observer.disconnect();
 },[]);
}

function StoryFlow(){
 const [active,setActive]=useState(0),current=flow[active];
 const Icon=current.icon;
 return <div className="v7-flow-shell" data-reveal>
  <div className="v7-flow-index">
   {flow.map((s,i)=><button aria-pressed={active===i} onClick={()=>setActive(i)} className={'v7-flow-item '+(active===i?'selected':'')} key={s.n}>
    <span>{s.n}</span><strong>{s.title}</strong><ChevronRight size={18}/>
   </button>)}
  </div>
  <div className="v7-flow-stage" key={active}>
   <span className="v7-stage-kicker">{current.pill}</span>
   <div className="v7-stage-icon"><Icon size={30}/></div>
   <h3>{current.subtitle}</h3><p>{current.detail}</p>
   <div className="v7-stage-track"><div style={{width:`${(active+1)/flow.length*100}%`}}/></div>
   <div className="v7-stage-bottom"><span>{String(active+1).padStart(2,'0')} / 04</span><button onClick={()=>setActive((active+1)%flow.length)}>Next step <ArrowRight size={17}/></button></div>
  </div>
 </div>
}

function AskPreview(){
 const [question,setQuestion]=useState(questions[0]);
 const response=useMemo(()=>askWorkspace(question,summary),[question]);
 return <div className="v7-ask-demo" data-reveal>
  <div className="v7-ask-top"><div className="v7-ai-mark"><Sparkles size={22}/></div><span><b>TableSignal Analyst</b><small>Read-only • Verified sample evidence</small></span><span className="v7-sample-chip">SYNTHETIC</span></div>
  <div className="v7-ask-choice"><span>TRY A QUESTION</span>{questions.map(q=><button key={q} aria-pressed={question===q} className={question===q?'selected':''} onClick={()=>setQuestion(q)}>{q}<ArrowUpRight size={14}/></button>)}</div>
  <div className="v7-ask-answer" key={question} aria-live="polite"><span><CheckCircle2 size={15}/> Answer from calculated metrics</span><p>{response.answer}</p>
    <div className="v7-ask-evidence"><b>Evidence used</b><div>{response.evidence_keys.map((key:string)=><code key={key}>{key.replaceAll('_',' ')}</code>)}</div></div>
    <div className="v7-ask-next"><b>Next step</b><p>{response.recommended_next_step}</p></div>
  </div>
  <Link href="/workspace#analyst">Open the analyst <ArrowRight size={17}/></Link>
 </div>
}

export function LandingExperience(){
 useReveal();
 return <main className="v7-landing ts-home">
  <section className="v7-hero" id="top">
   <div className="v7-glow v7-glow-a"/><div className="v7-glow v7-glow-b"/>
   <div className="v7-hero-inner">
    <div className="v7-hero-copy" data-reveal>
     <div className="v7-brow"><span className="v7-brow-signal"/> RESTAURANT CUSTOMER & PROMOTION INTELLIGENCE</div>
     <h1>Know your guests.<br/><span>Grow with clarity.</span></h1>
     <p className="v7-hero-sub">See who returns, what your offers actually cost, and what to investigate next—together in one restaurant intelligence workspace.</p>
     <div className="v7-hero-cta"><Link className="v7-button-primary" href="/start">Explore the live demo <ArrowRight size={18}/></Link><Link className="v7-button-ghost" href="/pricing">See plans <ArrowUpRight size={17}/></Link></div>
     <div className="v7-hero-safe"><ShieldCheck size={17}/> Try it instantly using fictional data. No account required.</div>
     <div className="v7-hero-micro"><div className="v7-pulse-dots"><i/><i/><i/><i/></div><span>Sales intelligence</span><span className="v7-mini-dot">·</span><span>Guest behavior</span><span className="v7-mini-dot">·</span><span>AI-ready analysis</span></div>
    </div>
    <div className="v7-hero-product" data-reveal>
     <div className="v7-product-halo"/><div className="v7-motion-float v7-float-1"><Users size={17}/><span>Repeat guest visibility</span></div>
     <div className="v7-motion-float v7-float-2"><Sparkles size={16}/><span>Ask about your business</span></div>
     <MotionTour/>
    </div>
   </div>
   <a href="#the-opportunity" className="v7-scroll-cue">SCROLL TO EXPLORE <span>↓</span></a>
  </section>

  <div className="v7-marquee" aria-label="Platform capabilities"><div className="v7-marquee-track">{Array.from({length:2},(_,i)=><div key={i} className="v7-marquee-set" aria-hidden={i===1}><span>UNDERSTAND YOUR REGULARS</span><b>✦</b><span>EXPLAIN YOUR PROMOTIONS</span><b>✦</b><span>DISCOVER PATTERNS</span><b>✦</b><span>ASK BETTER QUESTIONS</span><b>✦</b></div>)}</div></div>

  <section className="v7-statement" id="the-opportunity"><div data-reveal><span className="v7-eyebrow">THE PROBLEM</span><h2>You know what you sold.<br/><em>But do you know what comes next?</em></h2><p>Traditional reports describe transactions. Understanding repeat behavior, promotional spending and unexplained differences takes more work. TableSignal brings those questions into a single, guided experience.</p></div><div className="v7-statement-decoration" aria-hidden="true"><span>ORDERS</span><span>GUESTS</span><span>PROMOTIONS</span><div><Sparkles size={30}/></div></div></section>

  <section className="v7-features" id="features">
   <div className="v7-section-intro" data-reveal><div><span className="v7-eyebrow">WHAT YOU GET</span><h2>A better view of your business.<br/>Not another wall of charts.</h2></div><p>Start with the questions that matter to an operator. Dig into the underlying evidence only when you need to.</p></div>
   <div className="v7-feature-grid">
    <article className="v7-feature v7-feature-large" data-reveal><div className="v7-feature-head"><span>01 / REVENUE</span><TrendingUp size={22}/></div><h3>See your business at a glance.</h3><p>One summary of net sales, orders, discounts and location performance—with consistent definitions.</p><div className="v7-feature-metrics"><div><small>Illustrative sample net sales</small><strong>{usd(summary.net_sales_minor)}</strong></div><div><small>Orders</small><strong>{summary.orders}</strong></div></div><div className="v7-feature-graph" aria-hidden="true">{[36,52,46,68,58,63,85,72,94,80,88,100].map((v,i)=><span key={i} style={{height:v+'%',animationDelay:i*.075+'s'}}/>)}</div></article>
    <article className="v7-feature v7-feature-guests" data-reveal><div className="v7-feature-head"><span>02 / GUESTS</span><Users size={22}/></div><h3>Learn who comes back.</h3><p>Analyze observed repeat purchasing for identifiable guests without treating anonymous orders as people.</p><div className="v7-guest-visual"><div className="v7-ring" style={{'--share':`${summary.identification_coverage_percent}%`} as CSSProperties}><span>{summary.identification_coverage_percent}%<small>orders identified</small></span></div><div><b>{summary.repeat_customers}</b><small>observed repeat guests</small></div></div></article>
    <article className="v7-feature v7-feature-campaign" data-reveal><div className="v7-feature-head"><span>03 / PROMOTIONS</span><TicketPercent size={22}/></div><h3>Understand what offers cost.</h3><p>Match coupon redemptions to orders. See observed discounts without claiming that attributed sales are incremental profit.</p><div className="v7-campaign-visual"><span><TicketPercent size={17}/> Campaign evidence</span><b>{campaigns.campaigns.reduce((s,c)=>s+c.redeemed_orders,0)} <small>matched redemptions</small></b><i><span/></i></div></article>
   </div>
  </section>

  <section className="v7-flow-section" id="how-it-works"><div className="v7-section-intro" data-reveal><div><span className="v7-eyebrow">FOUR SIMPLE STEPS</span><h2>From raw sales data<br/>to your next decision.</h2></div><p>No need to learn CSV schemas, table definitions or data pipelines to understand your restaurant.</p></div><StoryFlow/></section>

  <section className="v7-ai-section" id="analyst"><div className="v7-ai-copy" data-reveal><span className="v7-eyebrow">YOUR AI-READY BUSINESS ANALYST</span><h2>Ask the question<br/><span>behind the numbers.</span></h2><p>Want to know whether customers are coming back, where discounts are concentrated, or which location needs a closer look? Ask in plain language. TableSignal begins with verified calculations and shows the evidence.</p><div className="v7-ai-points"><span><Check size={18}/> Answers grounded in your available data</span><span><Check size={18}/> Clear explanation of unknowns</span><span><Check size={18}/> Actions to investigate—not made-up ROI</span></div><Link className="v7-button-ghost light" href="/workspace#analyst">Try questions with fictional data <ArrowRight size={17}/></Link><small>Free demo uses deterministic analysis. Optional model-backed explanations require a configured paid test account.</small></div><AskPreview/></section>

  <section className="v7-spotlight"><div className="v7-section-intro" data-reveal><div><span className="v7-eyebrow">PROACTIVE INSIGHTS</span><h2>Don't wait until you know<br/>which question to ask.</h2></div><p>Highlight patterns and the limits of the data before the restaurant owner goes searching for them.</p></div><div className="v7-signal-grid">{signals.slice(0,3).map((s,i)=><article className="v7-signal-card" data-reveal key={s.id}><div><span>INSIGHT 0{i+1}</span><Sparkles size={19}/></div><h3>{s.title}</h3><p>{s.detail}</p><small>{s.evidence_keys.map(x=>x.replaceAll('_',' ')).join(' · ')}</small></article>)}</div></section>

  <section className="v7-business-section"><div className="v7-business-inner"><div data-reveal><span className="v7-eyebrow">MADE FOR A REAL BUSINESS MODEL</span><h2>A workspace for every restaurant.<br/><span>A plan for every stage.</span></h2><p>Explore the example for free. When you’re ready, create an account for your restaurant profile and test the subscription experience. Real merchant data and live billing require a later secure launch.</p><div className="v7-business-ctas"><Link className="v7-button-primary" href="/sign-up">Create an account <ArrowRight size={17}/></Link><Link className="v7-button-ghost" href="/pricing">Review pricing <ArrowUpRight size={17}/></Link></div></div><div className="v7-business-steps" data-reveal><div><span>01</span><Store size={21}/><strong>Create an account</strong><small>Local email/password account</small></div><div><span>02</span><Database size={21}/><strong>Set up your restaurant</strong><small>Save goals and business profile</small></div><div><span>03</span><CreditCard size={21}/><strong>Manage your plan</strong><small>Stripe test checkout and billing portal</small></div></div></div></section>

  <section className="v7-faq-section" id="questions"><div data-reveal><span className="v7-eyebrow">QUESTIONS, ANSWERED</span><h2>See what works today.</h2><p>We’d rather be clear about what’s implemented than promise capabilities that aren't available yet.</p></div><div className="v7-faq-list" data-reveal><details><summary>Can I explore without creating an account?<span>+</span></summary><p>Yes. The entire public walkthrough uses fictional restaurant data and needs no login.</p></details><details><summary>Can I create an account and pay?<span>+</span></summary><p>Sign-up, sign-in, account password changes and a Stripe subscription test flow are implemented. Local accounts work without configuration; Stripe test checkout needs test credentials. Live charges remain disabled.</p></details><details><summary>Can I upload my real restaurant transactions?<span>+</span></summary><p>Not yet. The current public sandbox is for synthetic data only. Real merchant onboarding needs secured storage, tenant isolation, permissions, and a production security review.</p></details><details><summary>Is this AI or a normal chatbot?<span>+</span></summary><p>The demo uses a deterministic analytical engine tied to verified sample metrics. An optional language model can explain aggregated results for a configured account; it cannot invent profit lift or perform actions on your behalf.</p></details></div></section>

  <section className="v7-final"><div className="v7-final-orbit v7-orbit-1"/><div className="v7-final-orbit v7-orbit-2"/><div data-reveal><span className="v7-eyebrow">A BETTER QUESTION BEGINS HERE</span><h2>Know more about your restaurant.<br/><span>Guess less about what to do.</span></h2><p>Open the interactive sample workspace and see how the platform turns transaction records into evidence-backed insights.</p><div><Link className="v7-button-primary" href="/start">Explore the interactive demo <ArrowRight size={18}/></Link><Link className="v7-button-ghost light" href="/sign-up">Create an account <ArrowUpRight size={16}/></Link></div><small>TableSignal is a working-name prototype. Figures shown are synthetic. No verified merchant integrations or real payments.</small></div></section>
 </main>;
}
