/**
 * GuestLift offer scenario math.
 * This is a counterfactual COST SCENARIO against existing demo order values;
 * it is NOT a causal estimate of incremental visits, revenue, or profit.
 * All calculations use integer cents except the user-supplied percentage.
 */
export function evaluateOffer(orders, config) {
  const type = ['percent', 'fixed', 'free_item'].includes(config.type) ? config.type : 'percent';
  const thresholdMinor = Math.max(0, Math.round(Number(config.minimumMinor) || 0));
  const value = Math.min(100, Math.max(0, Number(config.value) || 0));
  const marginPercent = Math.min(95, Math.max(0, Number(config.marginPercent) || 0));
  const amountMinor = Math.max(0, Math.round(Number(config.amountMinor) || 0));
  const baseNetMinor = orders.reduce((sum, order) => sum + Math.max(0, order.net_sales_minor), 0);
  const candidateOrders = orders.filter(order =>
    order.net_sales_minor >= thresholdMinor &&
    !['VOIDED', 'CANCELED', 'CANCELLED'].includes(String(order.status).toUpperCase())
  );
  const details = candidateOrders.map(order => {
    const base = Math.max(0, order.net_sales_minor);
    const incrementalDiscountMinor = type === 'percent'
      ? Math.min(base, Math.round(base * value / 100))
      : type === 'fixed' ? Math.min(base, amountMinor) : 0;
    const extraRewardCostMinor = type === 'free_item' ? amountMinor : 0;
    return {
      provider: order.provider,
      orderId: order.source_order_id,
      location: order.location_id,
      baseNetMinor: base,
      incrementalDiscountMinor,
      extraRewardCostMinor,
      afterOfferNetMinor: base - incrementalDiscountMinor,
    };
  });
  const additionalDiscountMinor = details.reduce((sum, item) => sum + item.incrementalDiscountMinor, 0);
  const rewardCostMinor = details.reduce((sum, item) => sum + item.extraRewardCostMinor, 0);
  const offerCostMinor = additionalDiscountMinor + rewardCostMinor;
  const modeledNetMinor = baseNetMinor - additionalDiscountMinor;
  // Product costs and fees are assumed unchanged for the same orders. Adding
  // new visits would require another assumption; no added visits are claimed.
  const baseContributionMinor = Math.round(baseNetMinor * marginPercent / 100);
  const scenarioContributionMinor = baseContributionMinor - offerCostMinor;
  const averageEligibleBaseMinor = details.length
    ? Math.round(details.reduce((sum, item) => sum + item.baseNetMinor, 0) / details.length) : 0;
  const avgExtraCost = details.length ? offerCostMinor / details.length : 0;
  const extraOrderContributionMinor = Math.round(averageEligibleBaseMinor * marginPercent / 100 - avgExtraCost);
  const breakEvenAddedOrders = !details.length || !offerCostMinor ? 0 :
    extraOrderContributionMinor <= 0 ? null : Math.ceil(offerCostMinor / extraOrderContributionMinor);
  return {
    orderCount: orders.length,
    eligibleCount: details.length,
    baseNetMinor,
    modeledNetMinor,
    additionalDiscountMinor,
    rewardCostMinor,
    offerCostMinor,
    baseContributionMinor,
    scenarioContributionMinor,
    breakEvenAddedOrders,
    extraOrderContributionMinor,
    details,
  };
}
