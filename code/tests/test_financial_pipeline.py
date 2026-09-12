import unittest
from datetime import date
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.dates import parse_date, format_date, add_days
from utils.currency import CurrencyConverter
from utils.formatting import format_payment_plan, format_spending_changes
from vision_extractor import VisionExtractor

class TestFinancialPipeline(unittest.TestCase):
    def test_date_utils(self):
        d = parse_date("2026-09-12")
        self.assertEqual(d, date(2026, 9, 12))
        self.assertEqual(format_date(d), "2026-09-12")
        self.assertEqual(add_days(d, 5), date(2026, 9, 17))

    def test_formatting_utils(self):
        schedule = [(date(2026, 9, 12), 500.0), (date(2026, 10, 12), 250.50)]
        self.assertEqual(format_payment_plan(schedule), "2026-09-12:500|2026-10-12:250.5")
        
        changes = ["stop:event_14", "reduce_to:event_21:100"]
        self.assertEqual(format_spending_changes(changes), "stop:event_14|reduce_to:event_21:100")

    def test_vision_extractor(self):
        extractor = VisionExtractor()
        amt = extractor.get_event_amount("event_253")
        self.assertEqual(amt, 4365000.0)

    def test_currency_converter(self):
        rates_data = {
            "rate_date": ["2026-09-15"],
            "from_currency": ["USD"],
            "to_currency": ["INR"],
            "rate": [83.33]
        }
        df = pd.DataFrame(rates_data)
        converter = CurrencyConverter(df)
        converted = converter.convert(100.0, "USD", "INR", date(2026, 9, 15))
        self.assertAlmostEqual(converted, 8333.0, places=2)

if __name__ == "__main__":
    unittest.main()
