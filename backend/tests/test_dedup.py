import unittest
from datetime import datetime
from decimal import Decimal

from app.ocr.dedup import dedup_trades
from app.schemas import TradeInput


class TestDedup(unittest.TestCase):
    def test_dedup_by_symbol_price_qty_timestamp(self):
        ts = datetime(2026, 3, 5, 10, 0, 47)
        trades = [
            TradeInput(symbol="RKLB", side="BUY", qty=100, price=Decimal("69.00"), fee=Decimal("0"), timestamp=ts),
            TradeInput(symbol="RKLB", side="SELL", qty=100, price=Decimal("69.00"), fee=Decimal("0"), timestamp=ts),
            TradeInput(symbol="RKLB", side="BUY", qty=100, price=Decimal("69.0000"), fee=Decimal("0"), timestamp=ts),
            TradeInput(symbol="TSLA", side="BUY", qty=100, price=Decimal("69.00"), fee=Decimal("0"), timestamp=ts),
        ]
        out, removed = dedup_trades(trades)
        self.assertEqual(len(out), 2)
        self.assertEqual(len(removed), 2)

    def test_no_dedup_when_timestamp_missing(self):
        trades = [
            TradeInput(symbol="RKLB", side="BUY", qty=100, price=Decimal("69.00"), fee=Decimal("0"), timestamp=None),
            TradeInput(symbol="RKLB", side="BUY", qty=100, price=Decimal("69.00"), fee=Decimal("0"), timestamp=None),
        ]
        out, removed = dedup_trades(trades)
        self.assertEqual(len(out), 2)
        self.assertEqual(len(removed), 0)


if __name__ == "__main__":
    unittest.main()

