/** Clerk-backed client with the same shape as the local development client, so pages work unchanged.
 * Clerk owns sign-up, email verification, password reset and sessions. The backend receives a
 * short-lived session token (Authorization: Bearer) that is fetched fresh for every request.
 */
import {SESSION_EXPIRED_EVENT} from './auth-mode';

type ClerkUser={id:string;primaryEmailAddress?:{emailAddress:string}|null;delete:()=>Promise<void>};
type ClerkSession={status?:string;getToken:()=>Promise<string|null>};
type ClerkLike={loaded:boolean;user:ClerkUser|null|undefined;session:ClerkSession|null|undefined;
  signOut:(opts?:{redirectUrl?:string})=>Promise<void>;
  addListener:(cb:(e:{user?:ClerkUser|null;session?:ClerkSession|null})=>void)=>()=>void};
type Session={user:{id:string;email:string};access_token:string};
type Listener=(event:string,session:Session|null)=>void;

async function clerk():Promise<ClerkLike>{
 for(let i=0;i<100;i++){
  const c=(globalThis as unknown as {Clerk?:ClerkLike}).Clerk;
  if(c?.loaded)return c;
  await new Promise(r=>setTimeout(r,100));
 }
 throw new Error('Sign-in service did not load. Check your connection and refresh.');
}

async function current():Promise<Session|null>{
 const c=await clerk();
 // Right after sign-up (or a Clerk "task" such as choosing an organization) the session can be
 // pending for a moment. Wait briefly rather than report the user as signed out.
 for(let i=0;i<50&&((c.user&&!c.session)||c.session?.status==='pending');i++)await new Promise(r=>setTimeout(r,100));
 if(!c.user||!c.session)return null;
 const token=await c.session.getToken();
 if(!token)return null;
 return {user:{id:c.user.id,email:c.user.primaryEmailAddress?.emailAddress||''},access_token:token};
}

const unsupported=(what:string)=>Promise.resolve({data:{session:null,user:null},error:new Error(`${what} is handled on the Clerk sign-in screen.`)});

export const clerkClient={
 auth:{
  async getSession(){try{return {data:{session:await current()},error:null}}catch(e){return {data:{session:null},error:e instanceof Error?e:new Error('Session check unavailable')}}},
  signUp(_:{email:string;password:string;options?:unknown}){return unsupported('Sign-up')},
  signInWithPassword(_:{email:string;password:string}){return unsupported('Sign-in')},
  async signOut(){try{await (await clerk()).signOut();return {error:null}}catch(e){return {error:e instanceof Error?e:new Error('Sign out failed')}}},
  onAuthStateChange(callback:Listener){
   let off=()=>{};let active=true;
   void clerk().then(c=>{if(!active)return;let had=Boolean(c.session);
    off=c.addListener(({session})=>{
     if(!session&&had){had=false;callback('SIGNED_OUT',null)}
     else if(session&&!had){had=true;void current().then(s=>callback('SIGNED_IN',s))}
    })}).catch(()=>{});
   return {data:{subscription:{unsubscribe(){active=false;off()}}}};
  },
  async resetPasswordForEmail(_email:string){return {error:new Error('Use "Forgot password?" on the sign-in screen.')}},
  async updateUser(_:{password:string;current_password?:string}){return {error:new Error('Change your password from Account → Security.')}},
 }
};

/** A fresh token for each API call; Clerk refreshes it behind the scenes. */
export async function clerkToken():Promise<string>{
 const c=await clerk();
 const token=c.session?await c.session.getToken():null;
 if(!token)throw new Error('Your session has ended. Sign in again.');
 return token;
}

export async function deleteClerkUser():Promise<void>{const c=await clerk();if(c.user)await c.user.delete()}

/** API call with a fresh Clerk session token. A 401 raises the "session ended" banner. */
export async function clerkApi(url:string,method:'GET'|'POST',body?:unknown){
 const response=await fetch(url,{
  method,cache:'no-store',credentials:'omit',
  headers:{Authorization:'Bearer '+await clerkToken(),...(body!==undefined?{'Content-Type':'application/json'}:{})},
  body:body!==undefined?JSON.stringify(body):undefined
 });
 const result=await response.json().catch(()=>({detail:response.statusText}));
 if(response.status===401&&typeof window!=='undefined')window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
 if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:`Request failed (${response.status}).`);
 return result;
}
