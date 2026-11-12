import type { Metadata } from 'next';
import './globals.css';
import { Nav, Footer } from '@/components/site';

export const metadata: Metadata = {
  title: 'GuestLift | Restaurant data & offer intelligence',
  description: 'Explore a transparent Toast and Square data pipeline and model coupon economics using fictional restaurant orders. An independent prototype with no real merchant data.',
  openGraph: { title: 'GuestLift | Restaurant intelligence', description: 'Different POS systems. One trusted data model.' },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Nav/>{children}<Footer/></body></html>;
}
