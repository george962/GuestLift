import type {Metadata} from 'next';
import V012Experience from '@/components/v012-experience';
import './v012.css';

export const metadata:Metadata={
  title:'TableSignal | Restaurant insights that lead to decisions',
  description:'See restaurant sales, guest, and promotion data together. Investigate what changed, review the evidence, and track your next decision. Explore a fictional preview; live merchant connections and billing are not enabled.',
  openGraph:{
    title:'TableSignal | From restaurant data to your next move',
    description:'Connect the numbers, investigate what matters, and track the decision. Explore TableSignal with fictional restaurant data.'
  }
};

export default function Home(){
  return <V012Experience/>;
}
