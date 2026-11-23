import {apiOrigin,localAuthClient} from './local-auth';
import {authMode} from './auth-mode';

/** Owner data export, using cookies locally and fresh Clerk bearer authentication in managed mode. */
export async function accountExportZip():Promise<Blob>{
 const managed=authMode()==='clerk';
 const token=managed?await (await import('./clerk-auth')).clerkToken():null;
 if(!managed){const current=await localAuthClient().auth.getSession();if(current.error)throw current.error;
   if(!current.data.session)throw new Error('Sign in to export your workspace.');}
 const response=await fetch(apiOrigin()+'/api/readiness/export',{
  method:'GET',cache:'no-store',credentials:managed?'omit':'include',
  headers:token?{'Authorization':'Bearer '+token}:{}
 });
 if(!response.ok){const result=await response.json().catch(()=>({detail:'Export could not be generated.'}));
  throw new Error(typeof result.detail==='string'?result.detail:'Export failed.');}
 if(!(response.headers.get('content-type')||'').includes('application/zip'))throw new Error('Export returned an unexpected file type.');
 return response.blob();
}
