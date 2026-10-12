from decimal import Decimal
import unittest

from utils.cashing_form import (
    CASHING_FORM_VERSION_KEY,
    build_direct_cashing_entries,
    bus_option_label,
    clear_cashing_form_state,
)


class CashingFormTests(unittest.TestCase):
    def test_bus_option_label_uses_registration_and_driver(self):
        label = bus_option_label({"registration_number": "ABC123", "driver_name": "Mary Banda"})

        self.assertEqual(label, "ABC123 | Mary Banda")

    def test_build_direct_cashing_entries_for_one_bus(self):
        entries = build_direct_cashing_entries(
            selected_bus_ids=[1],
            normal_amounts={1: 600},
            sunday_amounts={1: 300},
            reasons={1: "Sunday included"},
        )

        self.assertEqual(
            entries,
            [
                {
                    "include": True,
                    "bus_id": 1,
                    "normal_amount": Decimal("600.00"),
                    "sunday_amount": Decimal("300.00"),
                    "actual_amount": Decimal("900.00"),
                    "explanation": "Sunday included",
                    "notes": None,
                }
            ],
        )

    def test_build_direct_cashing_entries_for_multiple_buses(self):
        entries = build_direct_cashing_entries(
            selected_bus_ids=[1, 2],
            normal_amounts={1: 600, 2: 750},
            sunday_amounts={1: 0, 2: 300},
            reasons={2: "Different amount"},
        )

        self.assertEqual([entry["bus_id"] for entry in entries], [1, 2])
        self.assertEqual(entries[0]["actual_amount"], Decimal("600.00"))
        self.assertEqual(entries[1]["actual_amount"], Decimal("1050.00"))
        self.assertEqual(entries[1]["explanation"], "Different amount")

    def test_build_direct_cashing_entries_requires_bus_selection(self):
        with self.assertRaisesRegex(ValueError, "Choose at least one bus"):
            build_direct_cashing_entries([], {})

    def test_build_direct_cashing_entries_requires_amount_for_each_bus(self):
        with self.assertRaisesRegex(ValueError, "Enter an amount"):
            build_direct_cashing_entries([1], {1: 0})

    def test_clear_cashing_form_state_advances_form_version(self):
        state = {CASHING_FORM_VERSION_KEY: 3, "cash_direct_3_buses": ["ABC123"]}

        clear_cashing_form_state(state)

        self.assertEqual(state[CASHING_FORM_VERSION_KEY], 4)


if __name__ == "__main__":
    unittest.main()
