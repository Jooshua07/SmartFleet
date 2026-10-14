import unittest
from datetime import date, timedelta
from decimal import Decimal
from services.maintenance_service import servicing_warning, servicing_costs


class ServicingTest(unittest.TestCase):
    def test_thresholds(self):
        today=date(2026,10,14)
        for days, label in [(15,'Normal'),(14,'Warning'),(8,'Warning'),(7,'Urgent'),(0,'Urgent'),(-1,'Overdue')]:
            self.assertEqual(servicing_warning(today+timedelta(days=days),today),label)

    def test_costs_and_invalid(self):
        self.assertEqual(sum(servicing_costs('100','50','0')),Decimal('150'))
        for value in ('-1','NaN','abc','0.001'):
            with self.assertRaises(ValueError):
                servicing_costs(value,0,0)

    def test_early_late(self):
        self.assertEqual(date(2026,10,16)+timedelta(days=35),date(2026,11,20))
        self.assertEqual(date(2026,10,20)+timedelta(days=35),date(2026,11,24))
