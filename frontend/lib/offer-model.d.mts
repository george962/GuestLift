export interface ScenarioOrder {
  provider: 'toast' | 'square';
  source_order_id: string;
  location_id: string;
  net_sales_minor: number;
  status: string;
}
export interface OfferConfig {
  type: 'percent' | 'fixed' | 'free_item';
  minimumMinor: number;
  value: number;
  amountMinor: number;
  marginPercent: number;
}
export interface OfferDetail {
  provider: string;
  orderId: string;
  location: string;
  baseNetMinor: number;
  incrementalDiscountMinor: number;
  extraRewardCostMinor: number;
  afterOfferNetMinor: number;
}
export interface OfferResult {
  orderCount: number;
  eligibleCount: number;
  baseNetMinor: number;
  modeledNetMinor: number;
  additionalDiscountMinor: number;
  rewardCostMinor: number;
  offerCostMinor: number;
  baseContributionMinor: number;
  scenarioContributionMinor: number;
  breakEvenAddedOrders: number | null;
  extraOrderContributionMinor: number;
  details: OfferDetail[];
}
export function evaluateOffer(orders: ScenarioOrder[], config: OfferConfig): OfferResult;
