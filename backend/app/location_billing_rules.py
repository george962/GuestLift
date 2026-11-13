"""Pure reference domain rules for TableSignal's provider-verified location billing.

v0.12 prototype ONLY. No API endpoints, Stripe events, OAuth credentials, database
persistence or production charge capability are provided by this module.

A production service MUST construct ProviderLocation from authenticated provider
records and verified canonical mappings, never directly from client JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


MONTHLY_LOCATION_PRICE_MINOR = 9_900  # Proposed $99.00 in USD cents; NOT a live Stripe price.


@dataclass(frozen=True)
class ProviderLocation:
    merchant_id: str
    provider_location_id: str
    canonical_location_id: str
    name: str
    status: str
    location_kind: str | None
    supported_order_data: bool
    owner_approved_mapping: bool = False

    @property
    def provider_key(self) -> tuple[str, str]:
        return (self.merchant_id, self.provider_location_id)

    @property
    def eligible(self) -> bool:
        # Cautious: physical ACTIVE location with tested order access and vetted mapping.
        # Other Square location types are explicitly reviewed, not auto-billed.
        return (
            self.status.upper() == "ACTIVE"
            and self.location_kind == "PHYSICAL"
            and self.supported_order_data
            and self.owner_approved_mapping
            and bool(self.canonical_location_id.strip())
        )


@dataclass(frozen=True)
class Quote:
    detected_count: int
    eligible_count: int
    selected_provider_count: int
    billable_canonical_count: int
    monthly_subtotal_minor: int
    currency: str = "USD"


def quote_selected_locations(
    authorized_locations: Iterable[ProviderLocation],
    selected_provider_keys: Iterable[tuple[str, str]],
    *,
    monthly_price_minor: int = MONTHLY_LOCATION_PRICE_MINOR,
) -> Quote:
    """Calculate an untrusted DISPLAY quote from trusted provider-side discovery.

    The selection may contain only keys returned to this organization's server-side
    authenticated provider connection. The client cannot supply count or amount.
    Canonical store IDs are server-verified before combining provider connections.
    Real subscription quantity is derived again from stored, approved entitlements
    during Stripe checkout and webhook reconciliation, never this preview object.
    """
    if monthly_price_minor <= 0:
        raise ValueError("Configured price must be positive")

    available = list(authorized_locations)
    by_key = {location.provider_key: location for location in available}
    if len(available) != len(by_key):
        raise ValueError("Duplicate provider location in authoritative discovery")

    selected = list(selected_provider_keys)
    if len(selected) != len(set(selected)):
        raise ValueError("Selection contains duplicate provider locations")
    if not selected:
        raise ValueError("Select at least one eligible monitored location")

    resolved: list[ProviderLocation] = []
    for key in selected:
        if key not in by_key:
            raise ValueError("Selected location was not authorized for this organization")
        location = by_key[key]
        if not location.eligible:
            raise ValueError("Selected location is inactive, unsupported or needs review")
        resolved.append(location)

    canonical_ids = {location.canonical_location_id for location in resolved}
    return Quote(
        detected_count=len(available),
        eligible_count=sum(location.eligible for location in available),
        selected_provider_count=len(resolved),
        billable_canonical_count=len(canonical_ids),
        monthly_subtotal_minor=monthly_price_minor * len(canonical_ids),
    )
