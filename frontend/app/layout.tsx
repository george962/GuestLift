import type { Metadata } from 'next';
import './globals.css';
import { Nav, Footer } from '@/components/site';

export const metadata: Metadata = {
  title: 'GuestLift | Restaurant intelligence from data to decisions',
  description: 'A restaurant intelligence workspace for sales, customers, promotions and evidence-backed AI analysis. Explore the free synthetic-data sandbox.',
  openGraph: { title: 'GuestLift | Restaurant intelligence', description: 'Different POS systems. One trusted data model.' },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Nav/>{children}<Footer/></body></html>;
}
