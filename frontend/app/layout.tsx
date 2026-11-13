import type {Metadata} from 'next';
import './globals.css';
import {Nav,Footer} from '@/components/site';
export const metadata:Metadata={
 title:'TableSignal | Restaurant retention and promotion intelligence',
 description:'Understand returning guests, explore promotion costs, and save evidence-backed restaurant decisions. A free fictional demo and local Square Sandbox developer integration.',
 openGraph:{title:'TableSignal | Restaurant intelligence',description:'Find out why guests return, and what to do next.'},
};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body><Nav/>{children}<Footer/></body></html>}
