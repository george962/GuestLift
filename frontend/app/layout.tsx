import type {Metadata} from 'next';
import './globals.css';
import {Nav,Footer} from '@/components/site';
export const metadata:Metadata={
 title:'TableSignal | Restaurant guest & promotion intelligence',
 description:'Understand who comes back, what offers cost, and what to investigate next. Explore restaurant sales, customer patterns and promotion insights using fictional sample data.',
 openGraph:{title:'TableSignal | Restaurant intelligence',description:'Find out why guests return, and what to do next.'},
};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body><Nav/>{children}<Footer/></body></html>}
