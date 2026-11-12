import type { Metadata } from 'next';
import './globals.css';
import { Nav, Footer } from '@/components/site';

export const metadata: Metadata = {
  title: 'GuestLift | Restaurant data, verified from source to decision',
  description: 'Upload fabricated Toast CSV or Square JSON records, inspect validation and unified restaurant sales metrics, then model transparent coupon scenarios. No real merchant data.',
  openGraph: { title: 'GuestLift | Restaurant intelligence', description: 'Different POS systems. One trusted data model.' },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Nav/>{children}<Footer/></body></html>;
}
