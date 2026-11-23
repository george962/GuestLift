'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight,Users} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';

/** Accept a team invite. Signed-out visitors sign up or sign in first, then return here. */
export default function Join(){
 const [state,setState]=useState<'checking'|'signed-out'|'joining'|'joined'|'error'>('checking');
 const [message,setMessage]=useState('');
 const [token,setToken]=useState('');
 useEffect(()=>{
  const t=new URLSearchParams(window.location.search).get('token')||'';setToken(t);
  if(!t){setState('error');setMessage('This invite link is incomplete. Ask the owner to send it again.');return}
  void localAuthClient().auth.getSession().then(async({data})=>{
   const session=data.session;if(!session){setState('signed-out');return}
   setState('joining');
   try{await accountApi('/api/team/invites/accept',session.access_token,'POST',{token:t});setState('joined')}
   catch(e){setState('error');setMessage(e instanceof Error?e.message:'Could not join the workspace.')}
  });
 },[]);
 const next=encodeURIComponent('/join?token='+token);
 return <main className="ts10-app"><div className="ts10-card ts10-empty"><Users size={40}/>
  <span className="ts10-eyebrow">TEAM INVITE</span>
  <h1>{state==='joined'?'You joined the workspace.':state==='signed-out'?'You have been invited to a TableSignal workspace.':state==='error'?'This invite could not be used.':'Joining…'}</h1>
  {message&&<p role="alert">{message}</p>}
  <div className="ts10-actions">
   {state==='joined'&&<Link className="ts10-primary" href="/dashboard">Open the dashboard <ArrowRight size={16}/></Link>}
   {state==='signed-out'&&<><Link className="ts10-primary" href={`/sign-up?next=${next}`}>Create an account to join <ArrowRight size={16}/></Link>
    <Link className="ts10-secondary" href={`/sign-in?next=${next}`}>I already have an account</Link></>}
  </div>
 </div></main>;
}
