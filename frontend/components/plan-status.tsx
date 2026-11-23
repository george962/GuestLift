'use client';
import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import {AlertTriangle,CalendarClock,CheckCircle2,Lock} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';

export type Entitlement={state:'setup'|'trial'|'trial_expired'|'active'|'canceling'|'past_due'|'read_only';
  access:'full'|'setup'|'read_only';until:string|null;days_left:number|null;message:string};

/** The workspace's plan state from the server (docs/PRODUCT_PLAN.md M5). */
export function usePlan(){
 const [plan,setPlan]=useState<Entitlement|null>(null);
 const load=useCallback(async()=>{
  try{const s=await localAuthClient().auth.getSession();const t=s.data.session?.access_token;
   if(!t){setPlan(null);return}
   const me=await accountApi('/api/saas/me',t);setPlan(me.workspace.entitlement as Entitlement);
  }catch{/* advisory */}
 },[]);
 useEffect(()=>{void load()},[load]);
 return {plan,reload:load};
}

/** Account-page banner: only when the owner needs to act soon. */
export function PlanBanner({plan}:{plan:Entitlement|null}){
 if(!plan)return null;
 const ending=plan.state==='trial'&&(plan.days_left??99)<=3;
 if(!(ending||plan.state==='past_due'||plan.access==='read_only'))return null;
 const urgent=plan.state==='past_due'||plan.access==='read_only';
 return <div className={'ts9-notice '+(urgent?'danger':'')} role="status" data-plan={plan.state}>
  {plan.access==='read_only'?<Lock size={17}/>:<AlertTriangle size={17}/>}<span>{plan.message}</span>
  <Link href="/billing" style={{fontWeight:700,marginLeft:8}}>{plan.state==='past_due'||plan.state==='read_only'?'Fix billing':'Choose a plan'}</Link>
 </div>;
}

const LABEL:Record<Entitlement['state'],string>={setup:'Not started',trial:'Free trial',trial_expired:'Trial ended',
 active:'Active',canceling:'Ending',past_due:'Payment failed',read_only:'Read-only'};

export function PlanStatusCard({plan}:{plan:Entitlement|null}){
 if(!plan)return null;
 const good=plan.access==='full'&&plan.state!=='past_due';
 return <section className="ts-settings-card" aria-labelledby="plan-h" data-plan={plan.state}>
  <div className="ts-section-icon">{good?<CheckCircle2 size={24}/>:plan.state==='setup'?<CalendarClock size={24}/>:<AlertTriangle size={24}/>}</div>
  <span className="ts-kicker">YOUR PLAN</span>
  <h2 id="plan-h">{LABEL[plan.state]}</h2>
  <p>{plan.message}</p>
  {plan.days_left!==null&&plan.until&&<p className="ts-muted">{plan.state==='trial'?'Trial ends':plan.state==='past_due'?'Grace period ends':plan.state==='canceling'?'Access ends':'Renews'} {new Date(plan.until).toLocaleDateString()} · {plan.days_left} {plan.days_left===1?'day':'days'} left</p>}
  {plan.access==='read_only'&&<p className="ts-muted">Your existing numbers stay visible. Syncing, the AI analyst and new decisions resume when billing is active.</p>}
 </section>;
}
