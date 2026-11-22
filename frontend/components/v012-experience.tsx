'use client';

import {useEffect, useState} from 'react';
import {
  ArrowRight, ArrowUpRight, BarChart3, Check, CheckCircle2, ChevronDown,
  ChevronRight, CircleHelp, CreditCard, Database, FileCheck2, GitBranch,
  LockKeyhole, Menu, MessageCircle, MousePointerClick, PlayCircle,
  RefreshCcw, SearchCheck, ShieldCheck, Sparkles, Store, TrendingUp,
  Users, X
} from 'lucide-react';
import {MotionTour} from '@/components/motion-tour';

type ConsoleView = 'review' | 'ask' | 'action';
type Question = {prompt:string;answer:string;evidence:string;next:string};
type Finding = {
  id:string; category:string;priority:string;title:string;summary:string;
  facts:string[];uncertainty:string;test:string;outcome:string;
};

const questions:Question[] = [
  {prompt:'Are we spending too much on discounts?',
    answer:'The sample shows $1,850 in Tuesday discounts. Order counts were similar on selected comparison Tuesdays. That warrants a closer look, not a conclusion that the promotion failed.',
    evidence:'Sample discount records · Tuesday orders · Comparison dates',
    next:'Check margin assumptions and test a limited change.'},
  {prompt:'Which guests stopped returning?',
    answer:'The observed return rate fell within the identifiable-guest cohort. We would check whether ID coverage changed before assuming guests were lost.',
    evidence:'Known-guest IDs · Repeat-visit windows · Identification coverage',
    next:'Verify matching and compare equivalent guest cohorts.'},
  {prompt:'What changed at the lunch rush?',
    answer:'Friday lunch sales at one sample location rose 12% against four comparison Fridays. Order mix and average check can help narrow the investigation.',
    evidence:'Location order totals · Daypart · Average order value',
    next:'Review the top-selling items and check whether the pattern repeats.'},
];

const findings:Finding[] = [
  {id:'discounts',category:'Promotions',priority:'Review first',
    title:'Is your Tuesday promotion worth the cost?',
    summary:'The sample restaurant recorded $1,850 in Tuesday discounts last month. Order counts were similar on several comparison dates.',
    facts:['$1,850 recorded discounts','Comparable Tuesday order counts','Offer redemptions matched to sample orders'],
    uncertainty:'Comparable sales do not prove the promotion was unnecessary. Guest mix, weather, holidays and other changes could explain the pattern.',
    test:'Run a small, approved promotion test with a suitable holdout or matched comparison.',
    outcome:'Compare net contribution and customer behavior. Report uncertainty if a causal effect cannot be measured.'},
  {id:'guests',category:'Guests',priority:'Investigate',
    title:'Why are fewer identifiable guests returning?',
    summary:'The sample location shows a lower observed 30-day return rate for guests with usable customer IDs.',
    facts:['Known-guest cohort comparison','Customer ID coverage checked','Observation windows aligned'],
    uncertainty:'Anonymous transactions cannot be assigned to individual guests. Changes in ID coverage may distort observed retention.',
    test:'Check channel mix, visit frequency, and known-guest coverage before making a re-engagement offer.',
    outcome:'Track eligible cohorts over the next period and distinguish changes in measurement from changes in behavior.'},
  {id:'locations',category:'Locations',priority:'Explore',
    title:'What changed at your strongest lunch location?',
    summary:'One sample location recorded a 12% increase in Friday lunch sales compared with four prior Fridays.',
    facts:['Friday lunch order totals','Average order value movement','Location and daypart comparison'],
    uncertainty:'The increase does not show whether marketing, staffing, pricing, or customer traffic caused the change.',
    test:'Review order mix and operating changes. Test one plausible factor instead of guessing.',
    outcome:'Monitor comparable Fridays and save what the operator decided to change.'}
];

const locations=[
  {id:'sq-01',name:'Downtown',tag:'Active · Storefront'},
  {id:'sq-02',name:'Marina',tag:'Active · Storefront'},
  {id:'sq-03',name:'Northside',tag:'Active · Storefront'},
  {id:'sq-04',name:'Midtown',tag:'Active · Storefront'},
  {id:'sq-05',name:'West End',tag:'Active · Storefront'},
  {id:'sq-06',name:'Airport',tag:'Active · Storefront'},
  {id:'sq-07',name:'Catering',tag:'Online/virtual · Eligibility review'}
];

