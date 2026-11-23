'use client';
import {useEffect,useState} from 'react';
import {CalendarDays} from 'lucide-react';
import {accountApi} from '@/lib/local-auth';

export type BriefEvidence={this_week:number;baseline:number;change_percent:number;weekly_spread:number;z:number|null;
  orders_this_week:number;week_start:string;baseline_from:string};
export type BriefFinding={id:string;scope:string;location_id:string|null;metric:string;title:string;detail:string;
  confidence:'clear'|'possible';impact_minor:number;evidence:BriefEvidence};
export type WeeklyBriefData={week_start:string;week_end:string;headline:string;findings:BriefFinding[];caveats:string[];method:string;has_data:boolean};

/** The Monday brief, in the app: what changed last week, how sure we are, and the evidence. */
export function WeeklyBrief({token}:{token:string}){
 const [brief,setBrief]=useState<WeeklyBriefData|null>(null);
 const [error,setError]=useState('');
 useEffect(()=>{void accountApi('/api/briefs/latest',token).then(b=>setBrief(b as WeeklyBriefData)).catch(e=>setError(e instanceof Error?e.message:'Could not load the weekly brief.'))},[token]);
 if(error)return <div className="ts10-notice ts10-danger" role="alert">{error}</div>;
 if(!brief)return <div className="ts10-notice">Loading this week's brief…</div>;
 if(!brief.has_data)return null;
 return <section className="ts10-card" aria-labelledby="weekly-h" data-weekly-brief>
  <span className="ts10-eyebrow"><CalendarDays size={15}/> THIS WEEK · {brief.week_start} to {brief.week_end}</span>
  <h2 id="weekly-h">{brief.headline}</h2>
  {brief.findings.length===0&&<p>Nothing moved more than it normally does from week to week. That's useful to know too.</p>}
  <div style={{display:'grid',gap:12}}>{brief.findings.map(f=><article key={f.id} data-finding={f.id}>
   <h3 style={{margin:'0 0 4px'}}>{f.title} <span className={'ts9-pill '+(f.confidence==='clear'?'ok':'')}>{f.confidence==='clear'?'Clear change':'Possible change'}</span></h3>
   <p style={{margin:0}}>{f.detail}</p>
   <details><summary>Evidence</summary><p className="ts10-small">This week {f.evidence.this_week.toLocaleString('en-US')} · 4-week average {f.evidence.baseline.toLocaleString('en-US')} · change {f.evidence.change_percent}% · normal weekly spread ±{f.evidence.weekly_spread.toLocaleString('en-US')} · {f.evidence.orders_this_week} orders · baseline from {f.evidence.baseline_from}{f.metric.endsWith('sales')||f.metric==='average_order'||f.metric==='discount_spend'?' · amounts in cents':''}</p></details>
  </article>)}</div>
  {brief.caveats.map(c=><p key={c} className="ts10-small">{c}</p>)}
  <p className="ts10-small">{brief.method}</p>
 </section>;
}
