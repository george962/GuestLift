/** Local development account client.
 * The session secret is an HttpOnly backend cookie, never JS storage.
 * `access_token` is ONLY a presence marker for the legacy UI; the server
 * ignores it and authenticates each request using its cookie.
 */
type User={id:string;email:string};
type LocalSession={user:User;access_token:'cookie-session'};
type AuthResult={data:{session:LocalSession|null;user?:User|null};error:Error|null};
type Listener=(event:string,session:LocalSession|null)=>void;
let csrfToken:string|null=null;
const listeners=new Set<Listener>();
const notify=(event:string,session:LocalSession|null)=>{for(const f of listeners)f(event,session)};
export const apiOrigin=()=>process.env.NEXT_PUBLIC_GUESTLIFT_API_URL||'http://localhost:8000';

async function api(path:string,method:'GET'|'POST'='GET',body?:unknown,csrf?:string){
 const response=await fetch(apiOrigin()+path,{
  method,credentials:'include',cache:'no-store',
  headers:{...(body!==undefined?{'Content-Type':'application/json'}:{}),...(csrf?{'X-CSRF-Token':csrf}:{})},
  body:body!==undefined?JSON.stringify(body):undefined
 });
 const result=await response.json().catch(()=>({detail:response.statusText}));
 if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:`Request failed (${response.status}).`);
 return result;
}
async function session():Promise<LocalSession|null>{
 let lastError:unknown=null;
 for(let attempt=0;attempt<3;attempt++){
  try{
   const result=await api('/api/local-auth/session');
   csrfToken=result.authenticated?result.csrf_token:null;
   return result.authenticated?{user:result.user,access_token:'cookie-session'}:null;
  }catch(e){lastError=e;if(attempt<2)await new Promise(resolve=>setTimeout(resolve,250*(attempt+1)));}
 }
 // A network outage is NOT a logout. Do not erase an existing CSRF token.
 throw lastError instanceof Error?lastError:new Error('Account connection temporarily unavailable. Retry.');
}

async function authenticate(path:'/api/local-auth/login'|'/api/local-auth/register',email:string,password:string):Promise<AuthResult>{
 try{
  const result=await api(path,'POST',{email,password});
  const current=await session();
  if(!current)throw new Error('Session cookie could not be established. Check localhost cookie settings.');
  notify(path.endsWith('login')?'SIGNED_IN':'SIGNED_UP',current);
  return {data:{session:current,user:result.user},error:null};
 }catch(e){return {data:{session:null,user:null},error:e instanceof Error?e:new Error('Account request failed')}}
}
const localClient={
 auth:{
  async getSession(){try{return {data:{session:await session()},error:null}}catch(e){return {data:{session:null},error:e instanceof Error?e:new Error('Session check unavailable')}}},
  signUp({email,password}:{email:string;password:string;options?:unknown}){return authenticate('/api/local-auth/register',email,password)},
  signInWithPassword({email,password}:{email:string;password:string}){return authenticate('/api/local-auth/login',email,password)},
  async signOut(){try{await api('/api/local-auth/logout','POST',{},csrfToken||(await api('/api/local-auth/session')).csrf_token);csrfToken=null;notify('SIGNED_OUT',null);return {error:null}}catch(e){return {error:e instanceof Error?e:new Error('Sign out failed')}}},
  onAuthStateChange(callback:Listener){listeners.add(callback);return {data:{subscription:{unsubscribe(){listeners.delete(callback)}}}}},
  async resetPasswordForEmail(_email:string){return {error:new Error('Email recovery is not enabled for local development. Sign in and use Change Password under Account instead.')}},
  async updateUser({password,current_password}:{password:string;current_password?:string}){
   try{
    if(!current_password)throw new Error('Enter your current password to change it locally.');
    await api('/api/local-auth/change-password','POST',{current_password,new_password:password},csrfToken||(await api('/api/local-auth/session')).csrf_token);
    return {error:null};
   }catch(e){return {error:e instanceof Error?e:new Error('Password update failed')}}
  }
 }
};
export function localAuthClient(){return localClient}
export async function accountApi(path:string,token:string,method:'GET'|'POST'='GET',body?:unknown){
 if(!token)throw new Error('Sign in to your local account first.');
 if(method==='POST'&&!csrfToken)await session();
 return api(path,method,body,method==='POST'?csrfToken||'':undefined);
}
