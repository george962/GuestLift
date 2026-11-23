/** Only redirect to known in-app pages after sign-in (no open redirects). */
const allowed=new Set(['/billing','/dashboard','/connections','/settings','/onboarding','/account']);
export function safeNext(value:string|null):string{
 if(!value)return '/dashboard';
 if(allowed.has(value))return value;
 if(/^\/join\?token=[A-Za-z0-9_-]{20,200}$/.test(value))return value;
 return '/dashboard';
}
