'use client';
import {useEffect,useState} from 'react';
import {accountApi} from '@/lib/local-auth';

type Loc={id:string;name:string;eligible:boolean;selected:boolean};
type Preview={subscribed:boolean;quantity_before:number;quantity_after:number;unit_amount_minor:number;monthly_total_minor:number;
  prorated_change_minor:number;next_invoice_total_minor:number|null;proration_date:number|null;message:string};
const money=(n:number)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);

/** Pick monitored locations; see exactly what it costs (with Stripe's proration) before confirming. */
export function ChangeLocations({token,onChanged}:{token:string;onChanged?:()=>void}){
 const [locs,setLocs]=useState<Loc[]|null>(null);
 const [picked,setPicked]=useState<string[]>([]);
 const [preview,setPreview]=useState<Preview|null>(null);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState('');
 useEffect(()=>{void accountApi('/api/integrations/square/locations',token).then(r=>{
  if(!r.enabled)return;setLocs(r.locations);setPicked(r.selected_location_ids)}).catch(()=>setLocs(null))},[token]);
 if(!locs)return null;
 const toggle=(id:string)=>{setPreview(null);setPicked(p=>p.includes(id)?p.filter(x=>x!==id):[...p,id])};
 async function run(fn:()=>Promise<void>){setBusy(true);setMessage('');try{await fn()}catch(e){setMessage(e instanceof Error?e.message:'That did not work.')}finally{setBusy(false)}}
 const doPreview=()=>run(async()=>setPreview(await accountApi('/api/saas/billing/locations/preview',token,'POST',{location_ids:picked})));
 const confirm=()=>run(async()=>{
  await accountApi('/api/saas/billing/locations/confirm',token,'POST',{location_ids:picked,proration_date:preview?.proration_date});
  setPreview(null);setMessage('Locations updated.');onChanged?.();
 });
 return <section className="ts-settings-card" aria-labelledby="locs-h">
  <span className="ts-kicker">MONITORED LOCATIONS</span><h2 id="locs-h">Change locations</h2>
  <p className="ts-muted">You pay per monitored location. Only these locations are imported and analyzed.</p>
  <ul style={{listStyle:'none',padding:0,display:'grid',gap:8}}>{locs.map(l=><li key={l.id}><label>
   <input type="checkbox" id={'loc-'+l.id} checked={picked.includes(l.id)} disabled={!l.eligible||busy} onChange={()=>toggle(l.id)}/> {l.name}{!l.eligible&&' (not eligible: inactive or not a physical store)'}
  </label></li>)}</ul>
  <button className="ts-btn-dark" disabled={busy||!picked.length} onClick={()=>void doPreview()}>Preview the price</button>
  {preview&&<div className="ts-alert" role="status" data-preview>
   <p><strong>{preview.quantity_before} → {preview.quantity_after} {preview.quantity_after===1?'location':'locations'}</strong> · {money(preview.monthly_total_minor)} per month ({money(preview.unit_amount_minor)} each)</p>
   {preview.subscribed&&<p>{preview.prorated_change_minor===0?'No change to your bill now.':`${preview.prorated_change_minor>0?'Prorated charge':'Prorated credit'} on your next invoice: ${money(Math.abs(preview.prorated_change_minor))}.`}{preview.next_invoice_total_minor!==null&&` Next invoice total: ${money(preview.next_invoice_total_minor)}.`}</p>}
   <p>{preview.message}</p>
   <button className="ts-btn-dark" disabled={busy} onClick={()=>void confirm()}>Confirm change</button>
  </div>}
  {message&&<div className="ts-alert" role="status">{message}</div>}
 </section>;
}
