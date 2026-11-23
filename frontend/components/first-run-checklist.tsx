'use client';

import {useCallback,useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {ArrowRight,CheckCircle2,Circle,RefreshCw} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';

type Step={key:string;label:string;detail:string;href:string;done:boolean};
type Checklist={onboarded:boolean;steps:Step[];completed:number};
type SquareStatus={connected:boolean;connection_status:string|null;last_sync_at:string|null};
type SandboxLocations={enabled:boolean;selected_count:number};
type DataHealth={status:string;backfill:{complete:boolean}|null};
type Brief={has_data:boolean;data_status?:string};
type Plans={plans:{id:string}[]};

// A route or action can request a fresh snapshot; the server remains the source of truth.
export function notifyFirstRunProgressChanged(){
  if(typeof window!=='undefined')window.dispatchEvent(new Event('tablesignal:progress-changed'));
}

/** Show the next safe action on every signed-in app page until the first decision is saved. */
export function FirstRunChecklist(){
  const pathname=usePathname();
  const requestId=useRef(0);
  const [state,setState]=useState<Checklist|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');

  const refresh=useCallback(async()=>{
    const id=++requestId.current;
    setLoading(true);setError('');
    try{
      const session=await localAuthClient().auth.getSession();
      if(session.error)throw session.error;
      const token=session.data.session?.access_token;
      if(!token){if(id===requestId.current)setState(null);return;}
      const progress=await accountApi('/api/saas/onboarding',token) as {stage:number};
      if(progress.stage<3){
        if(id===requestId.current)setState({onboarded:false,steps:[],completed:0});
        return;
      }
      // A saved decision is the durable completion signal: do not reopen onboarding when data goes stale.
      const plans=await accountApi('/api/decisions/plans',token) as Plans;
      if((plans.plans||[]).length>0){
        if(id===requestId.current)setState({onboarded:true,steps:[],completed:5});
        return;
      }
      const connection=await accountApi('/api/integrations/square/status',token) as SquareStatus;
      const connected=connection.connected&&connection.connection_status==='active';
      let selected=false,synced=false,insight=false;
      let selectionUnavailable=false;
      if(connected){
        // These are independently truthful. Missing/failed requests never mark a step complete.
        const locations=await accountApi('/api/integrations/square/locations',token) as SandboxLocations;
        selected=locations.enabled?locations.selected_count>0:connected;
        selectionUnavailable=!locations.enabled;
        const health=await accountApi('/api/integrations/square/health',token) as DataHealth;
        synced=selected&&health.backfill?.complete===true&&Boolean(connection.last_sync_at);
        if(synced&&health.status==='healthy'){
          const brief=await accountApi('/api/briefs/latest',token) as Brief;
          insight=brief.data_status==='ready'&&brief.has_data;
        }
      }
      const steps:Step[]=[
        {key:'connect',label:'Connect Square',detail:'Authorize a Square Sandbox seller.',href:'/connections',done:connected},
        {key:'locations',label:'Choose locations',detail:selectionUnavailable
          ?'Location selection is managed automatically in this development environment.'
          :'Choose which eligible locations TableSignal monitors.',href:'/connections',done:selected},
        {key:'sync',label:'Finish first sync',detail:'Import history and verify data is current.',href:'/connections',done:synced},
        {key:'insight',label:'First weekly brief ready',detail:'Open a verified brief before acting on changes.',href:'/analyst',done:insight},
        {key:'decision',label:'Save your first decision',detail:'Choose a metric and follow-up date.',href:'/opportunities',done:false}
      ];
      if(id===requestId.current)setState({onboarded:true,steps,completed:steps.filter(s=>s.done).length});
    }catch(e){
      if(id===requestId.current)setError(e instanceof Error?e.message:'Unable to load your setup progress.');
    }finally{
      if(id===requestId.current)setLoading(false);
    }
  },[]);

  useEffect(()=>{void refresh();return()=>{requestId.current+=1;};},[pathname,refresh]);
  useEffect(()=>{
    const update=()=>{void refresh();};
    window.addEventListener('tablesignal:progress-changed',update);
    window.addEventListener('focus',update);
    return()=>{
      window.removeEventListener('tablesignal:progress-changed',update);
      window.removeEventListener('focus',update);
    };
  },[refresh]);

  if(loading&&!state)return null;
  if(error)return <aside className="ts-m6-setup" role="status" data-first-run-error>
    <p>We could not check your setup progress. No progress has been changed.</p>
    <button type="button" className="ts-m6-refresh" onClick={()=>void refresh()}>Retry</button>
  </aside>;
  if(!state||state.completed===5)return null;
  const next=state.onboarded?state.steps.find(s=>!s.done):null;
  const href=next?.href||'/onboarding';
  const description=state.onboarded?(next?.detail||'Your setup is almost complete.')
    :'Finish your restaurant profile and plan choice before connecting Square.';

  return <aside className="ts-m6-setup" aria-label="First-run setup checklist"
    data-first-run-checklist data-completed-steps={state.completed}>
    <div className="ts-m6-setup-top">
      <div className="ts-m6-setup-copy">
        <span className="ts-m6-eyebrow">YOUR RESTAURANT · GETTING STARTED</span>
        <strong>{state.onboarded?(next?.label||'Next step'):'Finish restaurant setup'}</strong>
        <p>{description}</p>
      </div>
      <div className="ts-m6-setup-controls">
        <span className="ts-m6-count" aria-live="polite">{state.completed} of 5 complete</span>
        <Link href={href} className="ts-m6-continue" aria-label={'Continue setup: '+(next?.label||'Restaurant profile')}>
          Continue setup <ArrowRight size={15} aria-hidden="true"/>
        </Link>
        <button type="button" className="ts-m6-refresh" aria-label="Refresh setup progress" onClick={()=>void refresh()}
          disabled={loading}><RefreshCw size={15} aria-hidden="true"/> <span className="ts-m6-sr-only">Refresh progress</span></button>
      </div>
    </div>
    <progress className="ts-m6-setup-progress" value={state.completed} max={5}
      aria-label="First-run setup steps completed"/>
    {state.onboarded&&<details className="ts-m6-setup-details">
      <summary>See all five steps</summary>
      <ol>{state.steps.map(s=><li key={s.key} className={s.done?'done':''}>
        {s.done?<CheckCircle2 size={16} aria-hidden="true"/>:<Circle size={16} aria-hidden="true"/>}
        <span><strong>{s.label}</strong><small>{s.detail}</small></span>
        <span className="ts-m6-step-status">{s.done?'Done':'Not yet'}</span>
      </li>)}</ol>
    </details>}
    <small className="ts-m6-dev-note">Square Sandbox only. No live restaurant connections or payments.</small>
  </aside>;
}
