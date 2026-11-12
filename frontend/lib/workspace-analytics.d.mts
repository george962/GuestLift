import type {Order} from './types';
export type WorkspaceSummary={
  orders:number;net_sales_minor:number;discount_minor:number;average_order_minor:number;
  identified_orders:number;identified_customers:number;repeat_customers:number;
  identification_coverage_percent:number;repeat_customer_rate_percent:number|null;anonymous_orders:number;
  locations:{location:string;orders:number;net_sales_minor:number;discount_minor:number}[];
  daily:{date:string;orders:number;net_sales_minor:number}[];
  campaigns:{code:string;name:string;redemptions:number;net_sales_minor:number;discount_minor:number;modeled_contribution_minor:number|null}[];
  data_origin:string;
};
export type Answer={answer:string;tool:string;evidence_keys:string[];recommended_next_step:string;engine:string;data_origin:string;causal_claim:boolean};
export function summarizeWorkspace(orders:Order[],campaigns?:{name:string;code:string;redeemed_orders:number;attributed_net_sales_minor:number;recorded_discount_minor:number;modeled_contribution_minor:number|null}[]):WorkspaceSummary;
export function askWorkspace(question:string,summary:WorkspaceSummary):Answer;

export function discoverPatterns(summary:WorkspaceSummary):{id:string;level:string;title:string;detail:string;evidence_keys:string[];question:string}[];
