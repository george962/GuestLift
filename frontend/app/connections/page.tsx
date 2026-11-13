'use client';

import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowRight, CheckCircle2, Database, ExternalLink, Info, PlugZap, RefreshCcw,
  ShieldCheck, Trash2, Store, LifeBuoy, Clock3} from 'lucide-react';
import {accountApi,localAuthClient} from '@/lib/local-auth';

type Run={status:string;started_at:string;scanned:number;inserted:number;updated:number;skipped:number};
type Connection={connected:boolean;environment:string;merchant_id:string|null;credential_mode:string|null;
  last_sync_at:string|null;last_error:string|null;developer_token_configured:boolean;oauth_configured:boolean;
  production_enabled:boolean;runs:Run[];assisted_requests:{provider:string;status:string;created_at:string}[]};

export default function Connections(){
  const [token,setToken]=useState('');
  const [status,setStatus]=useState<Connection|null>(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  const [assistProvider,setAssistProvider]=useState('square');
  const [assistNote,setAssistNote]=useState('');
  const [synced,setSynced]=useState<{scanned:number;inserted:number;updated:number;skipped:number}|null>(null);
  const reload=useCallback(async()=>{
    try{
      const s=await localAuthClient().auth.getSession();const t=s.data.session?.access_token||'';
      setToken(t);
      if(t)setStatus(await accountApi('/api/integrations/square/status',t));
      else setStatus(null);
    }catch(e){setMessage(e instanceof Error?e.message:'Unable to read connection status.');}
    finally{setLoading(false);}
  },[]);
  useEffect(()=>{void reload()},[reload]);
  async function action(path:string,payload?:unknown){
    if(!token)return;
    setBusy(true);setMessage('');
    try{
      const result=await accountApi('/api/integrations/square/'+path,token,'POST',payload);
      if(path==='oauth/start'){
        if(typeof result.url==='string'&&result.url.startsWith('https://connect.squareupsandbox.com/oauth2/authorize'))window.location.assign(result.url);
      }else if(path==='sync'){
        setSynced(result);
        setMessage(`Square sync complete: ${result.scanned} scanned, ${result.inserted} new, ${result.updated} refreshed, ${result.skipped} skipped.`);
      }else if(path==='assisted-setup'){
        setMessage('Request stored locally. No notification was sent; the project developer must review it.');
        setAssistNote('');
      }else{
        setMessage(path==='disconnect'?'Sandbox connection and imported orders deleted locally.':'Square Sandbox connected. Sync your orders next.');
      }
      await reload();
    }catch(e){setMessage(e instanceof Error?e.message:'Connection action failed.');}
    finally{setBusy(false);}
  }
  function remove(){
    if(window.confirm('Delete this workspace\'s local Square connection AND all its imported Sandbox orders?')){
      void action('disconnect');
    }
  }
  const connected=Boolean(status?.connected);
  return <main className="ts9-app">
    <header className="ts9-app-top"><div><span className="ts9-kicker">ONBOARDING · STEP 2 OF 3</span><h1>Connect your data source.</h1><p>Make this workspace specific to your restaurant—not the sample restaurant everyone sees.</p></div>
      <Link href="/dashboard" className="ts9-button secondary">My dashboard <ArrowRight size={16}/></Link>
    </header>
    {!token&&!loading&&<div className="ts9-empty"><ShieldCheck size={30}/><h2>Sign in to connect a data source.</h2><Link href="/sign-in?next=%2Fconnections" className="ts9-button primary">Sign in <ArrowRight size={16}/></Link></div>}
    {loading&&<div className="ts9-notice">Checking your local account…</div>}
    {token&&<>
      <div className="ts9-onboarding-steps"><div className="done"><CheckCircle2 size={17}/> 1 · Create account and restaurant</div><div className="current"><PlugZap size={17}/> 2 · Connect Square Sandbox</div><div><Database size={17}/> 3 · Sync and analyze</div></div>
      <section className="ts9-panel ts9-connection-panel">
        <div className="ts9-connection-head"><div className="ts9-provider"><span className="ts9-provider-mark">■</span><div><span className="ts9-kicker">REAL API · TEST ENVIRONMENT</span><h2>Square Sandbox</h2><p>Square's hosted development API. No live seller or payment data.</p></div></div>
          <span className={'ts9-pill '+(connected?'ok':'')}>{connected?'Connected':'Not connected'}</span></div>
        {connected?<>
          <div className="ts9-connection-meta"><div><small>Sandbox merchant</small><strong>{status?.merchant_id}</strong></div><div><small>Connection type</small><strong>{status?.credential_mode==='oauth'?'Sandbox OAuth':'Local developer token'}</strong></div><div><small>Last successful sync</small><strong>{status?.last_sync_at?new Date(status.last_sync_at).toLocaleString():'Not yet synced'}</strong></div></div>
          {status?.last_error&&<div className="ts9-notice danger">{status.last_error}</div>}
          <div className="ts9-inline-actions"><button className="ts9-button primary" disabled={busy} onClick={()=>void action('sync')}><RefreshCcw size={17}/>{busy?'Working…':'Sync last 180 days'}</button>
          <button className="ts9-button secondary" disabled={busy} onClick={remove}><Trash2 size={16}/> Disconnect and delete imported orders</button></div>
          {synced&&<div className="ts9-notice success" role="status"><CheckCircle2 size={17}/> Sync complete: {synced.inserted} new · {synced.updated} refreshed · {synced.skipped} skipped · {synced.scanned} scanned. <Link href="/opportunities" style={{fontWeight:700}}>Review business opportunities <ArrowRight size={14}/></Link></div>}
        </>:<>
          <div className="ts9-connection-choices"><div><h3>Option A · One-click developer Sandbox</h3><p>For testing your own Square Sandbox seller. Its token stays in your local backend <code>.env</code>, never in the browser.</p>
            <button className="ts9-button primary" disabled={busy||!status?.developer_token_configured} onClick={()=>void action('connect-developer-sandbox')}>Connect my Sandbox <ArrowRight size={16}/></button>
            {!status?.developer_token_configured&&<small>Add <code>SQUARE_SANDBOX_ACCESS_TOKEN</code> in your local <code>.env</code> first.</small>}
          </div><div><h3>Option B · Seller authorization (OAuth)</h3><p>Simulate a seller granting restricted access via Square Sandbox. Requires Sandbox OAuth application credentials and a registered callback.</p>
            <button className="ts9-button secondary" disabled={busy||!status?.oauth_configured} onClick={()=>void action('oauth/start')}>Authorize with Square Sandbox <ExternalLink size={16}/></button>
            {!status?.oauth_configured&&<small>Requires Sandbox app ID, secret, callback URL and a local encryption key.</small>}
          </div></div>
        </>}
      </section>
      <section className="ts9-panel"><span className="ts9-kicker">IMPORT ACTIVITY</span><h3>Sync history</h3>
        {!status?.runs?.length?<p className="ts9-muted">No sync attempts yet. Once connected, this shows when data was imported and how many records were created or refreshed.</p>:<div className="ts9-run-list">{status.runs.map((r,i)=><div key={i}><span><Clock3 size={15}/> {new Date(r.started_at).toLocaleString()}</span><strong>{r.status}</strong><small>{r.scanned} scanned · {r.inserted} new · {r.updated} updated</small></div>)}</div>}
      </section>
      <section className="ts9-panel"><span className="ts9-kicker">ASSISTED ONBOARDING · FUTURE SERVICE</span><h3>Prefer help getting connected?</h3>
        <p>We can record a local onboarding request as a potential future service included in the subscription. This version does not send a support email or schedule an appointment.</p>
        <div className="ts9-ask-row"><select value={assistProvider} onChange={e=>setAssistProvider(e.target.value)} aria-label="POS provider"><option value="square">Square</option><option value="toast">Toast</option><option value="other">Other</option></select>
          <button className="ts9-button secondary" disabled={busy} onClick={()=>void action('assisted-setup',{provider:assistProvider,note:assistNote})}><LifeBuoy size={16}/> Save setup request</button></div>
        <textarea aria-label="Optional setup context" value={assistNote} onChange={e=>setAssistNote(e.target.value.slice(0,300))} placeholder="Optional: number of locations or questions. Do not enter passwords, API keys, or customer information." rows={3} className="ts9-textarea"/>
        {(status?.assisted_requests||[]).map((r,i)=><p className="ts9-muted" key={i}>Request recorded: {r.provider} · {r.status} · {new Date(r.created_at).toLocaleDateString()}</p>)}
      </section>
      {message&&<div className="ts9-notice" role="status">{message}</div>}
      <div className="ts9-important"><Info size={20}/><p><strong>Developer-only connection.</strong> This release never touches Square production. Totals exclude reported taxes and tips but are not payment/refund reconciled; Sandbox tests are not evidence of a real restaurant's revenue. For vendor development, see <a href="https://developer.squareup.com/apps" target="_blank" rel="noreferrer">Square Developer Console <ExternalLink size={13}/></a>.</p></div>
    </>}
  </main>
}
