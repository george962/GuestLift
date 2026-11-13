"""Stand-alone tests; run using python -m unittest discover -s backend/tests -v."""
import unittest

from app.location_billing_rules import ProviderLocation, quote_selected_locations


def store(i, *, status="ACTIVE", kind="PHYSICAL", supported=True, canonical=None,
          merchant="square-merchant-1", approved=True):
    return ProviderLocation(
        merchant_id=merchant,
        provider_location_id=f"sq-{i:02d}",
        canonical_location_id=canonical or f"physical-store-{i:02d}",
        name=f"Store {i}",
        status=status,
        location_kind=kind,
        supported_order_data=supported,
        owner_approved_mapping=approved,
    )


class LocationBillingRulesTests(unittest.TestCase):
    def test_seven_detected_six_eligible_three_selected_three_billed(self):
        locations = [store(i) for i in range(1, 7)] + [store(7, kind="ONLINE")]
        selected = [("square-merchant-1", f"sq-{i:02d}") for i in (1, 2, 3)]
        quote = quote_selected_locations(locations, selected)
        self.assertEqual((quote.detected_count, quote.eligible_count), (7, 6))
        self.assertEqual((quote.selected_provider_count, quote.billable_canonical_count), (3, 3))
        self.assertEqual(quote.monthly_subtotal_minor, 29_700)

    def test_tampered_unauthorized_location_rejected(self):
        with self.assertRaisesRegex(ValueError, "not authorized"):
            quote_selected_locations([store(1)], [("other-merchant", "sq-01")])

    def test_virtual_and_inactive_locations_not_billed(self):
        for record in [store(1, kind="ONLINE"), store(1, status="INACTIVE"),
                       store(1, supported=False), store(1, approved=False)]:
            with self.subTest(record=record), self.assertRaises(ValueError):
                quote_selected_locations([record], [record.provider_key])

    def test_duplicate_submission_and_empty_selection_rejected(self):
        location = store(1)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            quote_selected_locations([location], [location.provider_key, location.provider_key])
        with self.assertRaisesRegex(ValueError, "at least one"):
            quote_selected_locations([location], [])

    def test_same_server_verified_canonical_location_across_merchants_billed_once(self):
        a = store(1, canonical="restaurant-01", merchant="square-A")
        b = store(2, canonical="restaurant-01", merchant="square-B")
        quote = quote_selected_locations([a, b], [a.provider_key, b.provider_key])
        self.assertEqual(quote.selected_provider_count, 2)
        self.assertEqual(quote.billable_canonical_count, 1)
        self.assertEqual(quote.monthly_subtotal_minor, 9_900)

    def test_new_discovered_location_does_not_raise_price_without_selection(self):
        selected = [store(1), store(2)]
        before = quote_selected_locations(selected, [x.provider_key for x in selected])
        after = quote_selected_locations(selected + [store(3)], [x.provider_key for x in selected])
        self.assertEqual(before.monthly_subtotal_minor, after.monthly_subtotal_minor)


if __name__ == "__main__":
    unittest.main()
