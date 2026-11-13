'use client';

import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,BookOpen,BrainCircuit,CheckCircle2,Database,GitBranch,LockKeyhole,MessageCircle,RefreshCw,Send,ShieldCheck,Sparkles,TriangleAlert} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';

type Node={id:string;label:string;value:string;unit:string;detail:string};
type Edge={from:string;to:string;label:string};
type Finding={id:string;severity:string;title:string;detail:string;evidence_ids:string[];next_path:string};
type Brief={environment:string;data_connected:boolean;orders_available:boolean;last_sync_at:string|null;subscription_active:boolean;model_configured:boolean;ai_ready:boolean;nodes:Node[];edges:Edge[];findings:Finding[];suggested_questions:string[];limitations:string[]};
type Reply={answer:string;engine:string;disclaimer:string;source:string};
type Turn={role:'user'|'assistant';content:string};

export default function Analyst(){
 const [token,setToken]=useState('');
 const [brief,setBrief]=useState<Brief|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState('');
 const [question,setQuestion]=useState('');
 const [history,setHistory]=useState<Turn[]>([]);
 const [busy,setBusy]=useState(false);
 const [selected,setSelected]=useState('identity');
 const reload=useCallback(async()=>{
  setLoading(true);setError('');
  try{
   const {data,error:sessionError}=await localAuthClient().auth.getSession();
   if(sessionError)throw sessionError;
   const t=data.session?.access_token||'';setToken(t);
   if(t){const result=await accountApi('/api/intelligence/brief',t) as Brief;
    setBrief(result);setQuestion(v=>v||result.suggested_questions[0]);}
   else setBrief(null);
  }catch(e){setError(e instanceof Error?e.message:'Could not load your analyst.');}
  finally{setLoading(false)}
 },[]);
 useEffect(()=>{void reload()},[reload]);
 async function ask(q=question){
  if(!brief?.ai_ready||!token||busy||q.trim().length<3)return;
  const prompt=q.trim();setQuestion('');setBusy(true);setError('');
  try{
   const result=await accountApi('/api/intelligence/ask',token,'POST',{
    question:prompt,
    history:history.slice(-6)
   }) as Reply;
   setHistory(prev=>[...prev,{role:'user' as const,content:prompt},{role:'assistant' as const,content:result.answer}].slice(-16));
  }catch(e){setQuestion(prompt);setError(e instanceof Error?e.message:'The model is unavailable.');}
  finally{setBusy(false)}
 }
 const node=brief?.nodes.find(x=>x.id===selected);
 return <main className="ts10-app ts11-analyst">
  <header className="ts10-heading"><span className="ts9-kicker">YOUR RESTAURANT · EVIDENCE INTELLIGENCE</span>
   <h1>Connect the dots. Then decide.</h1>
   <p>Explore relationships between purchases, guest recognition, repeat behavior, and discount costs. Ask an AI analyst to explain what the evidence supports—and what it doesn't.</p>
  </header>
  {loading&&<div className="ts10-notice">Checking your restaurant's verified evidence…</div>}
  {error&&<div className="ts10-notice ts10-danger" role="alert"><TriangleAlert size={18}/>{error}<button onClick={()=>void reload()}>Reload evidence</button></div>}
  {!loading&&!token&&<div className="ts10-card ts11-gate"><LockKeyhole size={28}/><h2>Sign in to your restaurant</h2><p>AI answers are tied to your authenticated workspace, never to another restaurant.</p><Link className="ts10-primary" href="/sign-in?next=%2Fanalyst">Sign in <ArrowRight size={16}/></Link></div>}
  {brief&&<>
   <div className="ts11-status"><span><Database size={15}/>{brief.data_connected?'Square Sandbox connected':'No source connected'}</span><span><ShieldCheck size={15}/>Account-scoped aggregates only</span><span><BrainCircuit size={15}/>{brief.model_configured?'LLM configured':'LLM setup pending'}</span>
    <button type="button" onClick={()=>void reload()}><RefreshCw size={15}/> Refresh evidence</button>
   </div>
   {!brief.data_connected&&<div className="ts10-card ts11-gate"><Database size={27}/><h2>First, connect and synchronize orders</h2><p>This private workspace deliberately starts empty. We won't show invented guest behavior or use a different restaurant's transactions.</p><Link href="/connections" className="ts10-primary">Connect data <ArrowRight size={15}/></Link><Link href="/workspace" className="ts10-secondary">Explore the fictional demo</Link></div>}
   {brief.data_connected&&<>
    <div className="ts11-section-heading"><div><span className="ts9-kicker">EVIDENCE GRAPH</span><h2>How your restaurant's metrics relate</h2><p>Select a metric to see its definition and connections. Every link is defined by the server, not invented by AI.</p></div><GitBranch size={26}/></div>
    <div className="ts11-graph-layout">
     <div className="ts11-evidence-nodes">{brief.nodes.map((n)=><button type="button" className={'ts11-node '+(selected===n.id?'selected':'')} key={n.id} onClick={()=>setSelected(n.id)}><span>{n.label}</span><strong>{n.value}</strong><small>{n.unit}</small></button>)}</div>
     <aside className="ts10-card ts11-evidence-detail"><span className="ts9-kicker">VERIFIABLE MEASURE</span><h3>{node?.label}</h3><p>{node?.detail}</p><div className="ts11-relationships"><strong>Relationships</strong>{brief.edges.filter(e=>e.from===selected||e.to===selected).map(e=><p key={e.from+e.to}><span>{brief.nodes.find(n=>n.id===e.from)?.label}</span> <b>{e.label}</b> <span>{brief.nodes.find(n=>n.id===e.to)?.label}</span></p>)}</div></aside>
    </div>
    <div className="ts11-section-heading"><div><span className="ts9-kicker">SIGNALS WORTH INVESTIGATING</span><h2>What these numbers suggest</h2></div></div>
    <div className="ts11-findings">{brief.findings.map(f=><article className="ts10-card" key={f.id}><div className="ts11-finding-kicker"><Sparkles size={16}/> {f.severity==='attention'?'DATA QUALITY OPPORTUNITY':'OBSERVED PATTERN'}</div><h3>{f.title}</h3><p>{f.detail}</p><small>Evidence: {f.evidence_ids.join(' · ')}</small><Link href={f.next_path}>Explore next step <ArrowRight size={15}/></Link></article>)}</div>
   </>}
   <section className="ts10-card ts11-conversation" aria-label="Ask the TableSignal AI analyst">
    <div className="ts11-chat-heading"><div><span className="ts9-kicker">AI ANALYST · READ ONLY</span><h2><MessageCircle size={24}/> Ask about your business</h2><p>Real model responses use verified, account-scoped aggregates. Raw guest records are not included automatically. Do not enter personal data into your questions. The AI cannot send offers or change records.</p></div><BrainCircuit size={32}/></div>
    {!brief.subscription_active&&<div className="ts10-notice"><LockKeyhole size={17}/>Account AI is included with Growth. Your current Sandbox plan includes evidence cards without model chat. <Link href="/billing">Review test billing</Link></div>}
    {brief.subscription_active&&!brief.model_configured&&<div className="ts10-notice"><TriangleAlert size={17}/>Your Growth subscription is active. The site owner must enable the server-side LLM configuration before live AI answers work. No model responses will be simulated.</div>}
    {brief.subscription_active&&brief.model_configured&&!brief.orders_available&&<div className="ts10-notice">Connect and synchronize orders to unlock grounded AI responses.</div>}
    <div className="ts11-question-chips">{brief.suggested_questions.map(q=><button type="button" key={q} onClick={()=>setQuestion(q)}>{q}</button>)}</div>
    <div className="ts11-chat-log" aria-live="polite">{history.length===0?<div className="ts11-chat-empty"><BookOpen size={24}/><strong>Start with a question above</strong><p>You'll get an explanation grounded in the metrics shown on this page, plus practical next steps.</p></div>:history.map((m,i)=><div key={i} className={'ts11-message '+m.role}><strong>{m.role==='assistant'?'TableSignal analyst':'You'}</strong><p>{m.content}</p></div>)}{busy&&<p className="ts11-typing">Analyzing verified evidence…</p>}</div>
    <form className="ts11-question-form" onSubmit={e=>{e.preventDefault();void ask()}}><label htmlFor="ts11-question">Your question</label><div><input id="ts11-question" value={question} onChange={e=>setQuestion(e.target.value)} maxLength={500} placeholder="What should I investigate before offering a discount?"/><button type="submit" disabled={!brief.ai_ready||busy||question.trim().length<3}><Send size={17}/>{busy?'Analyzing…':'Ask analyst'}</button></div></form>
    <p className="ts11-privacy"><ShieldCheck size={15}/>Model requests include verified aggregates plus questions you type, with response storage disabled. Do not paste guest information. Answers may still be imperfect. Do not treat them as verified causal impact.</p>
   </section>
   <div className="ts11-action-rail"><div><CheckCircle2 size={19}/><strong>Turn an answer into a decision.</strong><span>Compare the cost of possible incentives and save an experiment you can revisit.</span></div><Link href="/opportunities" className="ts10-primary">Plan an experiment <ArrowRight size={16}/></Link></div>
  </>}
 </main>
}
