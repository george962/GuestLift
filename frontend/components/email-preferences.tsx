'use client';
import {useEffect,useState} from 'react';
import {Mail} from 'lucide-react';
import {accountApi} from '@/lib/local-auth';

type Prefs={email:string|null;weekly_digest:boolean;outcome_emails:boolean;provider_configured:boolean};

export function EmailPreferences({token}:{token:string}){
 const [prefs,setPrefs]=useState<Prefs|null>(null);
 const [saved,setSaved]=useState('');
 useEffect(()=>{void accountApi('/api/team/me/email',token).then(p=>setPrefs(p as Prefs)).catch(()=>setPrefs(null))},[token]);
 if(!prefs)return null;
 async function save(next:Prefs){setPrefs(next);setSaved('');
  await accountApi('/api/team/me/email',token,'POST',{weekly_digest:next.weekly_digest,outcome_emails:next.outcome_emails});setSaved('Saved.')}
 return <section className="ts-settings-card" aria-labelledby="email-h">
  <div className="ts-section-icon"><Mail size={24}/></div><h2 id="email-h">Email</h2>
  <p className="ts-muted">{prefs.email?`Sent to ${prefs.email}.`:'We could not find a verified email address for your account.'}{!prefs.provider_configured&&' Email sending is not set up on this server yet; messages are recorded but not delivered.'}</p>
  <label><input type="checkbox" id="pref-weekly" checked={prefs.weekly_digest} onChange={e=>void save({...prefs,weekly_digest:e.target.checked})}/> Weekly brief every Monday morning</label>
  <label><input type="checkbox" id="pref-outcome" checked={prefs.outcome_emails} onChange={e=>void save({...prefs,outcome_emails:e.target.checked})}/> How a decision turned out, on its follow-up date (owners)</label>
  {saved&&<p className="ts-muted" role="status">{saved}</p>}
 </section>;
}
