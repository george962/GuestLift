import type {Order,Provider} from './types';
export declare const DEMO_FILES: Record<Provider, string[]>;
export declare function parseCsv(content:string):Record<string,string>[];
export declare function transformUploaded(provider:Provider, files:Record<string,string>):{
  provider:Provider; records:Order[];
  summary:{orders:number;items:number;payments:number;net_sales_minor:number;discounts_minor:number;refunds_minor:number};
  warnings:string[];
};