const money=(amount:number)=>new Intl.NumberFormat('en-US',{
  style:'currency',currency:'USD',maximumFractionDigits:0
}).format(amount);

function Brand(){
  return <span className="ts12-brand"><span className="ts12-brandmark" aria-hidden="true"><span/><span/><span/><span/></span>table<span>signal</span><b>.</b></span>;
}

function HeroConsole(){
  const [view,setView]=useState<ConsoleView>('review');
  const [question,setQuestion]=useState(0);
  const selected=questions[question];

  return <div className="ts12-console" aria-label="Interactive fictional restaurant product preview">
    <div className="ts12-console-top">
      <div className="ts12-console-identity"><span className="ts12-console-symbol"><BarChart3 size={18}/></span><div><strong>Bluebird Kitchen</strong><small>Fictional restaurant group · 5 locations</small></div></div>
      <span className="ts12-preview-pill"><span className="ts12-led"/> SAMPLE DATA</span>
    </div>
    <div className="ts12-console-tabbar" role="tablist" aria-label="Explore TableSignal's workflow">
      <button role="tab" aria-selected={view==='review'} className={view==='review'?'active':''} onClick={()=>setView('review')}><SearchCheck size={16}/> Weekly review</button>
      <button role="tab" aria-selected={view==='ask'} className={view==='ask'?'active':''} onClick={()=>setView('ask')}><MessageCircle size={16}/> Ask the analyst</button>
      <button role="tab" aria-selected={view==='action'} className={view==='action'?'active':''} onClick={()=>setView('action')}><FileCheck2 size={16}/> Decision log</button>
    </div>
    <div className="ts12-console-body" key={view}>
      {view==='review'&&<div className="ts12-review">
        <div className="ts12-review-head"><div><span className="ts12-micro">YOUR WEEKLY BRIEF</span><h3>Here’s what needs a look.</h3></div><span className="ts12-review-date">Oct 26 – Nov 1</span></div>
        <div className="ts12-console-metrics">
          <div><small>Observed sales</small><strong>$142,400</strong><span><TrendingUp size={12}/> +4.2% vs prior week</span></div>
          <div><small>Identified repeat rate</small><strong>38%</strong><span>Known guests only</span></div>
          <div><small>Findings to review</small><strong>03</strong><span>Based on sample records</span></div>
        </div>
        <div className="ts12-console-chart"><div className="ts12-chart-top"><span>Sales by day</span><span>Sample illustration</span></div><div className="ts12-chart-bars" aria-label="Illustrative weekly sales bar chart">{[31,47,39,61,53,79,64,74,92,82,72,99].map((height,i)=><div className="ts12-chart-column" key={i}><span style={{height:`${height}%`,animationDelay:`${i*55}ms`}}/></div>)}</div><div className="ts12-chart-axis"><span>Monday</span><span>Sunday</span></div></div>
        <button className="ts12-alert-signal" onClick={()=>setView('ask')}><span className="ts12-alert-icon"><Sparkles size={19}/></span><span><small>QUESTION WORTH ASKING</small><strong>Tuesday discounts reached $1,850. Did they bring more orders?</strong><em>Explore the evidence <ArrowRight size={13}/></em></span><ChevronRight size={18}/></button>
      </div>}
      {view==='ask'&&<div className="ts12-analyst">
        <div className="ts12-analyst-head"><span className="ts12-console-symbol ts12-violet"><MessageCircle size={19}/></span><div><span className="ts12-micro">TABLESIGNAL ANALYST</span><h3>Ask about the numbers.</h3></div></div>
        <div className="ts12-question-picker"><span>Try a question</span>{questions.map((q,i)=><button key={q.prompt} className={question===i?'chosen':''} onClick={()=>setQuestion(i)} aria-pressed={question===i}>{q.prompt}<ArrowUpRight size={13}/></button>)}</div>
        <div className="ts12-answer" key={question}><span className="ts12-answer-author"><Sparkles size={16}/> Example answer</span><p>{selected.answer}</p><div className="ts12-answer-source"><Database size={15}/><span><b>Evidence:</b> {selected.evidence}</span></div><div className="ts12-answer-next"><strong>What to do next</strong><p>{selected.next}</p></div></div>
        <p className="ts12-smallprint">Scripted demonstration from fictional data; not a live model response.</p>
      </div>}
      {view==='action'&&<div className="ts12-decision">
        <span className="ts12-micro">SAVED DECISION · SAMPLE</span><h3>Don’t lose the reasoning.</h3><p>A useful answer is the start. TableSignal is designed to preserve what you decided and how you’ll measure it.</p>
        <div className="ts12-decision-timeline"><div><span className="ts12-timeline-dot done"><Check size={13}/></span><span><b>Finding investigated</b><small>$1,850 Tuesday discount spending examined</small></span><span className="ts12-tag-dark">Reviewed</span></div><div><span className="ts12-timeline-dot done"><Check size={13}/></span><span><b>Test defined</b><small>Compare an approved offer adjustment against a control</small></span><span className="ts12-tag-dark">Planned</span></div><div><span className="ts12-timeline-dot upcoming"/><span><b>Outcome check</b><small>Margin and repeat visits · awaiting comparable data</small></span><span className="ts12-tag-pending">Pending</span></div></div>
        <div className="ts12-decision-bottom"><ShieldCheck size={17}/><span>No automatic campaign execution. Operators review and approve decisions.</span></div>
      </div>}
    </div>
    <div className="ts12-console-footer"><span><span className="ts12-led"/> Interactive walkthrough · sample only</span><a href="/workspace">Open full sample workspace <ArrowUpRight size={15}/></a></div>
  </div>;
}

