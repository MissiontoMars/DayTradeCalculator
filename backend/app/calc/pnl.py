from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable, Literal


Side = Literal["BUY", "SELL"]


getcontext().prec = 28


@dataclass(frozen=True)
class Trade:
    symbol: str
    side: Side
    qty: int
    price: Decimal
    fee: Decimal
    timestamp_key: str | None = None
    source: str | None = None


@dataclass
class Lot:
    qty: int
    basis: Decimal


def _sign(n: int) -> int:
    if n > 0:
        return 1
    if n < 0:
        return -1
    return 0


def _effective_price(side: Side, qty: int, price: Decimal, fee: Decimal) -> Decimal:
    if qty <= 0:
        raise ValueError("qty must be positive")
    per_share_fee = (fee / Decimal(qty)) if fee else Decimal("0")
    if side == "BUY":
        return price + per_share_fee
    return price - per_share_fee


def compute_realized_pnl(trades: Iterable[Trade]) -> tuple[Decimal, int, list[Lot]]:
    lots: list[Lot] = []
    realized = Decimal("0")

    for t in trades:
        eff_price = _effective_price(t.side, t.qty, t.price, t.fee)
        incoming_qty = t.qty if t.side == "BUY" else -t.qty

        while incoming_qty != 0 and lots and _sign(lots[0].qty) != _sign(incoming_qty):
            lot = lots[0]
            match_qty = min(abs(lot.qty), abs(incoming_qty))

            if lot.qty > 0 and incoming_qty < 0:
                realized += Decimal(match_qty) * (eff_price - lot.basis)
                lot.qty -= match_qty
                incoming_qty += match_qty
            elif lot.qty < 0 and incoming_qty > 0:
                realized += Decimal(match_qty) * (lot.basis - eff_price)
                lot.qty += match_qty
                incoming_qty -= match_qty

            if lot.qty == 0:
                lots.pop(0)

        if incoming_qty != 0:
            lots.append(Lot(qty=incoming_qty, basis=eff_price))

    net_shares = sum(l.qty for l in lots)
    return realized, net_shares, lots


def lots_to_json(lots: list[Lot]) -> list[dict]:
    out: list[dict] = []
    for l in lots:
        out.append({"qty": l.qty, "basis": str(l.basis)})
    return out
