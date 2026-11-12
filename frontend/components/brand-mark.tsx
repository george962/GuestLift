import type {SVGProps} from 'react';

/**
 * Two source data paths converge on one validated record.
 * The icon encodes GuestLift's product promise, rather than generic growth bars.
 */
export function BrandMark(props:SVGProps<SVGSVGElement>){
  return <svg aria-hidden="true" viewBox="0 0 42 42" fill="none" {...props}>
    <path d="M7 10h10c5 0 8 3 8 8v3" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round"/>
    <path d="M7 31h10c5 0 8-3 8-8v-2" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round"/>
    <path d="M25 21h10" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round"/>
    <circle cx="7" cy="10" r="3.5" fill="#A5B9EF"/>
    <circle cx="7" cy="31" r="3.5" fill="#A5B9EF"/>
    <rect x="22" y="18" width="6" height="6" rx="1.8" fill="#71D9CB"/>
    <circle cx="35" cy="21" r="3.5" fill="#71D9CB"/>
  </svg>;
}