function useEntryMotion(){
  useEffect(()=>{
    const nodes=Array.from(document.querySelectorAll<HTMLElement>('.ts12 [data-reveal]'));
    const reduce=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if(reduce||!('IntersectionObserver' in window))return;
    const observer=new IntersectionObserver(entries=>{
      for(const entry of entries){
        if(entry.isIntersecting){entry.target.classList.add('ts12-inview');observer.unobserve(entry.target)}
      }
    },{threshold:0.12,rootMargin:'0px 0px -35px 0px'});
    nodes.forEach(node=>observer.observe(node));
    return ()=>observer.disconnect();
  },[]);
}

export default function V012Experience(){
  useEntryMotion();
  const [active,setActive]=useState('discounts');
  const [selected,setSelected]=useState<string[]>(['sq-01','sq-02','sq-03']);
  const [mobileMenu,setMobileMenu]=useState(false);
  const [expanded,setExpanded]=useState<number|null>(null);
  const [showSources,setShowSources]=useState(false);
  const finding=findings.find(item=>item.id===active)!;
  const toggleLocation=(id:string)=>{
    if(id==='sq-07')return;
    setSelected(old=>old.includes(id)?old.filter(item=>item!==id):[...old,id]);
  };
  const closeMenu=()=>setMobileMenu(false);

  return <main className="ts12">
    <div className="ts12-preview-notice"><span className="ts12-led"/> DEVELOPER PREVIEW <span aria-hidden="true">·</span> Production connections and billing are not enabled <span aria-hidden="true">·</span> Square Sandbox and Stripe test mode are available</div>
    <header className="ts12-nav">
      <div className="ts12-nav-inner"><a href="#top" aria-label="TableSignal home" onClick={closeMenu}><Brand/></a>
        <nav className={mobileMenu?'ts12-navlinks show':'ts12-navlinks'} aria-label="Main navigation">
          <a href="#product" onClick={closeMenu}>Product</a><a href="#experience" onClick={closeMenu}>See it work</a><a href="#how-it-works" onClick={closeMenu}>How it works</a><a href="#pricing" onClick={closeMenu}>Pricing</a>
          <a className="ts12-mobile-only" href="/connections" onClick={closeMenu}>Connect data</a><a className="ts12-mobile-only" href="/analyst" onClick={closeMenu}>AI Analyst</a><a className="ts12-mobile-only" href="/billing" onClick={closeMenu}>Billing (test)</a><a className="ts12-mobile-only" href="/sign-in" onClick={closeMenu}>Sign in</a>
        </nav>
        <div className="ts12-header-actions"><a className="ts12-signin" href="/sign-in">Sign in</a><a className="ts12-navcta" href="/sign-up">Create account <ArrowUpRight size={16}/></a></div>
        <button type="button" className="ts12-mobile" aria-label={mobileMenu?'Close navigation':'Open navigation'} aria-expanded={mobileMenu} onClick={()=>setMobileMenu(!mobileMenu)}>{mobileMenu?<X size={23}/>:<Menu size={23}/>}</button>
      </div>
    </header>

    <section className="ts12-hero" id="top">
      <div className="ts12-hero-grid" aria-hidden="true"/><div className="ts12-hero-orb ts12-orb-one" aria-hidden="true"/><div className="ts12-hero-orb ts12-orb-two" aria-hidden="true"/>
      <div className="ts12-wrap ts12-hero-inner">
        <div className="ts12-hero-copy">
          <span className="ts12-eyebrow"><span className="ts12-led"/> RESTAURANT DECISION INTELLIGENCE</span>
          <h1>Your sales data<br/>has answers.<br/><em>Find your next move.</em></h1>
          <p className="ts12-hero-lead">Connect restaurant sales, guest, and promotion data. Spot what changed, ask why, and track what you decide to do about it—all in one place.</p>
          <div className="ts12-hero-actions"><a className="ts12-btn ts12-btn-primary" href="#experience">See a real example <ArrowRight size={18}/></a><a className="ts12-btn ts12-btn-secondary" href="/workspace"><PlayCircle size={18}/> Try the sample workspace</a></div>
          <p className="ts12-hero-trust"><ShieldCheck size={17}/> Explore a fictional business without an account. No live customer data.</p>
          <div className="ts12-hero-foot"><span><span className="ts12-hero-check"><Check size={13}/></span> Understand sales</span><span><span className="ts12-hero-check"><Check size={13}/></span> Ask the AI Analyst</span><span><span className="ts12-hero-check"><Check size={13}/></span> Track decisions</span></div>
        </div>
        <div className="ts12-hero-product" data-reveal><div className="ts12-floating-note ts12-float-top"><span className="ts12-pulse-mini"/> YOUR WEEKLY BRIEF IS READY</div><HeroConsole/><div className="ts12-floating-note ts12-float-bottom"><GitBranch size={15}/> From numbers to next steps</div></div>
      </div>
      <div className="ts12-hero-bottom"><div className="ts12-wrap"><span>BUILT AROUND YOUR WORKDAY</span><span>CONNECT <i/> INVESTIGATE <i/> DECIDE <i/> TRACK</span><a href="#product">What you get <ChevronDown size={16}/></a></div></div>
    </section>

    <section className="ts12-product ts12-section ts12-wrap" id="product">
      <div className="ts12-section-head" data-reveal><div><span className="ts12-kicker">THE PRODUCT, NOT JUST A DASHBOARD</span><h2>Three things you can actually do.</h2></div><p>Your data is already sitting in different systems. TableSignal is being built to turn it into a weekly decision workflow—not another set of reports to check.</p></div>
      <div className="ts12-feature-grid">
        <article className="ts12-feature-card ts12-feature-dark" data-reveal><div className="ts12-feature-top"><span>01 · BRING IT TOGETHER</span><Database size={24}/></div><div className="ts12-feature-art ts12-connect-art" aria-hidden="true"><span><Store size={17}/> POS orders</span><span><Users size={17}/> Guests</span><span><CreditCard size={17}/> Discounts</span><div className="ts12-connector-node"><span className="ts12-led"/> One view</div></div><h3>Stop jumping between tools.</h3><p>Bring orders, discounts, guests and locations into a consistent picture, with missing information called out.</p><a href="/connections">Connect data <ArrowUpRight size={17}/></a><small>Current connection: Square Sandbox for testing</small></article>
        <article className="ts12-feature-card ts12-feature-green" data-reveal><div className="ts12-feature-top"><span>02 · INVESTIGATE</span><MessageCircle size={24}/></div><div className="ts12-feature-art ts12-chat-art" aria-hidden="true"><div><span>Owner</span><b>Did our promotion actually help?</b></div><div><Sparkles size={15}/><b>Discount spend is known. Incremental lift needs a fair comparison.</b></div></div><h3>Ask better questions.</h3><p>Go from a finding to its supporting numbers. See where evidence ends instead of getting a confident guess.</p><a href="/analyst">AI Analyst <ArrowUpRight size={17}/></a><small>Sample answers here; account features depend on setup</small></article>
        <article className="ts12-feature-card ts12-feature-light" data-reveal><div className="ts12-feature-top"><span>03 · FOLLOW THROUGH</span><FileCheck2 size={24}/></div><div className="ts12-feature-art ts12-decide-art" aria-hidden="true"><div><span><Check size={14}/></span><b>Investigate offer costs</b><small>Reviewed</small></div><div><span><Check size={14}/></span><b>Plan a controlled test</b><small>Planned</small></div><div><span className="ts12-wait-icon"/><b>Review what changed</b><small>Upcoming</small></div></div><h3>Remember what you decided.</h3><p>Save a plan, define what success looks like, and revisit the result when new data arrives.</p><a href="/experiments">Decision tracker <ArrowUpRight size={17}/></a><small>Operator-approved actions, not automatic campaigns</small></article>
      </div>
    </section>

    <section className="ts12-experience-section ts12-section" id="experience"><div className="ts12-wrap">
      <div className="ts12-section-head" data-reveal><div><span className="ts12-kicker">TRY AN INVESTIGATION</span><h2>A useful question beats another chart.</h2></div><p>Here’s what we’d look at first in a fictional five-location restaurant. Choose a finding and trace the evidence behind it.</p></div>
      <div className="ts12-experience">
        <aside className="ts12-findings" aria-label="Sample business findings"><div className="ts12-findings-heading"><span><span className="ts12-led"/> SAMPLE MONDAY REVIEW</span><strong>3 findings</strong></div>{findings.map((item,i)=><button type="button" key={item.id} className={active===item.id?'ts12-finding active':'ts12-finding'} onClick={()=>{setActive(item.id);setShowSources(false)}} aria-pressed={active===item.id}><span className="ts12-finding-meta">0{i+1} · {item.category}</span><strong>{item.title}</strong><span className="ts12-finding-bottom"><span>{item.priority}</span><ArrowUpRight size={17}/></span></button>)}<p><ShieldCheck size={16}/> Fictional records. No restaurant connected here.</p></aside>
        <article className="ts12-investigation" aria-live="polite"><div className="ts12-investigation-header"><span><SearchCheck size={17}/> EVIDENCE REVIEW</span><span className="ts12-pill-muted">SAMPLE ONLY</span></div><h3>{finding.title}</h3><p className="ts12-investigation-summary">{finding.summary}</p><div className="ts12-evidence-grid"><div className="ts12-evidence-panel"><strong><Database size={17}/> What the data shows</strong>{finding.facts.map(fact=><span key={fact}><CheckCircle2 size={16}/>{fact}</span>)}</div><div className="ts12-unknown-panel"><strong><CircleHelp size={17}/> What we don’t know</strong><p>{finding.uncertainty}</p></div></div><div className="ts12-recommend"><div><span><Sparkles size={16}/> SUGGESTED NEXT STEP</span><strong>{finding.test}</strong><p>{finding.outcome}</p></div><ArrowUpRight size={19}/></div><button className="ts12-source-toggle" onClick={()=>setShowSources(!showSources)} aria-expanded={showSources}>{showSources?'Hide evidence requirements':'What would this use in a real restaurant?'} <ChevronDown size={15}/></button>{showSources&&<p className="ts12-source-description">A live investigation would require permissioned POS order and discount records, reliable locations and dates, relevant guest identifiers, and sometimes campaign assignments and costs. Missing data would be flagged, not invented.</p>}</article>
      </div>
    </div></section>

    <section className="ts12-motion-section ts12-section" id="demo"><div className="ts12-wrap ts12-motion-layout"><div className="ts12-motion-copy" data-reveal><span className="ts12-kicker">TAKE A LOOK INSIDE</span><h2>Not a slide deck.<br/><em>Something you can explore.</em></h2><p>Watch sales, guest, and promotion views change, or take control of the walkthrough yourself. Every number is labeled as sample data.</p><div className="ts12-motion-list"><span><CheckCircle2 size={18}/> Three interactive product views</span><span><CheckCircle2 size={18}/> Play, pause, or pick a screen</span><span><CheckCircle2 size={18}/> A complete sample workspace behind it</span></div><a className="ts12-btn ts12-btn-ink" href="/workspace">Open interactive demo <ArrowUpRight size={17}/></a></div><div className="ts12-motion-stage" data-reveal><div className="ts12-motion-label"><span className="ts12-led"/> WORKING SAMPLE WALKTHROUGH</div><MotionTour/></div></div></section>

    <section className="ts12-workflow ts12-section" id="how-it-works"><div className="ts12-wrap"><div className="ts12-section-head ts12-section-head-light" data-reveal><div><span className="ts12-kicker">FROM DATA TO DECISION</span><h2>Less dashboard time.<br/>More informed action.</h2></div><p>Each step is connected. You can follow a question from its original numbers through to a documented decision and later review.</p></div><div className="ts12-workflow-list">{[
      {n:'01',icon:Database,title:'Connect',subtitle:'Orders, guests, and offers',detail:'Start with an authorized source. Check that records and definitions are usable.'},
      {n:'02',icon:BarChart3,title:'Spot the change',subtitle:'A focused weekly brief',detail:'Prioritize patterns instead of leaving every owner to hunt through reports.'},
      {n:'03',icon:MessageCircle,title:'Ask why',subtitle:'An evidence trail, not a guess',detail:'Inspect the numbers and see when the data cannot support an answer.'},
      {n:'04',icon:MousePointerClick,title:'Make the call',subtitle:'A saved plan and success metric',detail:'Choose a measured next step with an owner and an approval path.'},
      {n:'05',icon:RefreshCcw,title:'Check the result',subtitle:'Follow-up, not a forgotten task',detail:'Compare subsequent observations and record what happened.'}
    ].map(step=><article className="ts12-workflow-item" key={step.n} data-reveal><span className="ts12-workflow-number">{step.n}</span><span className="ts12-workflow-icon"><step.icon size={23}/></span><div><h3>{step.title}</h3><b>{step.subtitle}</b><p>{step.detail}</p></div><ArrowRight size={20} className="ts12-workflow-arrow"/></article>)}</div><p className="ts12-workflow-note"><LockKeyhole size={17}/> The production version requires secure integrations and validated data. This preview never connects to live merchants or executes campaigns.</p></div></section>

    <section className="ts12-pricing-section ts12-section ts12-wrap" id="pricing"><div className="ts12-section-head" data-reveal><div><span className="ts12-kicker">LOCATION-BASED PRICING</span><h2>Know what you’ll pay.<br/>Before you commit.</h2></div><p>The proposed price is based on eligible locations you choose to monitor—not the number you type into a form. Try the example below.</p></div><div className="ts12-price-grid"><article className="ts12-price-plan"><span className="ts12-price-eyebrow">PROPOSED GROWTH PLAN · NOT ON SALE YET</span><div className="ts12-price-figure"><strong>$99</strong><span>/ monitored location<br/>per month</span></div><p>Restaurant intelligence in one place, rather than a tier for each report.</p><div className="ts12-price-features">{['Connected sales and known-guest patterns','Promotion and discount cost reviews','AI-assisted, evidence-linked investigations','Saved decisions and follow-up plans','Data quality and source health checks'].map(f=><span key={f}><CheckCircle2 size={18}/>{f}</span>)}</div><div className="ts12-price-links"><a href="/pricing">See plan details <ArrowUpRight size={16}/></a><a href="/billing">Billing (test) <ArrowUpRight size={16}/></a></div><small>Illustrative commercial pricing. Stripe test checkout uses its own configured test price. No live payments.</small></article><article className="ts12-location-card"><div className="ts12-location-head"><div><span className="ts12-kicker">INTERACTIVE PRICING EXAMPLE</span><h3>Pick the locations to monitor.</h3><p>Imagine Square reports seven locations, with one requiring eligibility review.</p></div><span className="ts12-source-chip"><Store size={14}/> Sample Square</span></div><div className="ts12-location-list">{locations.map(loc=><label key={loc.id} className={'ts12-location'+(loc.id==='sq-07'?' disabled':selected.includes(loc.id)?' selected':'')}><input type="checkbox" checked={selected.includes(loc.id)} disabled={loc.id==='sq-07'} onChange={()=>toggleLocation(loc.id)}/><span className="ts12-custom-check">{selected.includes(loc.id)?<Check size={13}/>:null}</span><span className="ts12-location-name"><b>{loc.name}</b><small>{loc.tag}</small></span><span className="ts12-location-state">{loc.id==='sq-07'?'Review needed':selected.includes(loc.id)?'Monitor':'Not billed'}</span></label>)}</div><div className="ts12-billing-summary"><div><span>Detected locations</span><b>7</b></div><div><span>Eligible in this example</span><b>6</b></div><div><span>Selected for monitoring</span><b>{selected.length}</b></div><div className="ts12-billing-total"><span>Illustrative monthly total</span><strong>{money(selected.length*99)}<small> / mo</small></strong></div></div><p className="ts12-billing-caption">Only selected, verified locations would count. This simulator does not save selections or charge anyone.</p></article></div></section>

    <section className="ts12-start-section ts12-section" id="start"><div className="ts12-wrap ts12-start-inner"><div><span className="ts12-kicker">THE DEVELOPER PREVIEW IS READY</span><h2>See the sample.<br/>Then try the workspace.</h2><p>Create a local account, set up a restaurant, and test the Square Sandbox and Stripe flows. You don’t need to hand over real restaurant data.</p><div className="ts12-start-actions"><a href="/sign-up" className="ts12-btn ts12-btn-primary">Create account <ArrowRight size={18}/></a><a href="/sign-in" className="ts12-btn ts12-btn-outline">Sign in</a></div><div className="ts12-direct-links"><a href="/connections">Connect data <ArrowUpRight size={15}/></a><a href="/analyst">AI Analyst <ArrowUpRight size={15}/></a><a href="/billing">Test checkout & billing <ArrowUpRight size={15}/></a></div></div><div className="ts12-onboarding-card"><span>WHAT HAPPENS NEXT</span>{[{n:'01',text:'Create your account',detail:'Local email and password'},{n:'02',text:'Set up your restaurant',detail:'Save a workspace profile'},{n:'03',text:'Connect a test source',detail:'Square Sandbox, if configured'},{n:'04',text:'Explore and investigate',detail:'Demo or account-scoped data'},{n:'05',text:'Try the billing flow',detail:'Stripe test mode only'}].map(item=><div key={item.n}><b>{item.n}</b><span><strong>{item.text}</strong><small>{item.detail}</small></span><CheckCircle2 size={17}/></div>)}</div></div></section>

    <section className="ts12-faq-section ts12-section ts12-wrap" id="faq"><div className="ts12-section-head" data-reveal><div><span className="ts12-kicker">GOOD QUESTIONS</span><h2>What’s real today?</h2></div><p>A good restaurant system should make its limitations just as clear as its capabilities.</p></div>{[
      {q:'Can I connect a live Square or Toast restaurant?',a:'Not in this preview. The existing Square integration is for Sandbox testing. Production OAuth, security controls and reconciliation must be verified before real merchant onboarding. Toast production access is not enabled.'},
      {q:'Is the analyst actually using AI?',a:'The public sample uses scripted, evidence-aware examples. The private analyst has optional model-assisted functionality when configured, and uses account-scoped metrics. Neither mode should invent causal conclusions.'},
      {q:'Can I pay for the $99-per-location plan now?',a:'No. The $99 rate and location selector are illustrative. Stripe test checkout is available with appropriate developer configuration, but production billing is disabled.'},
      {q:'Will this automatically run marketing campaigns?',a:'No. TableSignal helps investigate results, plan an action, and review outcomes. Campaign execution is not available and would require separate authorized integrations and approval.'}
    ].map((item,i)=><div className="ts12-faq-item" key={item.q}><button type="button" aria-expanded={expanded===i} onClick={()=>setExpanded(expanded===i?null:i)}><span>{item.q}</span><span>{expanded===i?'−':'+'}</span></button>{expanded===i&&<p>{item.a}</p>}</div>)}</section>

    <footer className="ts12-footer"><div className="ts12-wrap ts12-footer-inner"><div><Brand/><p>From what happened to what you do next.</p><small>Developer preview · Fictional data · Square Sandbox · Stripe test mode. No live merchant access or real charges.</small></div><nav aria-label="Footer navigation"><a href="/workspace">Sample workspace</a><a href="/sign-in">Sign in</a><a href="/sign-up">Create account</a><a href="/connections">Connect data</a><a href="/analyst">AI Analyst</a><a href="/billing">Billing (test)</a><a href="/pricing">Pricing</a></nav></div></footer>
  </main>;
}
