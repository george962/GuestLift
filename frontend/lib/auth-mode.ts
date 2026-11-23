/** Which identity system the frontend uses. Build-time: NEXT_PUBLIC_AUTH_MODE=clerk for hosted builds. */
export type AuthMode='local'|'clerk';
export const authMode=():AuthMode=>process.env.NEXT_PUBLIC_AUTH_MODE==='clerk'?'clerk':'local';
export const SESSION_EXPIRED_EVENT='tablesignal:session-expired';
