from datetime import date
from decimal import Decimal
import unittest

from services.smart_cashing_service import (
    _clean_smart_entry,
    build_standard_allocations,
    get_collection_coverage,
    record_obligation_payment,
    update_smart_cashing_collection,
)


PREVIEW = {
    "collection_type": "THURSDAY",
    "coverage_start": date(2026, 10, 5),
    "coverage_end": date(2026, 10, 7),
    "previous_sunday": date(2026, 10, 4),
    "buses": [
        {
            "id": 1,
            "registration_number": "ABC123",
            "normal_days": 3,
            "normal_daily_rate": Decimal("600.00"),
            "sunday_rate": Decimal("300.00"),
            "expected_amount": Decimal("1800.00"),
        },
        {
            "id": 2,
            "registration_number": "BCD223",
            "normal_days": 3,
            "normal_daily_rate": Decimal("600.00"),
            "sunday_rate": Decimal("300.00"),
            "expected_amount": Decimal("1800.00"),
        },
    ],
}


class SmartCashingServiceTests(unittest.TestCase):
    def test_sunday_collection_coverage(self):
        coverage = get_collection_coverage(date(2026, 10, 4))

        self.assertEqual(coverage["collection_type"], "SUNDAY")
        self.assertEqual(coverage["coverage_start"], date(2026, 10, 1))
        self.assertEqual(coverage["coverage_end"], date(2026, 10, 3))
        self.assertIsNone(coverage["previous_sunday"])

    def test_thursday_collection_coverage_includes_previous_sunday_option(self):
        coverage = get_collection_coverage(date(2026, 10, 8))

        self.assertEqual(coverage["collection_type"], "THURSDAY")
        self.assertEqual(coverage["coverage_start"], date(2026, 10, 5))
        self.assertEqual(coverage["coverage_end"], date(2026, 10, 7))
        self.assertEqual(coverage["previous_sunday"], date(2026, 10, 4))

    def test_standard_allocations_use_k600_and_sunday_k300(self):
        allocation = build_standard_allocations(PREVIEW, [1, 2], [1], "3900")

        self.assertEqual(allocation["expected_total"], Decimal("3900.00"))
        self.assertEqual(allocation["unallocated_amount"], Decimal("0.00"))
        self.assertEqual(allocation["entries"][0]["sunday_days"], 1)
        self.assertEqual(allocation["entries"][0]["actual_amount"], Decimal("2100.00"))

    def test_unknown_shortage_is_unallocated_not_silent_bus_split(self):
        allocation = build_standard_allocations(PREVIEW, [1, 2], [], "3000", "UNKNOWN_DIFFERENCE")

        self.assertEqual(allocation["expected_total"], Decimal("3600.00"))
        self.assertEqual(allocation["unallocated_amount"], Decimal("-600.00"))
        self.assertEqual([entry["actual_amount"] for entry in allocation["entries"]], [Decimal("1800.00"), Decimal("1800.00")])
        self.assertEqual(allocation["difference_classification"], "UNKNOWN_DIFFERENCE")

    def test_positive_variance_is_surplus(self):
        allocation = build_standard_allocations(PREVIEW, [1, 2], [], "4000")

        self.assertEqual(allocation["unallocated_amount"], Decimal("400.00"))
        self.assertEqual(allocation["difference_classification"], "SURPLUS")

    def test_clean_smart_entry_rejects_unknown_classification(self):
        with self.assertRaisesRegex(ValueError, "classification"):
            _clean_smart_entry(
                {
                    "bus_id": 1,
                    "normal_days": 3,
                    "normal_daily_rate": 600,
                    "sunday_days": 0,
                    "sunday_rate": 300,
                    "actual_amount": 1800,
                    "difference_classification": "MADE_UP",
                }
            )

    def test_obligation_payment_must_be_positive_before_database_work(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            record_obligation_payment(
                obligation_id=1,
                payment_date=date(2026, 10, 8),
                amount=0,
                financial_account_id=9,
            )

    def test_smart_correction_requires_bus_entries_before_database_work(self):
        with self.assertRaisesRegex(ValueError, "Choose at least one bus"):
            update_smart_cashing_collection(
                collection_id=1,
                collection_date=date(2026, 10, 4),
                financial_account_id=9,
                total_received=0,
                entries=[],
                unallocated_amount=0,
            )


if __name__ == "__main__":
    unittest.main()

