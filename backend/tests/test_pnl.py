import unittest
from decimal import Decimal

from app.calc.pnl import Trade, compute_realized_pnl


class TestPnL(unittest.TestCase):
    def test_fifo_long_realized(self):
        trades = [
            Trade(symbol="AAPL", side="BUY", qty=100, price=Decimal("10"), fee=Decimal("0")),
            Trade(symbol="AAPL", side="SELL", qty=40, price=Decimal("12"), fee=Decimal("0")),
            Trade(symbol="AAPL", side="SELL", qty=60, price=Decimal("11"), fee=Decimal("0")),
        ]
        realized, net, lots = compute_realized_pnl(trades)
        self.assertEqual(realized, Decimal("140"))
        self.assertEqual(net, 0)
        self.assertEqual(len(lots), 0)

    def test_fees_adjust_basis(self):
        trades = [
            Trade(symbol="AAPL", side="BUY", qty=100, price=Decimal("10"), fee=Decimal("1")),
            Trade(symbol="AAPL", side="SELL", qty=100, price=Decimal("10"), fee=Decimal("1")),
        ]
        realized, net, _lots = compute_realized_pnl(trades)
        self.assertEqual(net, 0)
        self.assertEqual(realized, Decimal("-2"))

    def test_short_then_cover(self):
        trades = [
            Trade(symbol="TSLA", side="SELL", qty=10, price=Decimal("100"), fee=Decimal("0")),
            Trade(symbol="TSLA", side="BUY", qty=6, price=Decimal("90"), fee=Decimal("0")),
            Trade(symbol="TSLA", side="BUY", qty=4, price=Decimal("110"), fee=Decimal("0")),
        ]
        realized, net, lots = compute_realized_pnl(trades)
        self.assertEqual(net, 0)
        self.assertEqual(realized, Decimal("20"))
        self.assertEqual(len(lots), 0)


if __name__ == "__main__":
    unittest.main()
