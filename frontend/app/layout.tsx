import type { Metadata } from 'next';
import './globals.css';
import { Nav, Footer } from '@/components/site';

export const metadata: Metadata = {
  title: 'GuestLift — Restaurant data, finally speaking the same language',
  description: 'See how Toast POS and Square POS data flow into one transparent, reliable restaurant analytics model. Explore the synthetic demo.',
  openGraph: { title: 'GuestLift | Restaurant intelligence', description: 'Different POS systems. One trusted data model.' },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Nav/>{children}<Footer/></body></html>;
}
