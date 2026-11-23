'use client';
import {useCallback,useEffect,useState} from 'react';
import {Copy,Trash2,UserPlus,Users} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';
import {authMode} from '@/lib/auth-mode';
import {deleteClerkUser} from '@/lib/clerk-auth';

type Member={id:string;role:string;email:string;is_me:boolean;joined_at:string};
type Invite={id:string;email:string;role:string;created_at:string;expires_at:number};
type Team={workspace_name:string;my_role:'owner'|'manager';members:Member[];pending_invites:Invite[]};

/** Team members, invites and workspace deletion (docs/PRODUCT_PLAN.md M2). */
export function TeamSettings({token}:{token:string}){
 const [team,setTeam]=useState<Team|null>(null);
 const [email,setEmail]=useState('');
 const [link,setLink]=useState('');
 const [confirm,setConfirm]=useState('');
 const [message,setMessage]=useState('');
 const [busy,setBusy]=useState(false);
 const load=useCallback(async()=>{try{setTeam(await accountApi('/api/team',token))}catch(e){setMessage(e instanceof Error?e.message:'Unable to load your team.')}},[token]);
 useEffect(()=>{void load()},[load]);
 async function run(fn:()=>Promise<void>){setBusy(true);setMessage('');try{await fn()}catch(e){setMessage(e instanceof Error?e.message:'That did not work. Try again.')}finally{setBusy(false)}}
 const invite=(e:React.FormEvent)=>{e.preventDefault();void run(async()=>{const r=await accountApi('/api/team/invites',token,'POST',{email:email.trim(),role:'manager'});setLink(r.invite_url);setEmail('');await load()})};
 const revoke=(id:string)=>run(async()=>{await accountApi(`/api/team/invites/${id}/revoke`,token,'POST');await load()});
 const remove=(id:string)=>run(async()=>{await accountApi(`/api/team/members/${id}/remove`,token,'POST');await load()});
 const destroy=(e:React.FormEvent)=>{e.preventDefault();void run(async()=>{
  const owner=team?.my_role==='owner';
  await accountApi('/api/team/account/delete',token,'POST',{confirm:owner?confirm:'leave'});
  if(owner&&authMode()==='clerk')await deleteClerkUser();
  else await localAuthClient().auth.signOut();
  window.location.assign(owner?'/?deleted=1':'/?left=1');
 })};
 if(!team)return <section className="ts-settings-card"><p className="ts-muted">{message||'Loading your team…'}</p></section>;
 const owner=team.my_role==='owner';
 return <>
  <section className="ts-settings-card" aria-labelledby="team-h">
   <div className="ts-section-icon"><Users size={24}/></div>
   <h2 id="team-h">Team</h2>
   <p className="ts-muted">{owner?'Managers can see the dashboard, sync data and save decisions. Only you can connect Square, manage billing, invite people or delete the workspace.':'You are a manager in this workspace. The owner manages billing, connections and the team.'}</p>
   <ul style={{listStyle:'none',padding:0,display:'grid',gap:8}}>
    {team.members.map(m=><li key={m.id} style={{display:'flex',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}>
     <span>{m.email||(m.is_me?'You':'Member')}{m.is_me&&m.email?' (you)':''} · <strong>{m.role}</strong></span>
     {owner&&!m.is_me&&<button className="ts9-text-button" disabled={busy} onClick={()=>void remove(m.id)}>Remove</button>}
    </li>)}
   </ul>
   {owner&&<>
    {team.pending_invites.length>0&&<><h3>Pending invites</h3><ul style={{listStyle:'none',padding:0,display:'grid',gap:8}}>
     {team.pending_invites.map(i=><li key={i.id} style={{display:'flex',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}>
      <span>{i.email} · expires {new Date(i.expires_at*1000).toLocaleDateString()}</span>
      <button className="ts9-text-button" disabled={busy} onClick={()=>void revoke(i.id)}>Revoke</button></li>)}</ul></>}
    <form className="ts-form" onSubmit={invite}>
     <label htmlFor="invite-email">Invite a manager by email</label>
     <input id="invite-email" type="email" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="manager@restaurant.com"/>
     <button className="ts-btn-dark" type="submit" disabled={busy}><UserPlus size={16}/> Create invite link</button>
    </form>
    {link&&<div className="ts-alert good" role="status">
     Send this link to them. It works once and expires in 7 days.
     <div style={{display:'flex',gap:8,marginTop:8,flexWrap:'wrap'}}><code style={{wordBreak:'break-all'}}>{link}</code>
      <button className="ts9-text-button" onClick={()=>void navigator.clipboard?.writeText(link)}><Copy size={14}/> Copy</button></div>
    </div>}
   </>}
  </section>
  <section className="ts-settings-card" aria-labelledby="danger-h">
   <div className="ts-section-icon"><Trash2 size={24}/></div>
   <h2 id="danger-h">{owner?'Delete workspace':'Leave workspace'}</h2>
   <p className="ts-muted">{owner?'This permanently deletes your restaurant workspace, imported Square data, decisions and team, and your login. Cancel any subscription first. Then revoke TableSignal in Square under Account & Settings → Apps.':'You will lose access to this workspace. Your login stays, with a new empty workspace.'}</p>
   <form className="ts-form" onSubmit={destroy}>
    {owner&&<><label htmlFor="confirm-name">Type <strong>{team.workspace_name}</strong> to confirm</label>
     <input id="confirm-name" value={confirm} onChange={e=>setConfirm(e.target.value)} autoComplete="off"/></>}
    <button className="ts-btn-dark" type="submit" disabled={busy||(owner&&confirm!==team.workspace_name)}>{owner?'Delete workspace and account':'Leave workspace'}</button>
   </form>
  </section>
  {message&&<div className="ts-alert" role="alert">{message}</div>}
 </>;
}
