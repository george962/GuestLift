import type {Metadata} from 'next';
import V012Experience from '@/components/v012-experience';
import './v012.css';

export const metadata:Metadata={
 title:'TableSignal | Know what matters. Know what to do.',
 description:'Explore how TableSignal helps restaurants discover business changes, investigate evidence, make decisions and track outcomes. Fictional product preview; real connections are not yet available.',
 openGraph:{title:'TableSignal | Your restaurant. Your next move.',description:'Go from connected data to evidence-backed business decisions. Explore a fictional restaurant preview.'}
};
export default function Home(){return <V012Experience/>}
