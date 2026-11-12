import {createClient, type SupabaseClient} from '@supabase/supabase-js';
let client:SupabaseClient | null | undefined;
export function supabaseClient():SupabaseClient|null {
  if(client!==undefined)return client;
  const url=process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key=process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if(!url||!key){client=null;return null}
  client=createClient(url,key,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
  return client;
}
export const apiOrigin=()=>process.env.NEXT_PUBLIC_GUESTLIFT_API_URL||'http://localhost:8000';
export async function accountApi(path:string,token:string,method:'GET'|'POST'='GET',body?:unknown){
  const res=await fetch(apiOrigin()+path,{method,headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,cache:'no-store'});
  const result=await res.json().catch(()=>({detail:res.statusText}));
  if(!res.ok)throw new Error(result.detail||`HTTP ${res.status}`);
  return result;
}
