import unittest
from datetime import datetime
from decimal import Decimal

from app.ocr.parse import parse_text_lines


class TestParsePair(unittest.TestCase):
    def test_pair_lines_to_single_order(self):
        lines = [
            "买入 Rocket Lab 100 03/05",
            "全部成交 RKLB 69.00 09:30:29 (美东)",
            "卖出 Rocket Lab 50 03/04",
            "全部成交 RKLB 74.00 10:44:06 (美东)",
        ]
        trades, warnings = parse_text_lines(lines, "x.png")
        self.assertEqual(warnings, [])
        self.assertEqual(len(trades), 2)

        y = datetime.now().year

        self.assertEqual(trades[0].symbol, "RKLB")
        self.assertEqual(trades[0].side, "BUY")
        self.assertEqual(trades[0].qty, 100)
        self.assertEqual(trades[0].price, Decimal("69.00"))
        self.assertEqual(trades[0].timestamp, datetime(y, 3, 5, 9, 30, 29))

        self.assertEqual(trades[1].symbol, "RKLB")
        self.assertEqual(trades[1].side, "SELL")
        self.assertEqual(trades[1].qty, 50)
        self.assertEqual(trades[1].price, Decimal("74.00"))
        self.assertEqual(trades[1].timestamp, datetime(y, 3, 4, 10, 44, 6))

    def test_fill_line_without_space_between_price_and_time(self):
        lines = [
            "买入 Rocket Lab 100 03/05",
            "全部成交 RKLB 69.0010:00:47(美东)",
        ]
        trades, warnings = parse_text_lines(lines, "x.png")
        self.assertEqual(warnings, [])
        self.assertEqual(len(trades), 1)
        y = datetime.now().year
        self.assertEqual(trades[0].symbol, "RKLB")
        self.assertEqual(trades[0].price, Decimal("69.00"))
        self.assertEqual(trades[0].timestamp, datetime(y, 3, 5, 10, 0, 47))


if __name__ == "__main__":
    unittest.main()
