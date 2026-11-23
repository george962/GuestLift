import type {Metadata} from 'next';
import './globals.css';
import './m6-onboarding.css';
import './m6-readiness.css';
import {ClerkProvider} from '@clerk/nextjs';
import {Nav,Footer} from '@/components/site';
import {SessionExpiredBanner} from '@/components/session-expired-banner';
import {authMode} from '@/lib/auth-mode';
export const metadata:Metadata={
 title:'TableSignal | Restaurant retention and promotion intelligence',
 description:'Understand returning guests, explore promotion costs, and save evidence-backed restaurant decisions. A free fictional demo and local Square Sandbox developer integration.',
 openGraph:{title:'TableSignal | Restaurant intelligence',description:'Find out why guests return, and what to do next.'},
};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){
 const page=<html lang="en"><body><SessionExpiredBanner/><Nav/>{children}<Footer/></body></html>;
 return authMode()==='clerk'?<ClerkProvider publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}>{page}</ClerkProvider>:page;
}
